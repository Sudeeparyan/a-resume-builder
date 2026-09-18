"""
SQLite: a cache, an index and a run log. Never the authority.

CLAUDE.md makes the markdown workspace the source of truth, so resume content,
research and study plans live on disk under output/<folder>/ exactly as before,
and applications.tsv remains the application record. This database stores what
files cannot: discovered postings, run history, per-stage durations (which is
what makes an honest ETA possible), and evaluation results.

If this file is deleted the dashboard rebuilds it and loses nothing that
matters.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from . import paths

_local = threading.local()

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    company       TEXT NOT NULL,
    company_key   TEXT NOT NULL,
    role_title    TEXT NOT NULL,
    role_key      TEXT NOT NULL,
    url           TEXT NOT NULL,
    location      TEXT DEFAULT '',
    remote        INTEGER DEFAULT 0,
    department    TEXT DEFAULT '',
    posted_at     TEXT,
    jd_text       TEXT DEFAULT '',
    content_hash  TEXT DEFAULT '',
    raw_json      TEXT DEFAULT '{}',
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_dedupe ON jobs(company_key, role_key, content_hash);
CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs(company_key);
CREATE INDEX IF NOT EXISTS ix_jobs_seen ON jobs(last_seen);

CREATE TABLE IF NOT EXISTS job_analysis (
    job_id          TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    run_id          TEXT,
    tier            TEXT,
    verdict         TEXT,
    reason          TEXT,
    reason_label    TEXT,
    triggering_sentence TEXT,
    everify         INTEGER DEFAULT 0,
    cap_exempt      INTEGER DEFAULT 0,
    h1b_approvals   INTEGER DEFAULT 0,
    link_status     TEXT DEFAULT 'UNCHECKED',
    score           REAL DEFAULT 0,
    score_json      TEXT DEFAULT '{}',
    jd_json         TEXT DEFAULT '{}',
    research_path   TEXT,
    research_json   TEXT DEFAULT '{}',
    prediction_json TEXT DEFAULT '{}',
    recommendation  TEXT DEFAULT '',
    ghost_flags     TEXT DEFAULT '[]',
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_analysis_score ON job_analysis(tier, score DESC);

CREATE TABLE IF NOT EXISTS excluded (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT,
    company    TEXT,
    role_title TEXT,
    url        TEXT DEFAULT '',
    stage      TEXT,
    why        TEXT,
    triggering_sentence TEXT,
    at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id         TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    status     TEXT NOT NULL,
    params     TEXT DEFAULT '{}',
    stages     TEXT DEFAULT '[]',
    message    TEXT DEFAULT '',
    error      TEXT,
    cost_usd   REAL DEFAULT 0,
    tokens_in  INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    resume_after TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_runs_created ON runs(created_at DESC);

CREATE TABLE IF NOT EXISTS run_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id  TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq     INTEGER NOT NULL,
    type    TEXT NOT NULL,
    stage   TEXT,
    message TEXT DEFAULT '',
    data    TEXT DEFAULT '{}',
    at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_run ON run_events(run_id, seq);

-- what makes an honest ETA possible
CREATE TABLE IF NOT EXISTS stage_durations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    stage      TEXT NOT NULL,
    items      INTEGER DEFAULT 1,
    duration_ms INTEGER NOT NULL,
    at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_durations_stage ON stage_durations(stage);

CREATE TABLE IF NOT EXISTS resumes (
    id           TEXT PRIMARY KEY,
    job_id       TEXT,
    run_id       TEXT,
    company      TEXT NOT NULL,
    role_title   TEXT NOT NULL,
    folder       TEXT NOT NULL,
    track        TEXT DEFAULT 'track_a',
    track_reason TEXT DEFAULT '',
    signature_project TEXT DEFAULT '',
    signature_reason  TEXT DEFAULT '',
    audit_json   TEXT DEFAULT '{}',
    ats_json     TEXT DEFAULT '{}',
    honesty_json TEXT DEFAULT '{}',
    suggestions_json TEXT DEFAULT '[]',
    pages        INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'DRAFT',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_resumes_updated ON resumes(updated_at DESC);

CREATE TABLE IF NOT EXISTS evals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT,
    subject_id TEXT,
    subject    TEXT NOT NULL,
    agent      TEXT NOT NULL,
    kind       TEXT NOT NULL,
    passed     INTEGER,
    score      REAL,
    dimensions TEXT DEFAULT '{}',
    findings   TEXT DEFAULT '[]',
    notes      TEXT DEFAULT '',
    human_verdict TEXT,
    at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_evals_subject ON evals(subject_id);

CREATE TABLE IF NOT EXISTS llm_calls (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT,
    agent      TEXT,
    model      TEXT,
    provider   TEXT,
    tokens_in  INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cache_read INTEGER DEFAULT 0,
    cost_usd   REAL DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    ok         INTEGER DEFAULT 1,
    error      TEXT,
    at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_calls_run ON llm_calls(run_id);

CREATE TABLE IF NOT EXISTS kv (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);

-- The hiring manager's bar for one job. Deliberately built WITHOUT her profile:
-- its whole value is that it is an outside view, not a flattering one.
-- No foreign key to jobs(id): a verdict must also be runnable for a folder that
-- /hunt created, whose job row was never persisted.
CREATE TABLE IF NOT EXISTS manager_verdicts (
    job_id       TEXT PRIMARY KEY,
    run_id       TEXT,
    company      TEXT NOT NULL,
    role_title   TEXT NOT NULL,
    verdict_json TEXT NOT NULL DEFAULT '{}',
    sources_json TEXT NOT NULL DEFAULT '[]',
    provider     TEXT DEFAULT '',
    model        TEXT DEFAULT '',
    cost_usd     REAL DEFAULT 0,
    degraded     INTEGER DEFAULT 0,
    jd_sha       TEXT DEFAULT '',
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_manager_company ON manager_verdicts(company);

-- How one resume is shaped. rendered_sha detects a hand edit in the LaTeX
-- drawer, so a recompose can refuse instead of silently discarding her work.
-- ship_sha makes the Download gate server truth that survives a page reload.
CREATE TABLE IF NOT EXISTS resume_specs (
    folder       TEXT PRIMARY KEY,
    spec_json    TEXT NOT NULL DEFAULT '{}',
    pages_target INTEGER NOT NULL DEFAULT 1,
    rendered_sha TEXT DEFAULT '',
    ship_sha     TEXT DEFAULT '',
    updated_at   TEXT NOT NULL
);

-- Durable instructions re-applied on EVERY rebuild.
-- op != ''  -> mechanical: folded into the Selection.
-- op == ''  -> advisory: prompt guidance only, and labelled as such in the UI
--              so she is never misled about what is actually enforced.
CREATE TABLE IF NOT EXISTS resume_rules (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    scope      TEXT NOT NULL DEFAULT 'folder',
    folder     TEXT NOT NULL DEFAULT '',
    text       TEXT NOT NULL,
    op         TEXT DEFAULT '',
    args_json  TEXT NOT NULL DEFAULT '{}',
    enabled    INTEGER NOT NULL DEFAULT 1,
    position   INTEGER NOT NULL DEFAULT 0,
    source     TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rules_scope ON resume_rules(scope, folder, position);

-- The transcript. plan_json/refusals_json let the panel re-render exactly after
-- a reload without re-calling the model; tex_before is one-click undo.
CREATE TABLE IF NOT EXISTS resume_chat (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    folder        TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL DEFAULT '',
    plan_json     TEXT NOT NULL DEFAULT '[]',
    refusals_json TEXT NOT NULL DEFAULT '[]',
    tex_before    TEXT NOT NULL DEFAULT '',
    tex_sha       TEXT DEFAULT '',
    cost_usd      REAL DEFAULT 0,
    at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chat_folder ON resume_chat(folder, seq);
"""


