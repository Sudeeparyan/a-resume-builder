"""
Bring an assistant's answer back into the workspace.

This is the bridge between the two ways this system runs. Today she works in a
Claude or ChatGPT project on her phone -- no API key, no server -- and pastes
the answer here so it becomes tracked, rankable and buildable. Later, when the
same thing runs on an API, the output lands through this identical path. One
data model, two front doors, and the workspace stays the source of truth either
way.

**Everything arriving here is untrusted.** It was written by a language model
that may have invented a company, a link or a sponsorship claim. So nothing the
paste asserts about eligibility is believed:

  * the sponsorship gate is re-run locally on the ad text
  * the tracker gate is re-run, so a company she already applied to cannot be
    smuggled back in
  * every link is marked UNCHECKED until verify_job_url says otherwise
  * a tier or score in the paste is discarded and recomputed

What the paste is trusted for is the only thing it is good at: naming companies,
roles and URLs that a human can go and check.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from .. import db, legacy
from ..agents import deterministic as D
from ..models import JobPosting, LinkStatus, ScoredJob
from . import context_loader, scoring, workspace_sync

FORMAT_VERSION = 1

# The fence the project pack asks the assistant to emit.
_FENCE = re.compile(r"```(?:careerops|json)?\s*(\{.*?\}|\[.*?\])\s*```", re.S)
_URL = re.compile(r"https?://[^\s)\]<>\"']+")


class IngestError(ValueError):
    """Something a person can fix, phrased for a person."""


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def parse(text: str) -> list[dict[str, Any]]:
    """
    Pull job rows out of whatever she pasted.

    Three shapes, in order of preference: the fenced block the pack asks for,
    a bare JSON object or array, and finally a markdown table -- because an
    assistant asked for a table will produce one no matter what the instructions
    said, and refusing it would just make her retype things.
    """
    text = (text or "").strip()
    if not text:
        raise IngestError("There is nothing to read - paste the assistant's answer first.")

    for chunk in _fenced_blocks(text) + [text]:
        rows = _rows_from_json(chunk)
        if rows:
            return rows

    rows = _rows_from_table(text)
    if rows:
        return rows

    raise IngestError(
        "I could not find any jobs in that. Paste the whole answer, including the "
        "table or the code block. If your assistant only wrote prose, ask it for "
        "\"the careerops block\" and paste that."
    )


def _fenced_blocks(text: str) -> list[str]:
    return [m.group(1) for m in _FENCE.finditer(text)]


def _rows_from_json(chunk: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(chunk.strip())
    except ValueError:
        return []
    if isinstance(data, dict):
        for key in ("jobs", "results", "rows", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        return []
    # Normalise here so every caller sees the same key names whichever shape
    # the assistant produced. The table path already does this, and leaving the
    # JSON path un-normalised makes every consumer re-learn the aliases.
    return [_normalise(r) for r in data if isinstance(r, dict) and _row_company(r)]


def _normalise(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in _ALIASES:
        v = _get(row, field)
        if v:
            out[field] = v
    # Keep anything unrecognised, so nothing the assistant said is silently lost.
    known = {k.lower().replace(" ", "_") for names in _ALIASES.values() for k in names}
    for k, v in row.items():
        if str(k).lower().replace(" ", "_") not in known and v not in (None, ""):
            out.setdefault(str(k), v)
    return out


_ALIASES = {
    "company": ("company", "employer", "organisation", "organization"),
    "role_title": ("role_title", "role", "title", "position", "job_title"),
    "url": ("url", "link", "apply", "apply_link", "posting_url", "job_url"),
    "location": ("location", "where", "city"),
    "jd_text": ("jd_text", "description", "job_description", "jd", "ad"),
    "note": ("note", "why", "why_it_fits", "reason", "notes"),
    "posted_at": ("posted_at", "posted", "date_posted"),
}


def _get(row: dict[str, Any], field: str) -> str:
    for key in _ALIASES.get(field, (field,)):
        for k, v in row.items():
            if str(k).strip().lower().replace(" ", "_") == key and v:
                return str(v).strip()
    return ""


def _row_company(row: dict[str, Any]) -> str:
    return _get(row, "company")


def _rows_from_table(text: str) -> list[dict[str, Any]]:
    """Read a markdown table, matching columns by their header names."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []

    def cells(ln: str) -> list[str]:
        return [c.strip() for c in ln.strip().strip("|").split("|")]

    header = [h.lower().strip("* ") for h in cells(lines[0])]
    idx: dict[str, int] = {}
    for field, names in _ALIASES.items():
        for i, h in enumerate(header):
            key = h.replace(" ", "_")
            if key in names or any(n in key for n in names):
                idx.setdefault(field, i)
                break
    if "company" not in idx:
        return []

    rows: list[dict[str, Any]] = []
    for ln in lines[1:]:
        c = cells(ln)
        if not c or set("".join(c)) <= set("-: "):
            continue                                   # the header rule row
        row: dict[str, Any] = {}
        for field, i in idx.items():
            if i < len(c):
                row[field] = _clean_cell(c[i])
        # A markdown link cell carries the real URL inside the parentheses.
        raw = c[idx["url"]] if "url" in idx and idx["url"] < len(c) else ""
        m = _URL.search(raw)
        if m:
            row["url"] = m.group(0).rstrip(".,)")
        if row.get("company"):
            rows.append(row)
    return rows


