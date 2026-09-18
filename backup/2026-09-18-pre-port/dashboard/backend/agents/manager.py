
"""
The hiring manager's bar for one job -- computed WITHOUT the candidate.

Every other agent here is on her side. This one is not, and that is the entire
point: an outside view of what the job demands is only useful if it was not
written by something trying to make her look good. So it never receives
fact_prefix(fb), her name, or her project bank.

Blindness is enforced three ways, in increasing strength:
  1. a whitelisting payload builder (prompts.manager_payload)
  2. assert_blind(), which raises before the call if anything leaked
  3. tests/test_manager_blind.py, which is the real guard -- the next person to
     "add a bit of context for better answers" breaks a test rather than a
     promise.
"""

from __future__ import annotations

import re
from typing import Any

from .. import db, paths
from ..llm.provider import LLMProvider, Message, QuotaExhausted
from ..models import JobPosting
from . import prompts
from . import deterministic as D

MANAGER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "role_in_one_line", "mandatory", "strong_signals", "perfect_projects",
        "screening_questions", "instant_rejects", "the_bar",
    ],
    "properties": {
        "role_in_one_line": {"type": "string"},
        "what_breaks_without_this_hire": {"type": "string"},
        "seniority_read": {"type": "string"},
        "mandatory": {
            "type": "array", "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["requirement", "why_disqualifying"],
                "properties": {
                    "requirement": {"type": "string"},
                    "why_disqualifying": {"type": "string"},
                    "how_i_check": {"type": "string"},
                    "evidence_quote": {
                        "type": "string",
                        "description": "Verbatim from the ad. A claim about the ad points at the ad.",
                    },
                },
            },
        },
        "strong_signals": {
            "type": "array", "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["signal", "why_it_moves_me"],
                "properties": {
                    "signal": {"type": "string"},
                    "why_it_moves_me": {"type": "string"},
                    "how_rare": {"enum": ["common", "uncommon", "rare"]},
                },
            },
        },
        "perfect_projects": {
            "type": "array", "minItems": 2, "maxItems": 4,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["name", "what_it_proves", "scope"],
                "properties": {
                    "name": {"type": "string"},
                    "what_it_proves": {"type": "string"},
                    "stack": {"type": "array", "maxItems": 8, "items": {"type": "string"}},
                    "scope": {"type": "string"},
                    "rough_effort_days": {"type": "integer"},
                    "what_bad_looks_like": {"type": "string"},
                },
            },
        },
        "screening_questions": {
            "type": "array", "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["question"],
                "properties": {
                    "question": {"type": "string"},
                    "what_a_good_answer_contains": {"type": "string"},
                    "what_a_bad_answer_sounds_like": {"type": "string"},
                },
            },
        },
        "instant_rejects": {
            "type": "array", "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["signal"],
                "properties": {
                    "signal": {"type": "string"}, "why": {"type": "string"},
                },
            },
        },
        "the_bar": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
}


class ProfileLeak(RuntimeError):
    """The manager agent was about to be told who the candidate is."""


def _leak_terms() -> list[str]:
    """Her name and her project ids -- the things that must never appear."""
    terms: list[str] = []
    m = re.search(
        r"full_name:\s*[\"']?([^\"'\n]+)", paths.read_text(paths.PROFILE_YML)
    )
    if m:
        name = m.group(1).strip()
        terms += [name] + [p for p in name.split() if len(p) > 3]
    try:
        from ..services import factbank
        _roles, projects = factbank.load()
        terms += [p.pid for p in projects]
    except Exception:  # noqa: BLE001 -- a parse failure must not disable the check
        pass
    return [t for t in terms if t]


def assert_blind(system: str, user_text: str, fb: Any = None) -> None:
    """
    Raise before the call if any candidate detail reached the payload.

    Cheap, and it fails loudly in development rather than quietly shipping a
    flattering verdict that reads like an objective one.
    """
    blob = f"{system}\n{user_text}"
    low = blob.lower()

    if fb is not None and getattr(fb, "bundle", ""):
        head = fb.bundle[:400].strip()
        if head and head in blob:
            raise ProfileLeak("Her verified facts reached the hiring-manager agent.")

    for term in _leak_terms():
        if re.search(rf"\b{re.escape(term.lower())}\b", low):
            raise ProfileLeak(
                f"{term!r} reached the hiring-manager agent, which must not know "
                "who the candidate is."
            )


async def run(
    job: JobPosting, *, research: Any = None, provider: LLMProvider,
) -> tuple[dict[str, Any], list[str], bool, float]:
    """
    Returns (verdict, sources, degraded, cost_usd).

    Degrades to a deterministic bar rather than an error page: without a model
    the ad's own repeated requirements are still worth showing.
    """
    payload = prompts.manager_payload(job, research)
    assert_blind(prompts.MANAGER_AGENT, payload)

    try:
        res = await provider.complete_structured(
            system=prompts.MANAGER_AGENT,
            messages=[Message(role="user", content=payload)],
            schema=MANAGER_SCHEMA, tier="deep", effort="high",
            cache_prefix=None,          # see the module docstring: no rulebook either
            web_search=True, agent="manager_agent", max_tokens=12000,
        )
    except QuotaExhausted:
        raise
    except Exception:  # noqa: BLE001
        return fallback_verdict(job), [], True, 0.0

    verdict = _to_verdict(res.data or {})
    if not verdict.get("mandatory") and not verdict.get("perfect_projects"):
        return fallback_verdict(job), [], True, res.usage.cost_usd
    return verdict, list(res.citations or []), False, res.usage.cost_usd