def connect() -> sqlite3.Connection:
    """One connection per thread. SQLite objects are not thread-safe to share."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        paths.ensure_dirs()
        conn = sqlite3.connect(paths.DB_PATH, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        _local.conn = conn
    return conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    c = connect()
    c.execute("BEGIN")
    try:
        yield c
    except Exception:
        c.execute("ROLLBACK")
        raise
    else:
        c.execute("COMMIT")


def init() -> None:
    connect()


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def dumps(v: Any) -> str:
    return json.dumps(v, default=str, ensure_ascii=False)


def loads(s: Any, default: Any = None) -> Any:
    if not s:
        return default if default is not None else {}
    try:
        return json.loads(s)
    except (TypeError, ValueError):
        return default if default is not None else {}


def kv_get(key: str, default: Any = None) -> Any:
    row = connect().execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
    return loads(row["v"], default) if row else default


def kv_set(key: str, value: Any) -> None:
    connect().execute(
        "INSERT INTO kv (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
        (key, dumps(value)),
    )


def record_duration(stage: str, duration_ms: int, items: int = 1) -> None:
    connect().execute(
        "INSERT INTO stage_durations (stage, items, duration_ms, at) VALUES (?, ?, ?, ?)",
        (stage, max(1, items), max(0, int(duration_ms)), now()),
    )


def median_duration(stage: str, limit: int = 40) -> float | None:
    """Median milliseconds per item for a stage, from real history."""
    rows = connect().execute(
        "SELECT duration_ms, items FROM stage_durations WHERE stage = ? "
        "ORDER BY id DESC LIMIT ?",
        (stage, limit),
    ).fetchall()
    if not rows:
        return None
    per = sorted((r["duration_ms"] / max(1, r["items"])) for r in rows)
    n = len(per)
    return per[n // 2] if n % 2 else (per[n // 2 - 1] + per[n // 2]) / 2


def percentile_duration(stage: str, pct: float = 0.8, limit: int = 40) -> float | None:
    rows = connect().execute(
        "SELECT duration_ms, items FROM stage_durations WHERE stage = ? "
        "ORDER BY id DESC LIMIT ?",
        (stage, limit),
    ).fetchall()
    if not rows:
        return None
    per = sorted((r["duration_ms"] / max(1, r["items"])) for r in rows)
    idx = min(len(per) - 1, max(0, int(round(pct * (len(per) - 1)))))
    return per[idx]
