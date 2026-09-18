"""
Writing back into the workspace.

CLAUDE.md makes the markdown workspace the source of truth, so this is the only
module that writes to output/ and system/data/. Three rules it enforces:

  * Atomic writes. Write to .tmp then os.replace, which is atomic on NTFS and
    survives OneDrive briefly locking a file mid-sync.
  * One writer for applications.tsv. A Claude Code session may be running
    track.py at the same moment, so writes take a lock file.
  * TSV hygiene. sponsor_evidence holds a sentence lifted from a job ad, which
    can contain tabs and newlines. csv round-trips it correctly but a human
    opening the file in Excel sees a mess, so it is collapsed and truncated.
"""

from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from typing import Any

from .. import legacy, paths
from ..models import ExcludedJob, ScoredJob, Tier, TIER_LABEL

LOCK = paths.DATA / ".applications.lock"
LOCK_TIMEOUT_S = 10.0


class _FileLock:
    """A lock a separate Claude Code process can also see."""

    def __init__(self, path=LOCK, timeout: float = LOCK_TIMEOUT_S):
        self.path, self.timeout, self.fd = path, timeout, None

    def __enter__(self):
        deadline = time.time() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() > deadline:
                    # A stale lock from a crashed process must not block forever.
                    try:
                        if time.time() - self.path.stat().st_mtime > 60:
                            self.path.unlink(missing_ok=True)
                            continue
                    except OSError:
                        pass
                    raise TimeoutError(
                        "applications.tsv is locked by another process. If a Claude Code "
                        "session is running a tracker command, wait for it to finish."
                    )
                time.sleep(0.1)

    def __exit__(self, *a):
        if self.fd is not None:
            os.close(self.fd)
        self.path.unlink(missing_ok=True)


def atomic_write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def clean_cell(value: str, limit: int = 200) -> str:
    """A JD sentence, made safe for a tab-separated file a human will open."""
    s = re.sub(r"\s+", " ", (value or "").replace("\t", " ")).strip()
    return s[: limit - 1] + "…" if len(s) > limit else s


def md_cell(value: str, limit: int = 200) -> str:
    """
    A value made safe to drop into a markdown table cell.

    Job titles genuinely contain pipes: German ads write "(m|w|d)", and plenty
    of boards write "Senior QA Engineer | London". Interpolated raw, one of
    those splits the row into extra columns and corrupts the table from that
    row down. That matters more than it looks -- WorkspaceSource reads these
    tables back on the next scan, so a broken table becomes phantom jobs.
    """
    return clean_cell(value, limit).replace("|", "\\|")


# --------------------------------------------------------------------------
# applications.tsv
# --------------------------------------------------------------------------
def bootstrap_tracker() -> bool:
    """
    The file does not exist yet: track.load() returns [] so reads are safe, but
    nothing has ever written the header. Create it so she can open it in Excel.
    """
    if paths.APPLICATIONS_TSV.exists():
        return False
    with _FileLock():
        legacy.save_applications([])
    return True


def add_application(
    *, company: str, role: str, url: str = "", tier: str = "C", score: float = 0,
    track: str = "", folder: str = "", ats: str = "", evidence: str = "",
    notes: str = "", status: str = "PREPARED",
) -> dict[str, Any]:
    """Append one row. Same schema as track.py --add, written under the lock."""
    with _FileLock():
        rows = legacy.load_applications()
        for r in rows:
            if (legacy.track.norm(r["company"]) == legacy.track.norm(company)
                    and legacy.track.norm(r["role_title"]) == legacy.track.norm(role)):
                return r                     # never a duplicate

        today = date.today().isoformat()
        row = {
            "app_id": legacy.next_app_id(rows),
            "date_found": today, "date_applied": "",
            "company": company.strip(), "role_title": role.strip(),
            "job_url": url, "ats": ats, "track": track,
            "score": str(int(round(score))) if score else "",
            "sponsor_tier": tier, "sponsor_evidence": clean_cell(evidence),
            "status": status, "last_update": today,
            "folder": folder, "notes": clean_cell(notes),
        }
        rows.append(row)
        legacy.save_applications(rows)
        return row


