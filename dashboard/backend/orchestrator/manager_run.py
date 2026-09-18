"""
Running the hiring-manager agent as a tracked run, so the UI can watch it.

It is one long call -- web search plus deep reasoning, usually about a minute --
which is exactly long enough to look broken. So it reports three stages and
ticks an elapsed counter every five seconds, and it reuses the run/event
plumbing the scan already has rather than inventing a second progress channel.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from .. import db, settings
from ..agents import manager
from ..llm import registry
from ..llm.provider import QuotaExhausted
from ..models import JobPosting
from ..services import tectonic
from . import events

STAGES = [
    ("manager_read", "Reading the ad the way the hiring manager would"),
    ("manager_research", "Checking what this team actually runs"),
    ("manager_verdict", "Writing the bar a candidate has to clear"),
]

RUNS: dict[str, dict[str, Any]] = {}
_TASKS: dict[str, asyncio.Task] = {}


def _plan() -> list[dict[str, Any]]:
    return [{"key": k, "label": l, "status": "PENDING"} for k, l in STAGES]


async def _emit_stage(run_id: str, key: str, status: str, message: str = "") -> None:
    await events.emit(
        run_id, "stage_finished" if status in ("DONE", "SKIPPED") else "stage_started",
        stage=key, message=message, status=status,
    )


def start(job: JobPosting, job_id: str, research: Any = None) -> str:
    """Kick the agent off and hand back a run id the SSE stream understands."""
    run_id = "mgr-" + uuid4().hex[:10]

    # INSERT the runs row FIRST. run_events.run_id is a foreign key and
    # events.emit swallows insert failures, so skipping this produces a run that
    # streams live and replays nothing after a reconnect -- invisible until she
    # closes the laptop mid-run.
    db.connect().execute(
        "INSERT INTO runs (id, kind, status, params, stages, message, cost_usd,"
        " started_at, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (run_id, "manager", "RUNNING",
         db.dumps({"job_id": job_id, "company": job.company}),
         db.dumps(_plan()),
         f"Working out what {job.company} actually wants", 0.0, db.now(), db.now()),
    )

    RUNS[run_id] = {
        "id": run_id, "kind": "manager", "status": "RUNNING",
        "job_id": job_id, "company": job.company, "role_title": job.role_title,
        "stages": _plan(), "started_at": datetime.now().isoformat(timespec="seconds"),
        "message": f"Working out what {job.company} actually wants",
        "elapsed_seconds": 0, "cost_usd": 0.0, "error": None,
    }
    _TASKS[run_id] = asyncio.create_task(_execute(run_id, job, job_id, research))
    return run_id


def state(run_id: str) -> dict[str, Any] | None:
    if run_id in RUNS:
        return RUNS[run_id]
    r = db.connect().execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if r is None:
        return None
    return {
        "id": r["id"], "kind": r["kind"], "status": r["status"],
        "stages": db.loads(r["stages"], []), "message": r["message"],
        "error": r["error"], "cost_usd": r["cost_usd"],
        "started_at": r["started_at"], "finished_at": r["finished_at"],
    }


def _save_run(run_id: str, status: str, message: str = "", error: str | None = None) -> None:
    st = RUNS.get(run_id, {})
    db.connect().execute(
        "UPDATE runs SET status = ?, stages = ?, message = ?, error = ?,"
        " cost_usd = ?, finished_at = ? WHERE id = ?",
        (status, db.dumps(st.get("stages", [])), message or st.get("message", ""),
         error, st.get("cost_usd", 0.0),
         db.now() if status in ("DONE", "FAILED", "CANCELLED") else None, run_id),
    )


def _mark(run_id: str, key: str, status: str) -> None:
    for s in RUNS.get(run_id, {}).get("stages", []):
        if s["key"] == key:
            s["status"] = status


async def _execute(run_id: str, job: JobPosting, job_id: str, research: Any) -> None:
    started = datetime.now()
    events.restore_seq(run_id)
    await events.emit(run_id, "run_started", message=RUNS[run_id]["message"],
                      plan=RUNS[run_id]["stages"])

    provider = await registry.resolve()
    cfg = settings.get_settings()

    try:
        _mark(run_id, "manager_read", "DONE")
        await _emit_stage(run_id, "manager_read", "DONE", "Ad read")

        if not provider.supports_web_search:
            _mark(run_id, "manager_research", "SKIPPED")
            await _emit_stage(
                run_id, "manager_research", "SKIPPED",
                "This connection cannot search the web, so the verdict is based on "
                "the ad alone.",
            )
        else:
            _mark(run_id, "manager_research", "DONE")
            await _emit_stage(run_id, "manager_research", "DONE", "")

        _mark(run_id, "manager_verdict", "RUNNING")
        await _emit_stage(run_id, "manager_verdict", "RUNNING",
                          "Writing the bar a candidate has to clear")

        task = asyncio.create_task(
            manager.run(job, research=research, provider=provider)
        )
        # A minute of silence reads as a hang. Tick, so it reads as work.
        while True:
            done, _ = await asyncio.wait({task}, timeout=5.0)
            if done:
                break
            secs = int((datetime.now() - started).total_seconds())
            RUNS[run_id]["elapsed_seconds"] = secs
            await events.emit(
                run_id, "log", stage="manager_verdict",
                message=f"Still working - {secs}s so far",
            )

        verdict, sources, degraded, cost = task.result()

        manager.save(
            job, job_id, verdict, sources, degraded=degraded,
            provider=provider.name,
            model=(cfg.model_deep if provider.name == "anthropic" else ""),
            cost_usd=cost, run_id=run_id, jd_sha=tectonic.sha_of(job.jd_text or ""),
        )

        RUNS[run_id]["cost_usd"] = cost
        _mark(run_id, "manager_verdict", "DONE")
        RUNS[run_id]["status"] = "DONE"
        msg = (
            "Based on the ad alone - add an API key for the full verdict."
            if degraded else f"Here is what {job.company} is really asking for."
        )
        RUNS[run_id]["message"] = msg
        await _emit_stage(run_id, "manager_verdict", "DONE", msg)
        _save_run(run_id, "DONE", msg)

    except QuotaExhausted as exc:
        RUNS[run_id]["status"] = "WAITING_QUOTA"
        RUNS[run_id]["error"] = str(exc)
        _save_run(run_id, "WAITING_QUOTA", "Usage limit reached", str(exc))
        await events.emit(run_id, "quota_wait", message=str(exc))
    except Exception as exc:  # noqa: BLE001
        RUNS[run_id]["status"] = "FAILED"
        RUNS[run_id]["error"] = str(exc)[:400]
        _save_run(run_id, "FAILED", "Could not finish", str(exc)[:400])
        await events.emit(run_id, "error", message=str(exc)[:400])
    finally:
        RUNS[run_id]["elapsed_seconds"] = int((datetime.now() - started).total_seconds())
        # run_finished is what terminates the SSE subscription.
        await events.emit(run_id, "run_finished", message=RUNS[run_id].get("message", ""))