def _clean_cell(s: str) -> str:
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s or "")
    return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()


# --------------------------------------------------------------------------
# normalising
# --------------------------------------------------------------------------
def to_postings(rows: list[dict[str, Any]], *, origin: str = "pasted") -> list[JobPosting]:
    out: list[JobPosting] = []
    for i, row in enumerate(rows, start=1):
        company = _get(row, "company")
        role = _get(row, "role_title")
        if not company or not role:
            continue
        url = _get(row, "url")
        if url and not url.lower().startswith("http"):
            url = ""
        jd = _get(row, "jd_text") or _get(row, "note")
        source_id = legacy.normalize_company(company) + "-" + legacy.track.norm(role)
        out.append(JobPosting(
            source=origin,
            source_id=source_id[:120] or f"row{i}",
            company=company,
            role_title=role,
            url=url,
            location=_get(row, "location"),
            jd_text=jd,
            content_hash=legacy.track.norm(f"{company}|{role}")[:64],
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            raw={"ingested_from": origin, "original_row": row},
        ))
    return out


# --------------------------------------------------------------------------
# the gates -- re-run locally, never taken on trust
# --------------------------------------------------------------------------
def screen(postings: list[JobPosting]) -> dict[str, Any]:
    """
    Apply the same gates a real scan applies, and report what happened to each
    row so a wrong exclusion is visible rather than a silent disappearance.
    """
    postings, dupes = D.dedupe(postings)
    kept, excluded = D.hard_filter(postings)

    tracker = D.TrackerGate()
    kept, tracker_dropped = tracker.split(kept)
    excluded += tracker_dropped

    fb = context_loader.load()
    scored: list[ScoredJob] = []
    for p in kept:
        verdict = D.sponsorship_gate(p)
        if verdict.excluded:
            from ..models import ExcludedJob
            excluded.append(ExcludedJob(
                company=p.company, role_title=p.role_title, url=p.url,
                why=verdict.reason_label,
                triggering_sentence=verdict.triggering_sentence,
                stage="sponsorship",
            ))
            continue

        s = ScoredJob(job=p, sponsor=verdict, link_status=LinkStatus.UNCHECKED)
        thin = len(p.jd_text.strip()) < 200
        s.jd = None if thin else D.parse_jd_keywords(p)
        s.score = scoring.score_job(p, verdict, jd=s.jd, fb=fb)
        if thin:
            # Without the ad text there is nothing to score against. Say so
            # rather than presenting a confident number built on nothing.
            s.score.evidence["skill_match"] = (
                "No job ad text came across with this one, so it is not scored on "
                "keywords yet. Open the link and paste the description in."
            )
        s.recommendation = scoring.recommendation(
            s.score.total, s.score.competition, has_jd=not thin
        )
        s.ghost_flags = scoring.ghost_flags(p)
        scored.append(s)

    return {
        "scored": scoring.rank(scored),
        "excluded": excluded,
        "duplicates": dupes,
    }