def set_status(app_id: str, status: str, note: str = "") -> bool:
    with _FileLock():
        rows = legacy.load_applications()
        for r in rows:
            if r["app_id"] == app_id:
                r["status"] = status
                r["last_update"] = date.today().isoformat()
                if status == "APPLIED" and not r.get("date_applied"):
                    r["date_applied"] = date.today().isoformat()
                if note:
                    r["notes"] = clean_cell(f"{r.get('notes','')} {note}".strip())
                legacy.save_applications(rows)
                return True
    return False


def age_applications() -> int:
    """Flip APPLIED rows silent for 21 days to GHOSTED. Run on boot and daily."""
    legacy.refresh_today()
    flipped = 0
    with _FileLock():
        rows = legacy.load_applications()
        today = date.today()
        for r in rows:
            if r.get("status") != "APPLIED":
                continue
            when = legacy.track.parse_date(r.get("last_update") or r.get("date_applied") or "")
            if when and (today - when).days >= legacy.GHOST_AFTER_DAYS:
                r["status"] = "GHOSTED"
                r["last_update"] = today.isoformat()
                flipped += 1
        if flipped:
            legacy.save_applications(rows)
    return flipped


def sync_applied_companies() -> None:
    """applied-companies.md is generated. Regenerate it, never hand-edit."""
    legacy.refresh_today()
    pairs, companies, reasons = legacy.exclusions()
    lines = [
        "# Applied companies — GENERATED FILE, DO NOT EDIT",
        "",
        "Regenerated from `system/data/applications.tsv`.",
        f"Last synced: {date.today().isoformat()}",
        "",
        "## Never surface these company + role pairs again",
        "",
    ]
    lines += [f"- {c} / {r}" for c, r in sorted(pairs)] or ["(none)"]
    lines += ["", "## Companies fully suppressed right now", ""]
    lines += [f"- {c}" for c in sorted(companies)] or ["(none)"]
    lines += ["", "## Reasons", ""]
    lines += [f"- {r}" for r in reasons] or ["(nothing tracked yet)"]
    atomic_write(paths.APPLIED_COMPANIES, "\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# output/SUMMARY.md -- the one page she reads
# --------------------------------------------------------------------------
_SHORTLIST_HEADING = "## Companies found, no resume yet"


def backup_summary() -> None:
    """
    Keep a copy before overwriting.

    SUMMARY.md is the one page she reads and can contain roles found by hand or
    through Claude Code that this process cannot rediscover -- Indeed links in
    particular, since that connector is unreachable from here.
    """
    if not paths.SUMMARY.exists():
        return
    backups = paths.DB_DIR / "summary-backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    atomic_write(backups / f"SUMMARY-{stamp}.md", paths.read_text(paths.SUMMARY))
    keep = sorted(backups.glob("SUMMARY-*.md"))[:-20]
    for old in keep:
        old.unlink(missing_ok=True)


def _carry_forward(scored: list[ScoredJob]) -> list[list[str]]:
    """
    Rows from the previous shortlist that this scan did not rediscover.

    Without this the dashboard's own output replaces her curated list, and the
    workspace importer then reads that back -- so a role found through Claude
    Code silently disappears after one scan. Losing a cap-exempt lead that way
    is the most expensive failure this file can have.
    """
    text = paths.read_text(paths.SUMMARY)
    if _SHORTLIST_HEADING not in text:
        return []
    block = text.split(_SHORTLIST_HEADING, 1)[1].split("\n## ", 1)[0]

    seen = {
        (legacy.track.norm(s.job.company), legacy.track.norm(s.job.role_title))
        for s in scored
    }
    out: list[list[str]] = []
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or set(cells[0]) <= set("-: ") or cells[0].lower() == "#":
            continue
        company, role = cells[1], cells[2]
        if not company or company.lower() == "company":
            continue
        if (legacy.track.norm(company), legacy.track.norm(role)) in seen:
            continue
        out.append(cells)
    return out


def write_summary(
    *, scored: list[ScoredJob], excluded: list[ExcludedJob],
    last_run_note: str, study_items: list[tuple[str, int]] | None = None,
) -> None:
    backup_summary()
    carried = _carry_forward(scored)
    rows = legacy.load_applications()
    today = date.today()

    out: list[str] = [
        "# Your job search — the one page",
        "",
        f"**Last run:** {last_run_note}",
        "",
        "**To start:** open the dashboard and press *Find jobs*, or paste a job ad "
        "into the Resume Builder tab.",
        "",
        "## Your resumes",
        "",
    ]

    prepared = [r for r in rows if r.get("folder")]
    if prepared:
        out += ["| # | Company | Role | Folder | Tier | Score | Status | Apply |",
                "|---|---------|------|--------|------|-------|--------|-------|"]
        for i, r in enumerate(prepared, 1):
            link = f"[Apply]({r['job_url']})" if r.get("job_url") else "—"
            out.append(
                f"| {i} | {md_cell(r['company'])} | {md_cell(r['role_title'])} | "
                f"`{md_cell(r['folder'])}` | "
                f"{r.get('sponsor_tier','C')} | {r.get('score','')} | {r.get('status','')} | {link} |"
            )
    else:
        out.append("_No resumes built yet._")

    out += ["", "## Pipeline", ""]
    live = [r for r in rows if r.get("status") in legacy.OPEN_STATUSES]
    if live:
        out += ["| # | Company | Role | Applied | Days quiet | Next move |",
                "|---|---------|------|---------|------------|-----------|"]
        for i, r in enumerate(live, 1):
            when = legacy.track.parse_date(r.get("date_applied") or r.get("last_update") or "")
            quiet = (today - when).days if when else "—"
            move = "Follow up" if isinstance(quiet, int) and quiet >= 10 else "Wait"
            out.append(f"| {i} | {md_cell(r['company'])} | {md_cell(r['role_title'])} | "
                       f"{r.get('date_applied') or '—'} | {quiet} | {move} |")
    else:
        out.append("_Nothing out yet._")
    out += ["",
            f"After {legacy.GHOST_AFTER_DAYS} days of silence an application becomes GHOSTED, "
            f"and that company becomes available again after {legacy.GHOST_COOLDOWN_DAYS} days "
            "for a different role. A rejection suppresses the company for "
            f"{legacy.REJECT_COOLDOWN_DAYS} days.",
            ""]

    out += ["## Companies found, no resume yet", ""]
    fresh = [s for s in scored if not any(
        legacy.track.norm(r["company"]) == legacy.track.norm(s.job.company)
        and legacy.track.norm(r["role_title"]) == legacy.track.norm(s.job.role_title)
        for r in rows
    )]
    if fresh:
        out += ["| # | Company | Role | Tier | Sponsor evidence | Location | Score | Link |",
                "|---|---------|------|------|------------------|----------|-------|------|"]
        for i, s in enumerate(fresh[:25], 1):
            ev = (
                s.sponsor.cap_exempt_why if s.sponsor.cap_exempt
                else (f"{s.sponsor.h1b_approvals} H-1B approvals "
                      f"{'/'.join(s.sponsor.h1b_years)}" if s.sponsor.h1b_approvals
                      else "no record — the normal case")
            )
            link = f"[Apply]({s.job.url})" if s.job.url else "—"
            out.append(
                f"| {i} | {md_cell(s.job.company)} | {md_cell(s.job.role_title)} | "
                f"{s.sponsor.tier.value} | {md_cell(ev, 60)} | "
                f"{md_cell(s.job.location) or '—'} | {s.score.total} | {link} |"
            )
    elif not carried:
        out.append("_Nothing new this run._")

    if carried:
        if not fresh:
            out += ["| # | Company | Role | Tier | Sponsor evidence | Location | Score | Link |",
                    "|---|---------|------|------|------------------|----------|-------|------|"]
        start = len(fresh)
        for i, cells in enumerate(carried[:25], start=start + 1):
            padded = (cells + [""] * 8)[:8]
            padded[0] = str(i)
            out.append("| " + " | ".join(padded) + " |")
        out += ["",
                f"_The last {len(carried)} above were found earlier and were not "
                "re-found this run — they are kept so nothing gets lost._"]

    out += ["", "## Excluded", "",
            "Every exclusion shows the sentence that caused it, so you can overrule me.",
            "",
            "| Company | Role | Why | Triggering sentence |",
            "|---------|------|-----|---------------------|"]
    if excluded:
        for e in excluded[:40]:
            out.append(
                f"| {md_cell(e.company)} | {md_cell(e.role_title)} | {md_cell(e.why)} | "
                f"{md_cell(e.triggering_sentence or '—', 120)} |"
            )
    else:
        out.append("| — | — | Nothing excluded this run | — |")

    out += ["", "## What to study this week", ""]
    if study_items:
        for skill, n in study_items[:8]:
            out.append(f"- **{skill}** — wanted by {n} of the jobs above")
    else:
        out.append("_Build some resumes and this fills in with what the jobs actually ask for._")

    out += ["", "## How the sponsorship rule works", "",
            "| What the posting says | What happens |",
            "|---|---|",
            "| Explicitly will not sponsor | Excluded |",
            "| Says nothing | **Shown** — this is most postings, and where most offers come from |",
            "| Explicitly will sponsor | Shown, ranked top |",
            "| Needs citizenship / clearance / ITAR | Excluded |",
            ""]
    for t in ("S", "A", "B", "C"):
        out.append(f"- **{t}** — {TIER_LABEL[t]}")
    out += ["",
            "Jobs are ordered by tier first and score second: a cap-exempt employer can "
            "file for you any time of year with no lottery, which outweighs a few points.",
            ""]

    atomic_write(paths.SUMMARY, "\n".join(out) + "\n")


def append_scan_history(
    *, found: int, kept: int, excluded: int, prepared: int, note: str
) -> None:
    header = "date\tregion\tqueries_run\tfound\tkept\texcluded\tprepared\tnotes\n"
    line = (f"{date.today().isoformat()}\tUS (dashboard)\t1\t{found}\t{kept}\t"
            f"{excluded}\t{prepared}\t{clean_cell(note, 160)}\n")
    p = paths.SCAN_HISTORY
    if not p.exists():
        atomic_write(p, header + line)
    else:
        with p.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)