def _to_verdict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Defensive in the style of enrich._to_research.

    web_search=True routes through prompt-and-parse, so additionalProperties is
    only advisory and a list asked to hold objects may hold bare strings.
    """
    def objs(key: str, main: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in data.get(key) or []:
            if isinstance(item, str) and item.strip():
                out.append({main: item.strip()})
            elif isinstance(item, dict):
                row = {k: v for k, v in item.items() if isinstance(k, str)}
                if row.get(main):
                    out.append(row)
        return out

    return {
        "role_in_one_line": str(data.get("role_in_one_line") or ""),
        "what_breaks_without_this_hire": str(data.get("what_breaks_without_this_hire") or ""),
        "seniority_read": str(data.get("seniority_read") or ""),
        "mandatory": objs("mandatory", "requirement"),
        "strong_signals": objs("strong_signals", "signal"),
        "perfect_projects": objs("perfect_projects", "name"),
        "screening_questions": objs("screening_questions", "question"),
        "instant_rejects": objs("instant_rejects", "signal"),
        "the_bar": str(data.get("the_bar") or ""),
        "sources": [s for s in (data.get("sources") or []) if isinstance(s, str)],
    }


def fallback_verdict(job: JobPosting) -> dict[str, Any]:
    """
    The bar, without a model.

    perfect_projects stays EMPTY on purpose. Recommending a project to build,
    with no model and nothing behind it, is fabrication wearing a helpful face.
    """
    jd = D.parse_jd_keywords(job)
    lines = [ln.strip() for ln in (job.jd_text or "").splitlines() if ln.strip()]

    def quote_for(term: str) -> str:
        low = term.lower()
        for ln in lines:
            if low in ln.lower():
                return ln[:300]
        return ""

    mandatory = [{
        "requirement": r.keyword or r.text,
        "why_disqualifying": "The ad repeats this, or files it under requirements.",
        "evidence_quote": quote_for(r.keyword or r.text),
    } for r in (jd.must_haves if jd else [])][:6]

    return {
        "role_in_one_line": f"{job.role_title} at {job.company}",
        "what_breaks_without_this_hire": "",
        "seniority_read": "",
        "mandatory": mandatory,
        "strong_signals": [
            {"signal": r.keyword or r.text, "why_it_moves_me": "Named in the ad as a plus."}
            for r in (jd.nice_to_haves if jd else [])
        ][:6],
        "perfect_projects": [],
        "screening_questions": [],
        "instant_rejects": [],
        "the_bar": "",
        "degraded_note": (
            "No hiring-manager verdict yet: the disqualifying bar, the projects worth "
            "building and the questions they would ask all need a model that can read "
            "this company. What the ad repeats most is listed above."
        ),
        "sources": [],
    }


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def load(job_id: str) -> dict[str, Any] | None:
    r = db.connect().execute(
        "SELECT * FROM manager_verdicts WHERE job_id = ?", (job_id,)
    ).fetchone()
    if r is None:
        return None
    return {
        "job_id": r["job_id"], "company": r["company"], "role_title": r["role_title"],
        "verdict": db.loads(r["verdict_json"], {}),
        "sources": db.loads(r["sources_json"], []),
        "degraded": bool(r["degraded"]), "jd_sha": r["jd_sha"],
        "provider": r["provider"], "model": r["model"],
        "cost_usd": r["cost_usd"], "created_at": r["created_at"],
    }


def save(
    job: JobPosting, job_id: str, verdict: dict[str, Any], sources: list[str],
    *, degraded: bool, provider: str = "", model: str = "",
    cost_usd: float = 0.0, run_id: str = "", jd_sha: str = "",
) -> None:
    db.connect().execute(
        "INSERT INTO manager_verdicts (job_id, run_id, company, role_title,"
        " verdict_json, sources_json, provider, model, cost_usd, degraded, jd_sha,"
        " created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(job_id) DO UPDATE SET run_id=excluded.run_id,"
        " verdict_json=excluded.verdict_json, sources_json=excluded.sources_json,"
        " provider=excluded.provider, model=excluded.model,"
        " cost_usd=excluded.cost_usd, degraded=excluded.degraded,"
        " jd_sha=excluded.jd_sha, created_at=excluded.created_at",
        (job_id, run_id, job.company, job.role_title, db.dumps(verdict),
         db.dumps(sources), provider, model, cost_usd, int(degraded), jd_sha, db.now()),
    )
