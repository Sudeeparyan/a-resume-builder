"""
A SQLite index over system/data/sponsors-uscis.csv.

sponsor_check.lookup_history() reads all 83,624 rows of a 5.9 MB CSV on every
call. That is fine for a one-shot CLI run and unacceptable on a request path --
screening 40 jobs would read 236 MB. We build the index once (about a second),
keyed on the same employer_key the script computes, and fall back to the script
when the index has not been built.

The CSV stays the source of truth. This table is a cache and is rebuilt
whenever the CSV's mtime or size changes.
"""

from __future__ import annotations

import csv
import sqlite3
from typing import Any

from .. import legacy, paths

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sponsors (
    employer_key TEXT NOT NULL,
    employer     TEXT,
    approvals    INTEGER DEFAULT 0,
    denials      INTEGER DEFAULT 0,
    fiscal_year  TEXT,
    state        TEXT,
    city         TEXT
);
CREATE INDEX IF NOT EXISTS ix_sponsors_key ON sponsors(employer_key);
CREATE TABLE IF NOT EXISTS sponsor_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    csv_mtime REAL,
    csv_size  INTEGER,
    rows      INTEGER,
    built_at  TEXT
);
"""


def _conn() -> sqlite3.Connection:
    paths.ensure_dirs()
    c = sqlite3.connect(paths.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _csv_stat() -> tuple[float, int] | None:
    p = paths.SPONSORS_CSV
    if not p.exists():
        return None
    st = p.stat()
    return (st.st_mtime, st.st_size)


def is_current() -> bool:
    stat = _csv_stat()
    if stat is None:
        return False
    try:
        with _conn() as c:
            c.executescript(_SCHEMA)
            row = c.execute("SELECT csv_mtime, csv_size FROM sponsor_meta WHERE id = 1").fetchone()
    except sqlite3.Error:
        return False
    return bool(row) and row["csv_mtime"] == stat[0] and row["csv_size"] == stat[1]


def build(force: bool = False) -> dict[str, Any]:
    """Rebuild the index. Returns a small report; never raises on a missing CSV."""
    stat = _csv_stat()
    if stat is None:
        return {"built": False, "reason": "sponsors-uscis.csv is not present", "rows": 0}
    if not force and is_current():
        with _conn() as c:
            row = c.execute("SELECT rows FROM sponsor_meta WHERE id = 1").fetchone()
        return {"built": False, "reason": "already current", "rows": row["rows"] if row else 0}

    def to_int(v: Any) -> int:
        try:
            return int(str(v or "0").strip() or 0)
        except ValueError:
            return 0

    rows = 0
    with _conn() as c:
        c.executescript(_SCHEMA)
        c.execute("DELETE FROM sponsors")
        with paths.SPONSORS_CSV.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            batch: list[tuple] = []
            for r in csv.DictReader(fh):
                batch.append((
                    (r.get("employer_key") or "").strip(),
                    (r.get("employer") or "").strip(),
                    to_int(r.get("approvals")),
                    to_int(r.get("denials")),
                    (r.get("fiscal_year") or "").strip(),
                    (r.get("state") or "").strip(),
                    (r.get("city") or "").strip(),
                ))
                if len(batch) >= 5000:
                    c.executemany("INSERT INTO sponsors VALUES (?,?,?,?,?,?,?)", batch)
                    rows += len(batch)
                    batch.clear()
            if batch:
                c.executemany("INSERT INTO sponsors VALUES (?,?,?,?,?,?,?)", batch)
                rows += len(batch)
        c.execute(
            "INSERT OR REPLACE INTO sponsor_meta (id, csv_mtime, csv_size, rows, built_at) "
            "VALUES (1, ?, ?, ?, datetime('now'))",
            (stat[0], stat[1], rows),
        )
    return {"built": True, "reason": "rebuilt from CSV", "rows": rows}


def lookup(company: str, state: str = "") -> dict[str, Any]:
    """
    Same shape as sponsor_check.lookup_history():
    {found, matched_name, approvals, denials, years, states, source}
    """
    key = legacy.normalize_company(company)
    empty = {
        "found": False, "matched_name": None, "approvals": 0, "denials": 0,
        "years": [], "states": [], "source": None,
    }
    if not key:
        return empty | {"reason": "empty company name"}

    if not is_current():
        # Fall back to the script's own scan so a missing index never breaks the gate.
        return legacy.sponsor_check.lookup_history(company, state)

    with _conn() as c:
        found = c.execute(
            "SELECT employer, approvals, denials, fiscal_year, state "
            "FROM sponsors WHERE employer_key = ?",
            (key,),
        ).fetchall()

    if not found:
        return empty

    years: list[str] = []
    states: list[str] = []
    approvals = denials = 0
    matched = None
    for r in found:
        approvals += r["approvals"] or 0
        denials += r["denials"] or 0
        matched = matched or r["employer"]
        for y in (r["fiscal_year"] or "").split(";"):
            y = y.strip()
            if y and y not in years:
                years.append(y)
        st = (r["state"] or "").strip()
        if st and st not in states:
            states.append(st)

    return {
        "found": True,
        "matched_name": matched or company,
        "approvals": approvals,
        "denials": denials,
        "years": sorted(years),
        "states": states,
        "source": "USCIS H-1B Employer Data Hub",
    }


def stats() -> dict[str, Any]:
    if not paths.SPONSORS_CSV.exists():
        return {"available": False, "rows": 0, "current": False}
    try:
        with _conn() as c:
            c.executescript(_SCHEMA)
            row = c.execute("SELECT rows, built_at FROM sponsor_meta WHERE id = 1").fetchone()
    except sqlite3.Error:
        row = None
    return {
        "available": True,
        "rows": row["rows"] if row else 0,
        "built_at": row["built_at"] if row else None,
        "current": is_current(),
    }