# --------------------------------------------------------------------------
# application folders
# --------------------------------------------------------------------------
def folder_name(company: str, index: int | None = None) -> str:
    """output/Annie_Manoharan_<Company>_<NN> -- the live convention on disk."""
    clean = re.sub(r"[^A-Za-z0-9]", "", company or "Company") or "Company"
    if index is None:
        index = 1
        while (paths.OUTPUT / f"Annie_Manoharan_{clean}_{index:02d}").exists():
            index += 1
    return f"Annie_Manoharan_{clean}_{index:02d}"


def write_application(
    folder: str, *, tex: str = "", jd_text: str = "", research: str = "",
    study_plan: str = "", audit: str = "", pdf_bytes: bytes | None = None,
) -> dict[str, str]:
    """Promote finished artifacts into the workspace. Scratch never lands here."""
    base = paths.OUTPUT / folder
    base.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for name, body in (
        ("resume.tex", tex), ("job-description.txt", jd_text),
        ("research.md", research), ("study-plan.md", study_plan), ("audit.md", audit),
    ):
        if body:
            atomic_write(base / name, body)
            written[name] = str(base / name)
    if pdf_bytes:
        tmp = base / "resume.pdf.tmp"
        tmp.write_bytes(pdf_bytes)
        os.replace(tmp, base / "resume.pdf")
        written["resume.pdf"] = str(base / "resume.pdf")
    return written


