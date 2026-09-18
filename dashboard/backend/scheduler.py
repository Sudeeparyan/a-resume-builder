"""
The 09:00 alarm clock. No new dependency, no cron syntax to learn.

One asyncio task wakes every 30 seconds, compares the wall clock against
daily_at, and fires the morning brief once per day. It is deliberately dumber
than a cron library because the failure mode that matters here is "the laptop
was asleep at 09:00", and no in-process scheduler survives that.

So the rule is: fire when the time has PASSED and today's brief has not run
yet. Open the laptop at 11:00 and the brief still runs, which is what she
actually wants. For a truly unattended run, use the Windows Task Scheduler
entry that cli.py prints -- that works with the app closed.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import date, datetime, time as dtime
from typing import Any

from . import settings

_task: asyncio.Task | None = None
_state: dict[str, Any] = {"running": False, "last_error": "", "last_fired": ""}

CHECK_EVERY_S = 30


def parse_at(value: str) -> dtime:
    """'09:00' -> time(9, 0). A malformed value falls back to 09:00 rather
    than crashing the app on boot."""
    try:
        hh, _, mm = (value or "").partition(":")
        return dtime(hour=max(0, min(23, int(hh))), minute=max(0, min(59, int(mm or 0))))
    except (TypeError, ValueError):
        return dtime(hour=9)


def due(now: datetime, at: dtime, last_run: str) -> bool:
    if now.time() < at:
        return False
    return (last_run or "") != now.date().isoformat()


def status() -> dict[str, Any]:
    cfg = settings.get_settings()
    at = parse_at(cfg.daily_at)
    now = datetime.now()
    today_at = datetime.combine(now.date(), at)
    next_at = today_at if now < today_at else datetime.combine(
        date.fromordinal(now.date().toordinal() + 1), at
    )
    if cfg.daily_enabled and due(now, at, cfg.daily_last_run):
        next_at = now                       # overdue; it will fire on the next tick
    return {
        "enabled": cfg.daily_enabled,
        "at": cfg.daily_at,
        "count": cfg.daily_job_count,
        "build_resumes": cfg.daily_build_resumes,
        "last_run": cfg.daily_last_run,
        "next_run": next_at.isoformat(timespec="seconds"),
        "running_now": _state["running"],
        "last_error": _state["last_error"],
    }


async def _fire() -> None:
    from .orchestrator import daily

    _state["running"] = True
    _state["last_error"] = ""
    try:
        await daily.run_brief()
        _state["last_fired"] = datetime.now().isoformat(timespec="seconds")
    except Exception as exc:  # noqa: BLE001 -- a bad morning must not kill the loop
        _state["last_error"] = str(exc)[:400]
    finally:
        _state["running"] = False


async def _loop() -> None:
    while True:
        try:
            cfg = settings.get_settings()
            if cfg.daily_enabled and not _state["running"]:
                if due(datetime.now(), parse_at(cfg.daily_at), cfg.daily_last_run):
                    await _fire()
        except Exception as exc:  # noqa: BLE001
            _state["last_error"] = str(exc)[:400]
        await asyncio.sleep(CHECK_EVERY_S)


def start() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


async def stop() -> None:
    global _task
    if _task is not None and not _task.done():
        _task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _task
    _task = None
