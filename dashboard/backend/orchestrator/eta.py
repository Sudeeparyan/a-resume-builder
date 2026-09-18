"""
"How long will this take?"

Seeded with hand-measured priors so the very first run shows a credible number
rather than nothing, then blended toward observed history:

    estimate = (n/(n+5)) * observed_median + (5/(n+5)) * prior

which converges after about five runs and never swings wildly on one slow call.

Two deliberate choices:
  * A phase's wall time is ceil(items / concurrency) * per_item, not
    items * per_item. Ignoring parallelism triples the number shown.
  * A range is reported, not a point. A point estimate that is wrong once
    destroys trust in the whole feature.

The estimate improves as the run proceeds, because the gates shrink the item
counts of later phases -- which is exactly the shape a person trusts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .. import db

# Milliseconds per item, measured on this machine where possible.
PRIORS_MS: dict[str, float] = {
    "preflight": 900,
    "source": 1500,          # per board
    "normalize": 30,
    "hard_filter": 5,
    "sponsorship": 20,
    "tracker": 5,
    "link_verify": 2500,
    "jd_parse": 7000,
    "company_intel": 60000,
    "skill_predict": 18000,
    "fit_score": 40,
    "rank": 200,
    "persist": 800,
    # build pipeline
    "track_classify": 1500,
    "signature_assign": 4000,
    "resume_write": 40000,
    "fabrication_guard": 60,
    "recruiter_audit": 55000,
    "ats_check": 60,
    "compile": 1400,
    "study_plan": 28000,
    "record": 500,
    "judge": 12000,
}

CONCURRENCY: dict[str, int] = {
    "source": 6, "link_verify": 4, "jd_parse": 4, "company_intel": 3,
    "skill_predict": 4, "resume_write": 3, "recruiter_audit": 3,
    "study_plan": 3, "compile": 2, "judge": 3,
}

BLEND_PRIOR_WEIGHT = 5.0


@dataclass
class PhasePlan:
    key: str
    label: str
    items: int = 1
    llm: bool = False


def per_item_ms(stage: str) -> tuple[float, float]:
    """(p50, p80) milliseconds per item, blending history with the prior."""
    prior = PRIORS_MS.get(stage, 1000.0)
    observed = db.median_duration(stage)
    p80_obs = db.percentile_duration(stage, 0.8)

    if observed is None:
        return prior, prior * 1.6

    row = db.connect().execute(
        "SELECT COUNT(*) AS n FROM stage_durations WHERE stage = ?", (stage,)
    ).fetchone()
    n = float(row["n"] if row else 0)
    w = n / (n + BLEND_PRIOR_WEIGHT)
    p50 = w * observed + (1 - w) * prior
    p80 = w * (p80_obs or observed * 1.4) + (1 - w) * prior * 1.6
    return p50, max(p80, p50)


def phase_seconds(stage: str, items: int) -> tuple[float, float]:
    if items <= 0:
        return 0.0, 0.0
    conc = max(1, CONCURRENCY.get(stage, 1))
    waves = math.ceil(items / conc)
    p50, p80 = per_item_ms(stage)
    return waves * p50 / 1000.0, waves * p80 / 1000.0


def estimate(plan: list[PhasePlan], done: set[str] | None = None) -> dict[str, Any]:
    done = done or set()
    p50 = p80 = 0.0
    detail: list[dict[str, Any]] = []
    for ph in plan:
        if ph.key in done:
            continue
        a, b = phase_seconds(ph.key, ph.items)
        p50 += a
        p80 += b
        detail.append({"stage": ph.key, "label": ph.label, "items": ph.items,
                       "p50_s": round(a), "p80_s": round(b)})
    return {
        "p50_seconds": int(p50),
        "p80_seconds": int(p80),
        "human": human_range(p50, p80),
        "detail": detail,
        "confidence": "low" if any(p.llm for p in plan if p.key not in done) else "high",
    }


def human_range(p50: float, p80: float) -> str:
    """Plain English, because she is not reading a dashboard of numbers."""
    if p80 < 45:
        return "under a minute"
    lo, hi = max(1, round(p50 / 60)), max(1, round(p80 / 60))
    if lo == hi:
        return f"about {lo} minute{'s' if lo != 1 else ''}"
    return f"about {lo}–{hi} minutes"


def record(stage: str, duration_ms: int, items: int = 1) -> None:
    db.record_duration(stage, duration_ms, items)
