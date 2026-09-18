"""
The HTTP surface.

Everything the two tabs need. Deliberately small: the frontend is a view over
the pipeline, and any logic that matters lives in services/ and agents/ where
it can be tested without a browser.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from .. import db, legacy, paths, settings
from ..llm import registry
from ..models import TIER_LABEL
from ..orchestrator import events, runner
from ..services import (
    context_loader, factbank, guards, latex_render, resume_rules, resume_spec,
    sponsor_index, tectonic, workspace_sync,
)

router = APIRouter(prefix="/api")

# Background brief tasks are held here so they are not garbage collected
# mid-run: asyncio keeps only a weak reference to a bare create_task().
_BRIEF_TASKS: list[asyncio.Task] = []


def _annotate_ats(ats: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Mark which missing keywords she can truthfully add right now, so the
    Suggestions panel can offer a one-click "Add" only where it is honest --
    everything else stays a plain gap for the study plan to cover.
    """
    if not ats:
        return ats
    fb = context_loader.load()
    for row in ats.get("rows", []):
        row["claimable"] = row["count"] == 0 and fb.claimable(row["term"])
    return ats


# --------------------------------------------------------------------------
# health and settings
# --------------------------------------------------------------------------
@router.get("/health")
async def health() -> dict[str, Any]:
    cfg = settings.get_settings()
    llm = await registry.health()
    return {
        "ok": True,
        "llm": llm,
        "engine": tectonic.engine_status(),
        "sponsor_index": sponsor_index.stats(),
        "workspace": {
            "context_files": len(context_loader.load().files),
            "applications_tsv": paths.APPLICATIONS_TSV.exists(),
            "output_folders": len(workspace_sync.list_applications()),
        },
        "sources": {
            "ats_boards": cfg.enable_ats_boards,
            "feeds": cfg.enable_feeds,
            "workspace_import": cfg.enable_workspace_import,
            "adzuna": bool(cfg.enable_adzuna and cfg.adzuna_app_id),
            "usajobs": bool(cfg.enable_usajobs and cfg.usajobs_email),
        },
    }


@router.get("/settings")
async def get_settings_api() -> dict[str, Any]:
    cfg = settings.get_settings()
    return {
        "key_set": cfg.has_key(),
        "key_hint": cfg.key_hint(),
        "llm_provider": cfg.llm_provider,
        "models": {"deep": cfg.model_deep, "mid": cfg.model_mid, "fast": cfg.model_fast},
        "sources": {
            "enable_ats_boards": cfg.enable_ats_boards,
            "enable_feeds": cfg.enable_feeds,
            "enable_workspace_import": cfg.enable_workspace_import,
            "enable_adzuna": cfg.enable_adzuna,
            "enable_usajobs": cfg.enable_usajobs,
            "enable_web_discovery": cfg.enable_web_discovery,
            "adzuna_app_id": cfg.adzuna_app_id,
            "usajobs_email": cfg.usajobs_email,
        },
        "behaviour": {
            "default_job_count": cfg.default_job_count,
            "verify_links": cfg.verify_links,
        },
    }