def list_applications() -> list[dict[str, Any]]:
    """Every folder under output/, whether the dashboard or /hunt created it."""
    out: list[dict[str, Any]] = []
    if not paths.OUTPUT.exists():
        return out
    tracker = {
        (legacy.track.norm(r["company"]), legacy.track.norm(r["role_title"])): r
        for r in legacy.load_applications()
    }
    by_folder = {r.get("folder"): r for r in legacy.load_applications() if r.get("folder")}

    for d in sorted(paths.OUTPUT.iterdir()):
        if not d.is_dir():
            continue
        tex = d / "resume.tex"
        if not tex.exists():
            continue
        row = by_folder.get(d.name, {})
        company = row.get("company") or _company_from_folder(d.name)
        out.append({
            "folder": d.name,
            "company": company,
            "role_title": row.get("role_title") or "",
            "tier": row.get("sponsor_tier") or "",
            "score": row.get("score") or "",
            "status": row.get("status") or "DRAFT",
            "app_id": row.get("app_id") or "",
            "url": row.get("job_url") or "",
            "has_pdf": (d / "resume.pdf").exists(),
            "has_research": (d / "research.md").exists(),
            "has_study_plan": (d / "study-plan.md").exists(),
            "updated_at": datetime.fromtimestamp(tex.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return out


def _company_from_folder(name: str) -> str:
    m = re.match(r"Annie_Manoharan_(.+?)_\d+$", name)
    return re.sub(r"(?<!^)(?=[A-Z])", " ", m.group(1)) if m else name