# --------------------------------------------------------------------------
# persisting
# --------------------------------------------------------------------------
def save(result: dict[str, Any], *, origin: str = "pasted") -> dict[str, Any]:
    """
    Write ingested jobs into the same tables a scan writes, under their own run
    id, so they appear in the UI exactly like scanned ones and are ranked
    against them.
    """
    run_id = "ingest-" + datetime.now().strftime("%Y%m%d%H%M%S")
    scored: list[ScoredJob] = result["scored"]
    excluded = result["excluded"]

    db.connect().execute(
        "INSERT INTO runs (id, kind, status, params, stages, message, cost_usd,"
        " started_at, finished_at, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (run_id, "ingest", "DONE", db.dumps({"origin": origin}), "[]",
         f"Imported {len(scored)} job(s) from {origin}", 0.0,
         db.now(), db.now(), db.now()),
    )

    for s in scored:
        j = s.job
        jid = f"{j.source}:{j.source_id}"
        db.connect().execute(
            "INSERT INTO jobs (id, source, source_id, company, company_key, role_title,"
            " role_key, url, location, remote, department, posted_at, jd_text,"
            " content_hash, raw_json, first_seen, last_seen)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(company_key, role_key, content_hash) DO UPDATE SET"
            " last_seen=excluded.last_seen, url=excluded.url,"
            " jd_text=CASE WHEN length(excluded.jd_text) > length(jobs.jd_text)"
            "   THEN excluded.jd_text ELSE jobs.jd_text END",
            (jid, j.source, j.source_id, j.company, legacy.normalize_company(j.company),
             j.role_title, legacy.track.norm(j.role_title), j.url, j.location,
             int(j.remote), j.department, None, j.jd_text, j.content_hash,
             db.dumps(j.raw), db.now(), db.now()),
        )
        db.connect().execute(
            "INSERT INTO job_analysis (job_id, run_id, tier, verdict, reason,"
            " reason_label, triggering_sentence, everify, cap_exempt, h1b_approvals,"
            " link_status, score, score_json, jd_json, research_json, prediction_json,"
            " recommendation, ghost_flags, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT(job_id) DO UPDATE SET run_id=excluded.run_id,"
            " tier=excluded.tier, score=excluded.score, score_json=excluded.score_json,"
            " jd_json=excluded.jd_json, recommendation=excluded.recommendation,"
            " updated_at=excluded.updated_at",
            (jid, run_id, s.sponsor.tier.value, s.sponsor.verdict, s.sponsor.reason,
             s.sponsor.reason_label, s.sponsor.triggering_sentence,
             int(s.sponsor.everify), int(s.sponsor.cap_exempt), s.sponsor.h1b_approvals,
             s.link_status.value, s.score.total,
             db.dumps(s.score.model_dump(mode="json")),
             db.dumps(s.jd.model_dump(mode="json") if s.jd else {}),
             "{}", "{}", s.recommendation, db.dumps(s.ghost_flags), db.now()),
        )

    for e in excluded:
        db.connect().execute(
            "INSERT INTO excluded (run_id, company, role_title, url, stage, why,"
            " triggering_sentence, at) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, e.company, e.role_title, e.url, e.stage, e.why,
             e.triggering_sentence, db.now()),
        )

    try:
        workspace_sync.write_summary(
            scored=scored, excluded=excluded,
            last_run_note=(
                f"Imported {len(scored)} job(s) from a {origin} answer on "
                f"{datetime.now():%d %b}. Links are unverified until you check them."
            ),
            study_items=[],
        )
    except Exception:  # noqa: BLE001 -- the summary is a view, not the record
        pass

    return {"run_id": run_id, "saved": len(scored), "excluded": len(excluded)}


def preview(text: str, *, origin: str = "pasted") -> dict[str, Any]:
    """Parse and gate without writing anything, so she can look before saving."""
    rows = parse(text)
    res = screen(to_postings(rows, origin=origin))
    scored: list[ScoredJob] = res["scored"]
    return {
        "found": len(rows),
        "duplicates": res["duplicates"],
        "jobs": [{
            "company": s.job.company,
            "role_title": s.job.role_title,
            "url": s.job.url,
            "location": s.job.location,
            "tier": s.sponsor.tier.value,
            "tier_why": s.sponsor.reason_label,
            "score": round(s.score.total, 1),
            "has_ad_text": len(s.job.jd_text.strip()) >= 200,
            "ghost_flags": s.ghost_flags,
            "link_status": s.link_status.value,
        } for s in scored],
        "excluded": [{
            "company": e.company, "role_title": e.role_title,
            "why": e.why, "triggering_sentence": e.triggering_sentence,
            "stage": e.stage,
        } for e in res["excluded"]],
        "warnings": _warnings(scored),
    }


def _warnings(scored: list[ScoredJob]) -> list[str]:
    out: list[str] = []
    no_url = sum(1 for s in scored if not s.job.url)
    thin = sum(1 for s in scored if len(s.job.jd_text.strip()) < 200)
    if no_url:
        out.append(
            f"{no_url} of these came with no link. An assistant cannot browse unless "
            "it searched the web, so check these exist before you spend time on them."
        )
    if thin:
        out.append(
            f"{thin} have no job ad text, so they are not keyword-scored yet. Open each "
            "link and paste the description in to get a real match score."
        )
    out.append(
        "Every link is marked unverified. Run Check links before you trust one."
    )
    return out
