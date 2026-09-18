"""
The morning brief: scan, rank, and build a resume for each of the top jobs.

This is the thing that runs at 09:00 without her opening anything. It is the
same pipeline the Job Hunter tab drives -- scan, sponsorship gate, tracker gate,
link check, score -- followed by a tailored one-page resume per job, so what she
finds in the morning is a folder she can send, not a list she still has to work.

tailor_job() lives here rather than in routes.py because the scheduled run and
the button in the UI must build resumes the same way. A second implementation
is a second set of rules to keep in sync, and they would drift.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import db, settings
from ..models import JDAnalysis, JobPosting
from . import runner


async def tailor_job(job_id: str, *, spec: Any = None) -> dict[str, Any]:
    """
    Build and save one tailored resume. Raises ValueError with a plain-English
    reason a non-developer can act on.
    """
    from ..agents import builder

    row = db.connect().execute(
        "SELECT j.*, a.jd_json, a.research_json FROM jobs j"
        " LEFT JOIN job_analysis a ON a.job_id = j.id WHERE j.id = ?",
        (job_id,),
    ).fetchone()
    if not row:
        raise ValueError("No such job.")

    job = JobPosting(
        source=row["source"], source_id=row["source_id"], company=row["company"],
        role_title=row["role_title"], url=row["url"], location=row["location"] or "",
        jd_text=row["jd_text"] or "",
    )
    if not job.jd_text.strip():
        raise ValueError(
            "This job has no ad text saved, so there is nothing to tailor against. "
            "Open the link and paste the description in first."
        )

    jd_data = db.loads(row["jd_json"], {})
    jd = JDAnalysis(**jd_data) if jd_data.get("must_haves") else None

    # One signature project per company: never reuse one that is already the
    # signature on another live application.
    used = {
        r["signature_project"]
        for r in db.connect().execute(
            "SELECT signature_project FROM resumes WHERE signature_project != ''"
        ).fetchall()
    }

    research_md = _research_markdown(db.loads(row["research_json"], {}))
    res = await builder.build_and_save(
        job, jd=jd, exclude_projects=used, spec=spec, research_md=research_md,
    )

    db.connect().execute(
        "INSERT INTO resumes (id, job_id, company, role_title, folder, track,"
        " track_reason, signature_project, honesty_json, pages, status,"
        " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at,"
        " signature_project=excluded.signature_project, pages=excluded.pages",
        (res.folder, job_id, job.company, job.role_title, res.folder,
         (res.report or {}).get("track", ""), (res.report or {}).get("track_reason", ""),
         (res.report or {}).get("signature_project", ""),
         db.dumps(res.guards.as_dict() if res.guards else {}),
         (res.report or {}).get("fit", {}).get("pages", 0),
         "DRAFT", db.now(), db.now()),
    )

    fit = (res.report or {}).get("fit", {})
    return {
        "folder": res.folder,
        "company": job.company,
        "role_title": job.role_title,
        "report": res.report,
        "guards": res.guards.as_dict() if res.guards else {},
        "pages": fit.get("pages", 0),
        "short_of_target": fit.get("short_of_target", False),
        "message": (
            f"Built a resume for {job.company}. Every bullet came straight from your "
            "context files - open it to edit and download."
        ),
    }


def _research_markdown(data: dict[str, Any]) -> str:
    from ..api import routes
    return routes._research_markdown(data)


# --------------------------------------------------------------------------
# the brief
# --------------------------------------------------------------------------
async def run_brief(
    *, count: int | None = None, build_resumes: bool | None = None,
    titles: list[str] | None = None,
) -> dict[str, Any]:
    """
    One complete morning brief. Safe to call from the scheduler, the API or the
    command line, and safe to run twice in a day -- the tracker gate makes the
    second run surface only genuinely new roles.
    """
    cfg = settings.get_settings()
    count = count if count is not None else cfg.daily_job_count
    build = cfg.daily_build_resumes if build_resumes is None else build_resumes

    started = datetime.now()
    run = runner.start({"count": count, "titles": titles or []})
    await runner.wait(run.id)

    state = run.state()
    jobs = db.connect().execute(
        "SELECT j.id, j.company, j.role_title, a.tier, a.score"
        " FROM jobs j JOIN job_analysis a ON a.job_id = j.id"
        " WHERE a.run_id = ? AND a.verdict = 'KEEP'"
        " ORDER BY CASE a.tier WHEN 'S' THEN 0 WHEN 'A' THEN 1 WHEN 'B' THEN 2"
        "   ELSE 3 END, a.score DESC LIMIT ?",
        (run.id, count),
    ).fetchall()

    built: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    if build:
        for r in jobs:
            try:
                built.append(await tailor_job(r["id"]))
            except Exception as exc:  # noqa: BLE001 -- one bad ad must not stop the brief
                failed.append({
                    "company": r["company"], "role_title": r["role_title"],
                    "why": str(exc)[:300],
                })

    # write_env() reloads settings itself.
    settings.write_env({"DAILY_LAST_RUN": started.date().isoformat()})

    summary = {
        "run_id": run.id,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "status": state.get("status"),
        "found": len(jobs),
        "built": len(built),
        "failed": len(failed),
        "resumes": built,
        "problems": failed,
        "counts": state.get("counts", {}),
        "cost_usd": state.get("cost_usd", 0),
    }
    db.kv_set("last_brief", summary)
    db.kv_set("last_brief_error", None)   # a good run clears the last failure
    return summary


# NOTE: no scan-history row is written here on purpose. runner's persist phase
# already appends one for the scan this brief just ran, and adding a second
# double-counts found/kept/excluded in system/data/scan-history.tsv. How many
# resumes the brief built is recorded in the last_brief record above, and each
# one adds its own row to applications.tsv.


def last_brief() -> dict[str, Any] | None:
    return db.kv_get("last_brief", None)