@router.put("/settings")
async def put_settings(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    mapping = {
        "llm_provider": "LLM_PROVIDER",
        "enable_ats_boards": "ENABLE_ATS_BOARDS",
        "enable_feeds": "ENABLE_FEEDS",
        "enable_workspace_import": "ENABLE_WORKSPACE_IMPORT",
        "enable_adzuna": "ENABLE_ADZUNA",
        "enable_usajobs": "ENABLE_USAJOBS",
        "enable_web_discovery": "ENABLE_WEB_DISCOVERY",
        "adzuna_app_id": "ADZUNA_APP_ID",
        "adzuna_app_key": "ADZUNA_APP_KEY",
        "usajobs_email": "USAJOBS_EMAIL",
        "default_job_count": "DEFAULT_JOB_COUNT",
        "verify_links": "VERIFY_LINKS",
    }
    for k, env in mapping.items():
        if k in payload:
            v = payload[k]
            updates[env] = str(v).lower() if isinstance(v, bool) else v
    if updates:
        settings.write_env(updates)
    registry.invalidate()
    return await get_settings_api()


@router.post("/settings/key")
async def set_key(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    key = (payload.get("key") or "").strip()
    if not key:
        settings.clear_key()
        registry.invalidate()
        return {"ok": True, "message": "Key removed.", "key_set": False}

    ok, why = settings.save_key(key)
    if not ok:
        return {"ok": False, "message": why, "key_set": False}

    registry.invalidate()
    provider = await registry.resolve(force=True)
    verified, msg = (True, "Key saved.")
    if hasattr(provider, "verify"):
        verified, msg = await provider.verify()
    return {
        "ok": verified, "message": msg,
        "key_set": settings.get_settings().has_key(),
        "key_hint": settings.get_settings().key_hint(),
    }


@router.post("/settings/test-key")
async def test_key() -> dict[str, Any]:
    provider = await registry.resolve(force=True)
    if hasattr(provider, "verify"):
        ok, msg = await provider.verify()
        return {"ok": ok, "message": msg}
    ok, why = await provider.available()
    return {"ok": ok, "message": why or "Ready."}


# --------------------------------------------------------------------------
# runs
# --------------------------------------------------------------------------
@router.post("/runs")
async def start_run(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    run = runner.start({
        "count": int(payload.get("count") or settings.get_settings().default_job_count),
        "titles": payload.get("titles") or None,
    })
    return run.state()


@router.get("/runs")
async def list_runs(limit: int = Query(20, le=100)) -> list[dict[str, Any]]:
    rows = db.connect().execute(
        "SELECT id, kind, status, message, error, cost_usd, started_at, finished_at,"
        " created_at FROM runs ORDER BY created_at DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    run = runner.get(run_id)
    if run:
        return run.state()
    row = db.connect().execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "No such run.")
    d = dict(row)
    d["stages"] = db.loads(d.get("stages"), [])
    d["params"] = db.loads(d.get("params"), {})
    return d


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, Any]:
    return {"cancelled": runner.cancel(run_id)}


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, after: int = Query(0)) -> StreamingResponse:
    """
    Server-sent events. Reconnect with ?after=<last seq> and nothing is missed --
    closing the laptop lid mid-run must not lose progress.
    """
    async def stream():
        try:
            async for ev in events.subscribe(run_id, after):
                yield f"id: {ev.get('seq', 0)}\nevent: {ev['type']}\ndata: {json.dumps(ev)}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------------------------------------------------------
# jobs
# --------------------------------------------------------------------------
@router.get("/jobs")
async def list_jobs(
    limit: int = Query(50, le=200), tier: str | None = None, min_score: float = 0,
) -> list[dict[str, Any]]:
    # Only the most recent scan. Results from an earlier run were produced by
    # older filters and older rules, and mixing them in would resurrect jobs a
    # later scan deliberately dropped.
    latest = db.connect().execute(
        "SELECT id FROM runs WHERE status IN ('DONE','WAITING_QUOTA')"
        " ORDER BY created_at DESC LIMIT 1"
    ).fetchone()

    sql = (
        "SELECT j.*, a.tier, a.verdict, a.reason_label, a.triggering_sentence,"
        " a.everify, a.cap_exempt, a.h1b_approvals, a.link_status, a.score,"
        " a.score_json, a.jd_json, a.research_json, a.prediction_json,"
        " a.recommendation, a.ghost_flags, a.updated_at AS analysed_at"
        " FROM jobs j JOIN job_analysis a ON a.job_id = j.id"
        " WHERE a.score >= ?"
    )
    params: list[Any] = [min_score]
    if latest:
        sql += " AND a.run_id = ?"
        params.append(latest["id"])
    if tier:
        sql += " AND a.tier = ?"
        params.append(tier)
    sql += " ORDER BY CASE a.tier WHEN 'S' THEN 0 WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END, a.score DESC LIMIT ?"
    params.append(limit)

    rows = db.connect().execute(sql, params).fetchall()
    return [_job_row(r) for r in rows]


# The job id is taken from the BODY, not the path. Job ids contain colons and
# spaces ("workspace:summary-University of ..."), and a {job_id:path} converter
# is greedy enough to swallow a "/tailor" suffix, which surfaces as a confusing
# 405 rather than a route miss.
@router.post("/tailor")
async def tailor(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    Build a tailored resume for one job.

    The work itself lives in orchestrator/daily.tailor_job, because the 09:00
    brief builds resumes too and a second implementation here would drift from
    it. This route is the button; that function is the behaviour.
    """
    from ..orchestrator import daily

    job_id = (payload.get("job_id") or "").strip()
    if not job_id:
        raise HTTPException(400, "Which job? Send a job_id.")
    try:
        return await daily.tailor_job(job_id)
    except ValueError as exc:
        raise HTTPException(
            404 if "No such job" in str(exc) else 400, str(exc)
        ) from None


@router.get("/jobs/{job_id:path}")
async def get_job(job_id: str) -> dict[str, Any]:
    row = db.connect().execute(
        "SELECT j.*, a.* FROM jobs j LEFT JOIN job_analysis a ON a.job_id = j.id"
        " WHERE j.id = ?", (job_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "No such job.")
    d = _job_row(row)
    d["jd_text"] = row["jd_text"]
    return d


def _job_row(r: Any) -> dict[str, Any]:
    tier = r["tier"] or "C"
    return {
        "id": r["id"], "source": r["source"], "company": r["company"],
        "role_title": r["role_title"], "url": r["url"], "location": r["location"],
        "remote": bool(r["remote"]), "department": r["department"],
        "posted_at": r["posted_at"], "jd_chars": len(r["jd_text"] or ""),
        "tier": tier, "tier_label": TIER_LABEL.get(tier, ""),
        "verdict": r["verdict"], "reason_label": r["reason_label"],
        "triggering_sentence": r["triggering_sentence"],
        "everify": bool(r["everify"]), "cap_exempt": bool(r["cap_exempt"]),
        "h1b_approvals": r["h1b_approvals"], "link_status": r["link_status"],
        "score": r["score"], "score_detail": db.loads(r["score_json"], {}),
        "jd": db.loads(r["jd_json"], {}), "research": db.loads(r["research_json"], {}),
        "prediction": db.loads(r["prediction_json"], {}),
        "recommendation": r["recommendation"],
        "ghost_flags": db.loads(r["ghost_flags"], []),
    }


@router.get("/excluded")
async def list_excluded(limit: int = Query(100, le=500)) -> list[dict[str, Any]]:
    """Every drop, with the sentence that caused it, so a wrong call is visible."""
    rows = db.connect().execute(
        "SELECT company, role_title, url, stage, why, triggering_sentence, at"
        " FROM excluded ORDER BY id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# resumes
# --------------------------------------------------------------------------
@router.get("/resumes")
async def list_resumes() -> list[dict[str, Any]]:
    return workspace_sync.list_applications()


@router.get("/resumes/{folder}")
async def get_resume(folder: str) -> dict[str, Any]:
    base = paths.OUTPUT / folder
    tex = base / "resume.tex"
    if not tex.exists():
        raise HTTPException(404, "No resume in that folder.")

    source = paths.read_text(tex)
    jd = paths.read_text(base / "job-description.txt")
    row = next((r for r in workspace_sync.list_applications() if r["folder"] == folder), {})

    spec = resume_spec.effective(folder)
    _rendered, ship_sha = resume_spec.shas(folder)
    report = guards.run_all(source, jd_text=jd, study_plan=paths.read_text(base / "study-plan.md"))
    ats = _annotate_ats(legacy.ats_score(source, jd) if jd.strip() else {"score": 0, "rows": [], "missing": []})

    return {
        **row,
        "folder": folder,
        "tex": source,
        "jd_text": jd,
        "research": paths.read_text(base / "research.md"),
        "study_plan": paths.read_text(base / "study-plan.md"),
        "audit": paths.read_text(base / "audit.md"),
        "guards": report.as_dict(),
        "ats": ats,
        "anchors": guards.anchor_map(source),
        "has_pdf": (base / "resume.pdf").exists(),
        "spec": spec.as_dict(),
        "pages_target": spec.pages_target,
        "rules": [r.as_dict() for r in resume_rules.effective(folder)],
        # Server truth, so the Download button survives a page reload instead of
        # silently re-locking or, worse, staying unlocked after an AI edit.
        "ship_ok": bool(ship_sha) and ship_sha == tectonic.sha_of(source),
    }


@router.put("/resumes/{folder}")
async def save_resume(folder: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    tex = (payload.get("tex") or "").strip()
    if not tex:
        raise HTTPException(400, "Nothing to save.")
    base = paths.OUTPUT / folder
    if not base.exists():
        raise HTTPException(404, "No such application folder.")
    workspace_sync.atomic_write(base / "resume.tex", tex + ("\n" if not tex.endswith("\n") else ""))
    # Any edit invalidates the last ship approval, so Download re-locks.
    resume_spec.clear_ship(folder)
    return {"ok": True, "saved_at": db.now(), "ship_ok_reset": True}


@router.post("/resumes/{folder}/compile")
async def compile_resume(folder: str, payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    """
    draft -- compiles anything, reports problems as warnings. Used by the editor.
    ship  -- the real gate: markers and a page count other than 1 are errors.
             Only a passing ship compile enables Download.
    """
    mode = payload.get("mode", "draft")
    base = paths.OUTPUT / folder
    tex = payload.get("tex")
    if tex is None:
        tex = paths.read_text(base / "resume.tex")
    if not tex.strip():
        raise HTTPException(400, "There is nothing to build.")

    # The page target is per-resume now: the exact-page gate still runs, it
    # just runs against her chosen number instead of a hard-coded 1.
    spec = resume_spec.effective(folder)
    out = await tectonic.compile_debounced(
        tex, resume_id=folder, mode=mode, return_pdf=True,
        want_pages=spec.pages_target,
        allow_fewer=(mode != "ship" and spec.pages_target > 1),
    )

    jd = paths.read_text(base / "job-description.txt")
    report = guards.run_all(
        tex, jd_text=jd, study_plan=paths.read_text(base / "study-plan.md")
    )
    result = out.as_dict()
    result["guards"] = report.as_dict()
    result["ats"] = _annotate_ats(legacy.ats_score(tex, jd) if jd.strip() else None)
    # A blocking guard violation must stop a ship build, even if LaTeX is happy.
    if mode == "ship" and not report.ok:
        result["ok"] = False
        result["problems"] = result.get("problems", []) + [
            {"severity": "error", "kind": v.kind, "line": v.line,
             "message": v.message, "raw": v.evidence}
            for v in report.blockers
        ]
    if result["ok"] and mode == "ship" and out.pdf_path:
        import shutil
        shutil.copyfile(out.pdf_path, base / "resume.pdf")
        # Record WHAT passed, not merely that something did. Download then
        # survives a reload, and re-locks the moment the file changes.
        resume_spec.set_ship(folder, tectonic.sha_of(tex))
    elif mode == "ship":
        resume_spec.clear_ship(folder)
    result["ship_ok"] = bool(result["ok"] and mode == "ship")
    result["pages_target"] = spec.pages_target
    return result


# Two safe, mechanical fixes the "Suggested improvements" panel can apply on
# her behalf -- both are deterministic text surgery (see latex_render.py), not
# an LLM rewrite, so neither one can put a new claim on the page. Anything
# that would require judgment (a hedged claim, a banned phrase inside a
# sentence) is left for her to edit by hand.
@router.post("/resumes/{folder}/apply-suggestion")
async def apply_suggestion(folder: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    base = paths.OUTPUT / folder
    tex_path = base / "resume.tex"
    if not tex_path.exists():
        raise HTTPException(404, "No such application folder.")

    action = payload.get("action")
    tex = paths.read_text(tex_path)

    try:
        if action == "add_keyword":
            keyword = (payload.get("keyword") or "").strip()
            if not keyword:
                raise HTTPException(400, "Which keyword?")
            fb = context_loader.load()
            if not fb.claimable(keyword):
                raise HTTPException(
                    400,
                    f"'{keyword}' is not on your Strong or Used-it skills list yet, "
                    "so it can't be added truthfully. Add it to context/05-skills.md "
                    "first, from the Profile tab, once it is genuinely true.",
                )
            new_tex = latex_render.add_skill_keyword(tex, keyword)
        elif action == "remove_block":
            block_id = (payload.get("block_id") or "").strip()
            if not block_id:
                raise HTTPException(400, "Which line?")
            new_tex = latex_render.remove_block(tex, block_id)
        else:
            raise HTTPException(400, f"Unknown suggestion action '{action}'.")
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    workspace_sync.atomic_write(tex_path, new_tex)
    resume_spec.clear_ship(folder)

    spec = resume_spec.effective(folder)
    jd = paths.read_text(base / "job-description.txt")
    out = await tectonic.compile_debounced(
        new_tex, resume_id=folder, mode="draft", return_pdf=True,
        want_pages=spec.pages_target, allow_fewer=spec.pages_target > 1,
    )
    report = guards.run_all(
        new_tex, jd_text=jd, study_plan=paths.read_text(base / "study-plan.md")
    )
    result = out.as_dict()
    result["guards"] = report.as_dict()
    result["ats"] = _annotate_ats(legacy.ats_score(new_tex, jd) if jd.strip() else None)
    result["tex"] = new_tex
    result["ship_ok_reset"] = True
    return result


@router.get("/resumes/{folder}/pdf")
async def resume_pdf(folder: str) -> FileResponse:
    pdf = paths.OUTPUT / folder / "resume.pdf"
    if not pdf.exists():
        raise HTTPException(404, "No PDF has been built yet.")
    row = next((r for r in workspace_sync.list_applications() if r["folder"] == folder), {})
    name = f"Annie_Manoharan_{(row.get('role_title') or 'Resume').replace(' ', '_')}.pdf"
    return FileResponse(pdf, media_type="application/pdf", filename=name)


@router.get("/resumes/{folder}/tex")
async def resume_tex(folder: str) -> FileResponse:
    tex = paths.OUTPUT / folder / "resume.tex"
    if not tex.exists():
        raise HTTPException(404, "No source in that folder.")
    return FileResponse(tex, media_type="text/plain", filename=f"{folder}.tex")


# --------------------------------------------------------------------------
# profile and tracker
# --------------------------------------------------------------------------
# What each context/ file governs -- shown as a caption in the Profile tab so
# she knows what she is editing without opening CLAUDE.md.
PROFILE_FILE_INFO: dict[str, str] = {
    "01-basics.md": "Your name, contact details and work authorization. Checked before any job is ever shown.",
    "02-education.md": "Degrees, university, graduation date and the full module list.",
    "03-experience.md": "Every job, internship and research role. Every resume bullet traces back to a line here.",
    "04-projects.md": "The project bank a signature project is chosen from for each company.",
    "05-skills.md": "Skills at three honesty levels: Strong, Used it, Touched it -- plus the gaps you never claim.",
    "06-achievements.md": "Certifications, awards and publications.",
    "07-preferences.md": "Steers the whole search: job titles, locations, and your hard limits.",
    "08-voice.md": "Tone and wording to avoid, and anything that needs to be handled carefully.",
    "09-anything-else.md": "Notes on your resume variants and anything else worth knowing.",
    "QUESTIONS-FOR-YOU.md": "Open questions that block specific resume claims until you answer them.",
}

PROFILE_FILE_NAMES: list[str] = [*context_loader.CONTEXT_ORDER, "QUESTIONS-FOR-YOU.md"]


@router.get("/profile/files")
async def profile_files() -> list[dict[str, Any]]:
    """Her context files, plain text, for the Profile tab to list and edit."""
    out = []
    for name in PROFILE_FILE_NAMES:
        p = paths.QUESTIONS if name == "QUESTIONS-FOR-YOU.md" else paths.CONTEXT / name
        content = paths.read_text(p)
        out.append({
            "name": name,
            "description": PROFILE_FILE_INFO.get(name, ""),
            "content": content,
            "chars": len(content),
            "exists": p.exists(),
        })
    return out


@router.put("/profile/files/{name}")
async def save_profile_file(name: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    She edits, we save -- this is the one sanctioned way the dashboard writes
    to context/. Nothing here is inferred or generated; it is her own text.
    """
    if name not in PROFILE_FILE_NAMES:
        raise HTTPException(400, "That is not one of your context files.")
    content = payload.get("content")
    if content is None:
        raise HTTPException(400, "Nothing to save.")

    p = paths.QUESTIONS if name == "QUESTIONS-FOR-YOU.md" else paths.CONTEXT / name
    workspace_sync.atomic_write(p, content if content.endswith("\n") else content + "\n")

    # Every resume, guard and ranking decision reads a cached snapshot of these
    # files -- without this they would keep working from what she just edited.
    context_loader.load(force=True)
    factbank.load(force=True)
    return {"ok": True, "saved_at": db.now(), "chars": len(content)}


@router.get("/profile")
async def profile() -> dict[str, Any]:
    fb = context_loader.load()
    return {
        "files": {k: len(v) for k, v in fb.files.items()},
        "skills": {
            "strong": sorted(fb.skills_strong),
            "used_it": sorted(fb.skills_used),
            "touched_it": sorted(fb.skills_touched),
            "honest_gaps": sorted(fb.skills_gap),
        },
        "open_questions": [q for q in context_loader.open_questions() if not q["answered"]][:14],
        "blocked_claims": context_loader.blocked_claims(),
    }


@router.get("/tracker")
async def tracker() -> dict[str, Any]:
    legacy.refresh_today()
    rows = legacy.load_applications()
    pairs, companies, reasons = legacy.exclusions()
    return {
        "applications": rows,
        "exclusions": {
            "pairs": [list(p) for p in sorted(pairs)],
            "companies": sorted(companies),
            "reasons": reasons,
        },
        "rules": {
            "ghost_after_days": legacy.GHOST_AFTER_DAYS,
            "reject_cooldown_days": legacy.REJECT_COOLDOWN_DAYS,
            "ghost_cooldown_days": legacy.GHOST_COOLDOWN_DAYS,
        },
    }


@router.post("/tracker/{app_id}/status")
async def set_app_status(app_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    status = (payload.get("status") or "").upper()
    if status not in legacy.OPEN_STATUSES | legacy.CLOSED_STATUSES:
        raise HTTPException(400, f"Unknown status '{status}'.")
    ok = workspace_sync.set_status(app_id, status, payload.get("note", ""))
    if ok:
        workspace_sync.sync_applied_companies()
    return {"ok": ok}


@router.get("/summary")
async def summary() -> dict[str, Any]:
    return {"markdown": paths.read_text(paths.SUMMARY)}


# --------------------------------------------------------------------------
# the morning brief, the schedule, and the portable project pack
# --------------------------------------------------------------------------
@router.get("/schedule")
async def get_schedule() -> dict[str, Any]:
    from .. import scheduler
    from ..orchestrator import daily
    st = scheduler.status()
    st["last_brief"] = daily.last_brief()
    return st


@router.put("/schedule")
async def put_schedule(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Turn the 09:00 brief on or off, and say how many jobs it should bring."""
    from .. import scheduler

    updates: dict[str, Any] = {}
    if "enabled" in payload:
        updates["DAILY_ENABLED"] = "true" if payload["enabled"] else "false"
    if "at" in payload:
        raw = str(payload["at"] or "").strip()
        if not re.fullmatch(r"[0-2]?\d:[0-5]\d", raw):
            raise HTTPException(400, "Give the time as HH:MM, like 09:00.")
        updates["DAILY_AT"] = scheduler.parse_at(raw).strftime("%H:%M")
    if "count" in payload:
        try:
            n = int(payload["count"])
        except (TypeError, ValueError):
            raise HTTPException(400, "How many jobs? Send a number.") from None
        updates["DAILY_JOB_COUNT"] = str(max(1, min(25, n)))
    if "build_resumes" in payload:
        updates["DAILY_BUILD_RESUMES"] = "true" if payload["build_resumes"] else "false"

    if updates:
        settings.write_env(updates)
    return scheduler.status()


@router.post("/brief")
async def start_brief(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
    """
    Run the brief now, in the background, and hand back the run id so the same
    SSE stream the Job Hunter already uses can show its progress.
    """
    from ..orchestrator import daily

    count = payload.get("count")
    build = payload.get("build_resumes")
    task = asyncio.create_task(
        daily.run_brief(
            count=int(count) if count else None,
            build_resumes=None if build is None else bool(build),
        )
    )
    _BRIEF_TASKS.append(task)
    task.add_done_callback(_brief_finished)
    return {
        "started": True,
        "message": (
            "Finding jobs and building a resume for each one. This takes a few "
            "minutes — you can leave this page."
        ),
    }


def _brief_finished(task: asyncio.Task) -> None:
    """
    Retrieve the result, so a crash is reported instead of vanishing.

    Without this the exception is never fetched: asyncio grumbles into the log
    at garbage-collection time and the UI shows a brief that simply never
    produced anything, which is indistinguishable from one that never ran.
    """
    if task in _BRIEF_TASKS:
        _BRIEF_TASKS.remove(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        db.kv_set("last_brief_error", {
            "error": str(exc)[:500],
            "at": db.now(),
        })


@router.get("/brief")
async def read_brief() -> dict[str, Any]:
    from ..orchestrator import daily

    return {
        "last": daily.last_brief(),
        "running": bool(_BRIEF_TASKS),
        "last_error": db.kv_get("last_brief_error", None),
    }


@router.post("/pack")
async def build_pack() -> dict[str, Any]:
    """
    Rebuild the project pack: the folder she uploads to a Claude or ChatGPT
    project so the whole system works on a subscription, with no key.
    """
    import importlib.util

    script = paths.ROOT / "system" / "scripts" / "export_project_pack.py"
    if not script.exists():
        raise HTTPException(500, "The pack exporter is missing from system/scripts.")

    spec = importlib.util.spec_from_file_location("export_project_pack", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    dest = paths.OUTPUT / "project-pack"
    written = await asyncio.to_thread(mod.build_pack, dest, True)
    return {
        "folder": str(dest),
        "zip": str(dest.parent / "project-pack.zip"),
        "files": [{"name": p.name, "kb": round(p.stat().st_size / 1024, 1)} for p in written],
        "message": (
            "Project pack rebuilt. Upload these files to a Claude or ChatGPT project "
            "and paste INSTRUCTIONS.md into the project instructions."
        ),
    }


# --------------------------------------------------------------------------
# bringing a Claude / ChatGPT project answer back in
# --------------------------------------------------------------------------
@router.post("/ingest/preview")
async def ingest_preview(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    Read what she pasted and show what would be saved, without saving it.

    The paste came from a language model, so nothing it claims about
    eligibility is believed: the sponsorship gate and the tracker gate are
    re-run here, and every link stays unverified until checked.
    """
    from ..services import ingest

    text = payload.get("text") or ""
    origin = (payload.get("origin") or "pasted").strip()[:40] or "pasted"
    try:
        return await asyncio.to_thread(ingest.preview, text, origin=origin)
    except ingest.IngestError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post("/ingest/save")
async def ingest_save(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Save the jobs from a pasted answer so they rank beside scanned ones."""
    from ..services import ingest

    text = payload.get("text") or ""
    origin = (payload.get("origin") or "pasted").strip()[:40] or "pasted"
    try:
        rows = await asyncio.to_thread(ingest.parse, text)
        screened = await asyncio.to_thread(
            ingest.screen, ingest.to_postings(rows, origin=origin)
        )
        result = await asyncio.to_thread(ingest.save, screened, origin=origin)
    except ingest.IngestError as exc:
        raise HTTPException(400, str(exc)) from None

    saved = result["saved"]
    return {
        **result,
        "message": (
            f"Imported {saved} job{'' if saved == 1 else 's'}. "
            "They are ranked with everything else - check the links before you apply."
            if saved else
            "Nothing new was imported. Everything in that answer was either already "
            "in your tracker or ruled out by the sponsorship gate."
        ),
    }


# --------------------------------------------------------------------------
# the hiring manager's bar -- computed without her profile
# --------------------------------------------------------------------------
def _job_posting(job_id: str):
    """The JobPosting plus its stored research, or a 404 she can act on."""
    from ..models import CompanyResearch, JobPosting

    row = db.connect().execute(
        "SELECT j.*, a.research_json FROM jobs j"
        " LEFT JOIN job_analysis a ON a.job_id = j.id WHERE j.id = ?",
        (job_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "No such job.")

    job = JobPosting(
        source=row["source"], source_id=row["source_id"], company=row["company"],
        role_title=row["role_title"], url=row["url"], location=row["location"] or "",
        jd_text=row["jd_text"] or "",
    )
    data = db.loads(row["research_json"], {})
    research = None
    if data.get("what_they_do"):
        try:
            research = CompanyResearch(**data)
        except Exception:  # noqa: BLE001 -- research is optional context
            research = None
    return job, research


# job_id goes in the BODY for the same reason it does on /tailor: ids contain
# colons and spaces, and a greedy {job_id:path} converter swallows a suffix.
@router.post("/manager")
async def manager_start(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    What does the hiring manager actually want?

    Cached permanently per job: this is an expensive call and the answer does
    not change unless the ad does. A verdict produced without a model is
    re-run once a model becomes available.
    """
    from ..agents import manager
    from ..orchestrator import manager_run

    job_id = (payload.get("job_id") or "").strip()
    if not job_id:
        raise HTTPException(400, "Which job? Send a job_id.")
    force = bool(payload.get("force"))

    job, research = _job_posting(job_id)
    if not (job.jd_text or "").strip():
        raise HTTPException(
            400,
            "This job has no ad text saved, so there is nothing for a hiring manager "
            "to react to. Open the link and paste the description in first.",
        )

    cached = manager.load(job_id)
    if cached and not force:
        stale = cached.get("jd_sha") and cached["jd_sha"] != tectonic.sha_of(job.jd_text)
        # A verdict written without a model is a placeholder, not an answer.
        if not cached["degraded"] and not stale:
            return {"cached": True, **cached}

    run_id = manager_run.start(job, job_id, research)
    return {
        "cached": False,
        "run_id": run_id,
        "status": "RUNNING",
        "message": f"Working out what {job.company} is really asking for.",
    }


@router.get("/manager/{job_id:path}")
async def manager_get(job_id: str) -> dict[str, Any]:
    from ..agents import manager

    cached = manager.load(job_id)
    if not cached:
        raise HTTPException(404, "No hiring-manager verdict for that job yet.")

    row = db.connect().execute("SELECT jd_text FROM jobs WHERE id = ?", (job_id,)).fetchone()
    stale = bool(
        row and cached.get("jd_sha")
        and cached["jd_sha"] != tectonic.sha_of(row["jd_text"] or "")
    )
    return {**cached, "stale": stale}


# --------------------------------------------------------------------------
# talking to the resume
# --------------------------------------------------------------------------
def _folder_or_404(folder: str):
    base = paths.OUTPUT / folder
    if not (base / "resume.tex").exists():
        raise HTTPException(404, "No resume in that folder.")
    return base


@router.post("/resumes/{folder}/chat")
async def resume_chat_turn(folder: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """
    One turn: plain English in, a changed resume or an honest refusal out.

    The model chooses from her real material; it never writes a word that
    reaches the page, and the guards run before anything is saved.
    """
    from ..agents import resume_chat

    _folder_or_404(folder)
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "Type what you would like changed.")

    lowered = message.lower()
    confirm = bool(payload.get("confirm_rebuild")) or "rebuild anyway" in lowered
    try:
        return await resume_chat.turn(folder, message, confirm_rebuild=confirm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.get("/resumes/{folder}/chat")
async def resume_chat_history(folder: str) -> dict[str, Any]:
    from ..agents import resume_chat

    _folder_or_404(folder)
    return {"turns": resume_chat.history(folder)}


@router.delete("/resumes/{folder}/chat")
async def resume_chat_clear(folder: str) -> dict[str, Any]:
    """Clears the transcript only. The resume itself is untouched."""
    from ..agents import resume_chat

    _folder_or_404(folder)
    resume_chat.clear(folder)
    return {"cleared": True, "message": "Cleared the conversation. Your resume is unchanged."}


@router.post("/resumes/{folder}/chat/{turn_id}/undo")
async def resume_chat_undo(folder: str, turn_id: int) -> dict[str, Any]:
    from ..agents import resume_chat
    from ..services import resume_spec

    base = _folder_or_404(folder)
    try:
        restored = resume_chat.undo(folder, turn_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None

    workspace_sync.atomic_write(base / "resume.tex", restored)
    resume_spec.clear_ship(folder)
    spec = resume_spec.effective(folder)
    out = await tectonic.compile_tex(
        restored, mode="draft", resume_id=f"{folder}-undo",
        want_pages=spec.pages_target, allow_fewer=spec.pages_target > 1,
        return_pdf=True,
    )
    return {
        "tex": restored, "ok": out.ok, "pages": out.pages, "pdf_b64": out.pdf_b64,
        "problems": out.problems, "ship_ok_reset": True,
        "message": "Put it back the way it was.",
    }


# --------------------------------------------------------------------------
# the rules box
# --------------------------------------------------------------------------
@router.get("/resumes/{folder}/rules")
async def rules_list(folder: str) -> dict[str, Any]:
    from ..agents import edit_ops, resume_chat
    from ..services import resume_rules, resume_spec

    _folder_or_404(folder)
    rules = resume_rules.effective(folder)
    try:
        cat = resume_chat.build_context(folder)["catalogue"]
        stale = set(edit_ops.stale_rules(rules, cat))
    except Exception:  # noqa: BLE001
        stale = set()

    def shape(r):
        d = r.as_dict()
        d["stale"] = r.id in stale
        return d

    return {
        "folder": [shape(r) for r in resume_rules.for_folder(folder)],
        "global": [shape(r) for r in resume_rules.globals_()],
        "spec": resume_spec.effective(folder).as_dict(),
    }


@router.post("/resumes/{folder}/rules")
async def rules_add(folder: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    from ..agents import edit_ops
    from ..services import resume_rules

    _folder_or_404(folder)
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "What is the rule?")
    op = (payload.get("op") or "").strip()
    if op and op not in edit_ops.SPEC_OPS | edit_ops.TEX_OPS:
        raise HTTPException(400, f"{op} is not something I can enforce.")
    r = resume_rules.add(
        text=text, op=op, args=payload.get("args") or {},
        scope=payload.get("scope") or "folder", folder=folder, source="manual",
    )
    return r.as_dict()


@router.patch("/resumes/{folder}/rules/{rule_id}")
async def rules_update(
    folder: str, rule_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    from ..services import resume_rules

    _folder_or_404(folder)
    try:
        return resume_rules.update(
            rule_id,
            text=payload.get("text"), enabled=payload.get("enabled"),
            position=payload.get("position"),
        ).as_dict()
    except KeyError:
        raise HTTPException(404, "No such rule.") from None


@router.delete("/resumes/{folder}/rules/{rule_id}")
async def rules_delete(folder: str, rule_id: int) -> dict[str, Any]:
    from ..services import resume_rules

    _folder_or_404(folder)
    resume_rules.delete(rule_id)
    return {"deleted": True}


@router.post("/resumes/{folder}/rebuild")
async def resume_rebuild(folder: str) -> dict[str, Any]:
    """Re-apply the spec and every rule, with no chat turn."""
    from ..agents import builder, resume_chat
    from ..services import resume_spec

    base = _folder_or_404(folder)
    ctx = resume_chat.build_context(folder)
    spec = resume_spec.effective(folder)

    res = await builder.build(
        ctx["job"], jd=resume_chat._jd_for(folder), spec=spec, resume_id=f"{folder}-rebuild",
    )
    report = guards.run_all(
        res.tex, jd_text=ctx["jd"], study_plan=ctx["study"], fb=ctx["fb"]
    )
    if report.blockers:
        raise HTTPException(
            400,
            "That rebuild would put an unsupported claim on the page, so I stopped.",
        )

    workspace_sync.atomic_write(base / "resume.tex", res.tex)
    resume_spec.save(
        folder, spec, rendered_sha=tectonic.sha_of(res.tex), ship_sha="",
    )
    fit = (res.report or {}).get("fit", {})
    return {
        "tex": res.tex, "spec": spec.as_dict(), "guards": report.as_dict(),
        "pages": fit.get("pages", 0), "short_of_target": fit.get("short_of_target", False),
        "ship_ok_reset": True,
        "message": fit.get("note") or "Rebuilt from your context files.",
    }
