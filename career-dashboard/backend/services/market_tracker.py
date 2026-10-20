"""The Sponsorship Tracker: every in-target US posting a search has read, with its sponsorship evidence.

A discovery pass reads far more postings than it saves: the feed pass reads every tracked
company and H-1B sponsor board, keeps the US, entry-level roles in Annie's four tracks, then
gates each one (sponsorship, never re-apply, fit, employer check) and saves the best few.
Until now everything that was read but not saved was a count in the run summary. The
Tracker keeps one row per posting so Annie can see the whole market she is searching:

* the posting's own sponsorship sentence, quoted (supports, silent, refuses, cannot hire);
* the employer's USCIS H-1B record (approvals, denials, fiscal years) and its tier;
* advertised pay when the posting states a range (US pay-transparency laws make this common);
* what the search decided and why (saved, excluded, below her fit threshold, ...).

Annie's own status (saved, applied, removed) is joined from the jobs table at read time and
never stored here, so there is still one status list. Rows not seen for ``KEEP_DAYS`` are
pruned. Nothing here is immigration advice: these are published facts with their sources.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from backend.services.postings import canonical_url, posting_key

PAGE = 50
MAX_ROWS = 5000
KEEP_DAYS = 60
TIER_ORDER = {"S": 1, "A": 2, "B": 3, "C": 4, "EXCLUDED": 9}
STATEMENTS = {
    "supports": "Says it sponsors",
    "silent": "Silent on sponsorship",
    "refuses": "Will not sponsor",
    "cannot_hire": "Requires citizenship / clearance",
}
OUTCOMES = {
    "saved": "Saved to your jobs",
    "duplicate": "Already in your jobs",
    "not_selected": "Passed every check; not saved this pass",
    "relevance": "Below her fit threshold",
    "reapply": "Never-re-apply rule",
    "legitimacy": "Employer needs a check",
    "excluded": "Excluded by the sponsorship gate",
}
SOURCES = {"tracked": "Tracked company", "sponsor_board": "H-1B sponsor board", "ai_search": "AI web search",
           "tracker": "Saved from the Tracker"}
FILTERS = {"q": "", "tier": "", "statement": "", "source": "", "outcome": "", "h1b": "", "min_pay": "",
           "seen_within": "", "hide_refusing": "1", "show_applied": "", "sort": "best", "page": "1"}
COLUMNS = ("key", "company", "title", "location", "url", "source", "posted_at", "statement", "sentence", "tier",
           "cap_exempt", "everify", "h1b_approvals", "h1b_denials", "h1b_years", "h1b_name", "pay_min", "pay_max",
           "pay_text", "fit_score", "outcome", "outcome_reason", "description")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---- advertised pay --------------------------------------------------------------------------

_AMOUNT = r"(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d+)?\s?[kK]?)"
_RANGE = re.compile(r"\$\s?" + _AMOUNT + r"\s*(?:USD\s*)?(?:-|–|—|to)\s*\$?\s?" + _AMOUNT + r"(\s*(?:USD|per|/|an|a)?\s*(?:hour|hr|year|yr|annually|annum)?)",
                    re.I)


def _amount(raw: str) -> float:
    raw = raw.replace(",", "").replace(" ", "")
    if raw[-1:] in "kK":
        return float(raw[:-1]) * 1000
    return float(raw)


def pay_range(text: str) -> tuple[int | None, int | None, str]:
    """(annual min, annual max, the words quoted) from the first plausible salary range; hourly is x2080."""
    for match in _RANGE.finditer(text or ""):
        try:
            low, high = _amount(match[1]), _amount(match[2])
        except ValueError:
            continue
        hourly = bool(re.search(r"hour|hr", match[3] or "", re.I)) or (high < 500 and low < 500)
        if hourly:
            low, high = low * 2080, high * 2080
        if 20_000 <= low <= high <= 1_000_000:
            return int(low), int(high), " ".join(match[0].split())[:80]
    return None, None, ""


# ---- what a pass read -------------------------------------------------------------------------

def statement(verdict) -> str:
    reason = verdict.screen.reason
    return {"no_sponsorship": "refuses", "cannot_hire": "cannot_hire", "explicit_sponsorship": "supports"}.get(reason, "silent")


def observation(job: dict[str, Any], verdict, source: str) -> dict[str, Any] | None:
    """One Tracker row for a posting and its sponsorship verdict; None when it has no usable URL
    or is outside the US (the Tracker charts the US market Annie can work in, nothing else)."""
    from backend.job_quality import is_us_location, remote_outside_us
    where = str(job.get("location") or "").strip()
    bare_remote = where.casefold() == "remote"
    if not (is_us_location(where) or (bare_remote and not remote_outside_us(job.get("description") or ""))):
        return None
    try:
        key = posting_key(job.get("url") or "")
        url = canonical_url(job.get("url") or "")
    except ValueError:
        return None
    low, high, words = pay_range(job.get("description") or "")
    evidence = verdict.evidence_json()
    return {
        "key": key, "company": str(job.get("company") or "").strip(), "title": str(job.get("title") or "").strip(),
        "location": str(job.get("location") or "").strip(), "url": url, "source": source,
        "posted_at": str(job.get("posted_at") or "")[:10], "statement": statement(verdict),
        "sentence": verdict.screen.sentence or "", "tier": verdict.tier, "cap_exempt": int(bool(verdict.cap_exempt)),
        "everify": int(bool(verdict.everify)), "h1b_approvals": int(verdict.h1b_approvals or 0),
        "h1b_denials": int(verdict.h1b_denials or 0), "h1b_years": ", ".join(evidence.get("h1b_years") or []),
        "h1b_name": verdict.h1b_matched_name or "", "pay_min": low, "pay_max": high, "pay_text": words,
        "fit_score": None, "outcome": "not_selected", "outcome_reason": "", "job_id": None,
        "description": str(job.get("description") or ""),
    }


def record(db, rows: Iterable[dict[str, Any] | None]) -> int:
    """Upsert what a pass read; the first sighting is kept, the latest outcome wins."""
    now = _now()
    count = 0
    for row in rows:
        if not row:
            continue
        values = {**{c: row.get(c) for c in COLUMNS}, "job_id": row.get("job_id"), "now": now}
        db.execute(
            f"""INSERT INTO market_postings({",".join(COLUMNS)},job_id,first_seen,last_seen,times_seen)
            VALUES({",".join(":" + c for c in COLUMNS)},:job_id,:now,:now,1)
            ON CONFLICT(key) DO UPDATE SET {",".join(f"{c}=excluded.{c}" for c in COLUMNS if c != "key")},
            job_id=COALESCE(excluded.job_id, market_postings.job_id), last_seen=excluded.last_seen,
            times_seen=market_postings.times_seen+1""",
            values,
        )
        count += 1
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
    db.execute("DELETE FROM market_postings WHERE last_seen < ?", (cutoff,))
    return count


# ---- reading it back ---------------------------------------------------------------------------

_SELECT = """
SELECT m.*, j.id AS my_job_id, j.status AS my_status, j.deleted_at AS my_removed_at
FROM market_postings m
LEFT JOIN posting_identities p ON p.identity = m.key
LEFT JOIN jobs j ON j.id = COALESCE(p.job_id, m.job_id)
"""


def _where(filters: dict[str, str]) -> tuple[str, list[Any]]:
    clauses, args = [], []
    q = (filters.get("q") or "").strip()
    if q:
        clauses.append("(m.company LIKE ? OR m.title LIKE ? OR m.location LIKE ?)")
        args += [f"%{q}%"] * 3
    for field in ("tier", "statement", "source", "outcome"):
        value = (filters.get(field) or "").strip()
        if value:
            clauses.append(f"m.{field} = ?")
            args.append(value)
    if filters.get("h1b") == "record":
        clauses.append("m.h1b_approvals > 0")
    elif filters.get("h1b") == "none":
        clauses.append("m.h1b_approvals = 0")
    if str(filters.get("min_pay") or "").strip().isdigit():
        clauses.append("m.pay_max >= ?")
        args.append(int(filters["min_pay"]))
    if str(filters.get("seen_within") or "").strip().isdigit():
        since = datetime.now(timezone.utc) - timedelta(days=int(filters["seen_within"]))
        clauses.append("m.last_seen >= ?")
        args.append(since.isoformat(timespec="seconds"))
    if filters.get("hide_refusing", "1") == "1" and not filters.get("statement"):
        clauses.append("m.statement NOT IN ('refuses','cannot_hire')")
    if not filters.get("show_applied"):
        clauses.append("(j.status IS NULL OR j.status IN ('saved','prepared') OR j.deleted_at IS NOT NULL)")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", args


_ORDER = {
    "best": "CASE m.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 WHEN 'C' THEN 4 ELSE 9 END, "
            "COALESCE(m.fit_score, 0) DESC, m.h1b_approvals DESC, m.last_seen DESC",
    "newest": "m.first_seen DESC, m.company",
    "pay": "COALESCE(m.pay_max, 0) DESC, m.company",
    "h1b": "m.h1b_approvals DESC, m.company",
    "fit": "COALESCE(m.fit_score, 0) DESC, m.company",
}


def _public(row) -> dict[str, Any]:
    item = {k: row[k] for k in row.keys() if k != "description"}
    item["statement_label"] = STATEMENTS.get(item["statement"], item["statement"])
    item["outcome_label"] = OUTCOMES.get(item["outcome"], item["outcome"])
    item["source_label"] = SOURCES.get(item["source"], item["source"])
    item["mine"] = ("removed" if item.get("my_removed_at") else item.get("my_status")) or ""
    return item


def query(db, filters: dict[str, str] | None = None) -> dict[str, Any]:
    """One page of Tracker rows with the filters applied, plus counts for the filter menus."""
    filters = {**FILTERS, **{k: str(v) for k, v in (filters or {}).items() if v is not None}}
    where, args = _where(filters)
    total = db.execute(f"SELECT COUNT(*) FROM ({_SELECT}{where})", args).fetchone()[0]
    page = max(1, int(filters["page"]) if str(filters["page"]).isdigit() else 1)
    order = _ORDER.get(filters.get("sort") or "best", _ORDER["best"])
    rows = db.execute(f"{_SELECT}{where} ORDER BY {order} LIMIT ? OFFSET ?", [*args, PAGE, (page - 1) * PAGE]).fetchall()
    facets = {}
    for field in ("tier", "statement", "source", "outcome"):
        facets[field] = {r[0]: r[1] for r in db.execute(f"SELECT {field}, COUNT(*) FROM market_postings GROUP BY {field}")}
    summary = db.execute(
        "SELECT COUNT(*), COUNT(DISTINCT company), SUM(h1b_approvals > 0), SUM(statement='supports'), "
        "SUM(statement IN ('refuses','cannot_hire')), MAX(last_seen) FROM market_postings").fetchone()
    return {
        "items": [_public(row) for row in rows], "total": total, "page": page, "page_size": PAGE,
        "filters": filters, "facets": facets,
        "labels": {"statement": STATEMENTS, "outcome": OUTCOMES, "source": SOURCES},
        "summary": {"postings": summary[0] or 0, "employers": summary[1] or 0, "with_h1b_record": summary[2] or 0,
                    "says_sponsors": summary[3] or 0, "refusing": summary[4] or 0, "last_read": summary[5] or ""},
    }


def rows_for_export(db, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    filters = {**FILTERS, **{k: str(v) for k, v in (filters or {}).items() if v is not None}}
    where, args = _where(filters)
    order = _ORDER.get(filters.get("sort") or "best", _ORDER["best"])
    return [_public(row) for row in db.execute(f"{_SELECT}{where} ORDER BY {order} LIMIT ?", [*args, MAX_ROWS])]


EXPORT = (("Company", "company"), ("Role", "title"), ("Location", "location"), ("Tier", "tier"),
          ("Sponsorship statement", "statement_label"), ("Posting says", "sentence"),
          ("H-1B approvals (USCIS)", "h1b_approvals"), ("H-1B denials", "h1b_denials"), ("Fiscal years", "h1b_years"),
          ("USCIS employer", "h1b_name"), ("E-Verify mentioned", "everify"), ("Cap-exempt", "cap_exempt"),
          ("Pay min (annual USD)", "pay_min"), ("Pay max (annual USD)", "pay_max"), ("Pay as written", "pay_text"),
          ("Fit score", "fit_score"), ("Search decision", "outcome_label"), ("Why", "outcome_reason"),
          ("Your status", "mine"), ("Found via", "source_label"), ("Posted", "posted_at"),
          ("First seen", "first_seen"), ("Last seen", "last_seen"), ("Apply link", "url"))


def to_csv(items: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([label for label, _ in EXPORT])
    for item in items:
        writer.writerow(["" if item.get(field) is None else item.get(field) for _, field in EXPORT])
    return buffer.getvalue()


def posting_for_save(db, key: str) -> dict[str, Any]:
    """The saved posting text for one Tracker row, in the shape add_posting takes."""
    row = db.execute("SELECT * FROM market_postings WHERE key=?", (key,)).fetchone()
    if not row:
        raise ValueError("That posting is no longer in the Tracker; run a search again")
    if row["statement"] in ("refuses", "cannot_hire"):
        raise ValueError("The posting's own words exclude it; restore it from Excluded roles if that was a wrong call")
    if len((row["description"] or "").strip()) < 80:
        raise ValueError("The Tracker has no full job description for this posting; paste its link with 'Save a job'")
    return {"company": row["company"], "title": row["title"], "location": row["location"] or "United States",
            "url": row["url"], "description": row["description"], "requisition_id": ""}


def mark_saved(db, key: str, job_id: str) -> None:
    db.execute("UPDATE market_postings SET outcome='saved', outcome_reason='Saved by Annie from the Tracker', job_id=? "
               "WHERE key=?", (job_id, key))
