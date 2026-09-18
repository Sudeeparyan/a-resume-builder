"""
The run event bus.

Every event is written to the database with a monotonic sequence number BEFORE
it is fanned out, so a browser that reconnects can ask for everything after the
last number it saw and lose nothing -- closing the laptop lid mid-run must not
lose progress.

Fan-out uses one queue per listener. A single shared queue would deliver each
event to only one of several open tabs.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, AsyncIterator

from .. import db

_listeners: dict[str, set[asyncio.Queue]] = defaultdict(set)
_seq: dict[str, int] = defaultdict(int)
_lock = asyncio.Lock()


async def emit(
    run_id: str, type_: str, *, stage: str | None = None,
    message: str = "", **data: Any,
) -> dict[str, Any]:
    async with _lock:
        _seq[run_id] += 1
        seq = _seq[run_id]

    event = {
        "run_id": run_id, "seq": seq, "type": type_, "stage": stage,
        "message": message, "data": data, "at": datetime.now().isoformat(timespec="seconds"),
    }

    try:
        db.connect().execute(
            "INSERT INTO run_events (run_id, seq, type, stage, message, data, at)"
            " VALUES (?,?,?,?,?,?,?)",
            (run_id, seq, type_, stage, message, db.dumps(data), event["at"]),
        )
    except Exception:  # noqa: BLE001 -- telemetry must never break a run
        pass

    for q in list(_listeners.get(run_id, ())):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    return event


def replay(run_id: str, after_seq: int = 0) -> list[dict[str, Any]]:
    rows = db.connect().execute(
        "SELECT seq, type, stage, message, data, at FROM run_events"
        " WHERE run_id = ? AND seq > ? ORDER BY seq",
        (run_id, after_seq),
    ).fetchall()
    return [
        {
            "run_id": run_id, "seq": r["seq"], "type": r["type"], "stage": r["stage"],
            "message": r["message"], "data": db.loads(r["data"]), "at": r["at"],
        }
        for r in rows
    ]


async def subscribe(run_id: str, after_seq: int = 0) -> AsyncIterator[dict[str, Any]]:
    """Replay what was missed, then stream live until the run finishes."""
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    _listeners[run_id].add(q)
    try:
        last = after_seq
        for ev in replay(run_id, after_seq):
            last = ev["seq"]
            yield ev
            if ev["type"] == "run_finished":
                return

        while True:
            try:
                ev = await asyncio.wait_for(q.get(), timeout=20.0)
            except asyncio.TimeoutError:
                yield {"type": "ping", "run_id": run_id, "seq": last,
                       "at": datetime.now().isoformat(timespec="seconds"),
                       "message": "", "stage": None, "data": {}}
                continue
            if ev["seq"] <= last:
                continue
            last = ev["seq"]
            yield ev
            if ev["type"] == "run_finished":
                return
    finally:
        _listeners[run_id].discard(q)
        if not _listeners[run_id]:
            _listeners.pop(run_id, None)


def restore_seq(run_id: str) -> None:
    row = db.connect().execute(
        "SELECT MAX(seq) AS m FROM run_events WHERE run_id = ?", (run_id,)
    ).fetchone()
    _seq[run_id] = (row["m"] or 0) if row else 0
