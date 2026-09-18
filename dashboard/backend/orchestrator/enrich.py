"""
The three LLM phases of a scan: read the ad, research the company, predict the odds.

Company research is the expensive one and the reason the whole dashboard is
worth running: it uses Claude's server-side web search to find what a company is
actually building, where they are heading, and which of her real skills they
care about -- then maps every skill to exactly one of three destinations.

The destination column IS the honesty wall. A skill she does not have goes to
the study plan or is named an honest gap. It never moves onto the resume.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from .. import db, settings
from ..agents import deterministic as D
from ..agents import prompts
from ..llm.provider import LLMProvider, Message, ProviderUnavailable, QuotaExhausted
from ..models import (
    CompanyResearch, DemandRow, JDAnalysis, Requirement, ScoredJob, SkillPrediction,
)
from ..services import context_loader

JD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["must_haves", "nice_to_haves", "hiring_problem"],
    "properties": {
        "team": {"type": "string"},
        "seniority": {"type": "string"},
        "work_mode": {"type": "string"},
        "years_required": {"type": ["integer", "null"]},
        "hiring_problem": {
            "type": "string",
            "description": "One sentence: what broke or is growing that opened this role.",
        },
        "must_haves": {
            "type": "array", "maxItems": 7,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["text", "keyword"],
                "properties": {
                    "text": {"type": "string"},
                    "keyword": {"type": "string",
                                "description": "The job ad's own wording, for ATS matching."},
                    "under_required_heading": {"type": "boolean"},
                },
            },
        },
        "nice_to_haves": {
            "type": "array", "maxItems": 5,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["text", "keyword"],
                "properties": {"text": {"type": "string"}, "keyword": {"type": "string"}},
            },
        },
        "domain_keywords": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
    },
}

RESEARCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["what_they_do", "demand_map", "sources"],
    "properties": {
        "what_they_do": {"type": "string"},
        "engineering_reality": {
            "type": "string",
            "description": "What they actually run. Their engineering blog beats their job ad.",
        },
        "current_projects": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
        "future_direction": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
        "team_shape": {"type": "string"},
        "pressures": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "day_job_months_1_3": {"type": "string"},
        "day_job_month_12": {"type": "string"},
        "fit_narrative": {"type": "string"},
        "questions_to_ask": {"type": "array", "maxItems": 5, "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
        "demand_map": {
            "type": "array", "maxItems": 14,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["skill", "centrality", "candidate_level", "destination"],
                "properties": {
                    "skill": {"type": "string"},
                    "named_by": {"type": "string"},
                    "centrality": {"enum": ["core", "important", "peripheral"]},
                    "candidate_level": {"enum": ["strong", "used_it", "touched_it", "none"]},
                    "destination": {
                        "enum": ["resume", "study_plan", "honest_gap"],
                        "description": (
                            "resume ONLY if she already has it. Otherwise study_plan if "
                            "learnable in weeks, else honest_gap. Never resume for a skill "
                            "she lacks."
                        ),
                    },
                    "evidence_url": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
    },
}

PREDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["must_have", "she_has", "she_lacks", "probability", "rationale"],
    "properties": {
        "must_have": {"type": "array", "items": {"type": "string"}},
        "should_have": {"type": "array", "items": {"type": "string"}},
        "nice_to_have": {"type": "array", "items": {"type": "string"}},
        "she_has": {"type": "array", "items": {"type": "string"}},
        "she_lacks": {"type": "array", "items": {"type": "string"}},
        "probability": {
            "type": "number", "minimum": 0, "maximum": 1,
            "description": "Interview probability. An estimate from evidence, not a promise.",
        },
        "rationale": {"type": "string"},
        "lift_if_learned": {
            "type": "array", "maxItems": 5,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["skill", "new_probability", "learn_days"],
                "properties": {
                    "skill": {"type": "string"},
                    "new_probability": {"type": "number"},
                    "learn_days": {"type": "integer"},
                },
            },
        },
    },
}


def _band(p: float) -> str:
    if p >= 0.55:
        return "high"
    if p >= 0.30:
        return "moderate"
    if p >= 0.12:
        return "low"
    return "long_shot"


async def run(run_obj, jobs: list[ScoredJob], *, fb, provider: LLMProvider) -> None:
    """Run the three LLM phases over the shortlist, in parallel within each phase."""
    cfg = settings.get_settings()
    cache = prompts.fact_prefix(fb)
    sem = asyncio.Semaphore(cfg.max_parallel_llm)

    # --- phase 1: read the ads -------------------------------------------
    t0 = await run_obj._start("jd_parse", items=len(jobs))

    async def parse(s: ScoredJob) -> None:
        async with sem:
            try:
                res = await provider.complete_structured(
                    system=prompts.JD_PARSER,
                    messages=[Message(role="user", content=prompts.jd_payload(s.job))],
                    schema=JD_SCHEMA, tier="mid", effort="medium",
                    cache_prefix=cache, agent="jd_parser", max_tokens=4000,
                )
                run_obj.cost_usd += res.usage.cost_usd
                s.jd = _to_jd(res.data or {}, s)
            except (ProviderUnavailable, Exception) as exc:  # noqa: BLE001
                if isinstance(exc, QuotaExhausted):
                    raise
                s.jd = D.parse_jd_keywords(s.job)

    await asyncio.gather(*(parse(s) for s in jobs))
    await run_obj._finish("jd_parse", t0, f"{len(jobs)} job ads read", items=len(jobs))

    # --- phase 2: research the companies ---------------------------------
    by_company: dict[str, list[ScoredJob]] = {}
    for s in jobs:
        by_company.setdefault(s.job.company, []).append(s)

    if not provider.supports_web_search:
        await run_obj._skip(
            "company_intel",
            "Company research needs web search, which this connection does not provide.",
        )
    else:
        t0 = await run_obj._start("company_intel", items=len(by_company))
        rsem = asyncio.Semaphore(3)
        done = 0

        async def research(company: str, group: list[ScoredJob]) -> None:
            nonlocal done
            async with rsem:
                try:
                    res = await provider.complete_structured(
                        system=prompts.COMPANY_RESEARCH,
                        messages=[Message(
                            role="user",
                            content=prompts.research_payload(group[0].job, group[0].jd),
                        )],
                        schema=RESEARCH_SCHEMA, tier="deep", effort="high",
                        cache_prefix=cache, web_search=True,
                        agent="company_intel", max_tokens=12000,
                    )
                    run_obj.cost_usd += res.usage.cost_usd
                    r = _to_research(res.data or {}, company, res.citations)
                    for s in group:
                        s.research = r
                except QuotaExhausted:
                    raise
                except Exception:  # noqa: BLE001
                    pass
                done += 1
                await run_obj._log(
                    f"Researched {company} ({done} of {len(by_company)})",
                    stage="company_intel", done=done, total=len(by_company),
                )

        await asyncio.gather(*(research(c, g) for c, g in by_company.items()))
        got = sum(1 for s in jobs if s.research)
        await run_obj._finish(
            "company_intel", t0, f"{len(by_company)} companies researched",
            items=len(by_company),
        )

    # --- phase 3: predict the odds ---------------------------------------
    t0 = await run_obj._start("skill_predict", items=len(jobs))

    async def predict(s: ScoredJob) -> None:
        async with sem:
            try:
                res = await provider.complete_structured(
                    system=prompts.INTERVIEW_PREDICTOR,
                    messages=[Message(
                        role="user", content=prompts.predict_payload(s.job, s.jd, s.research)
                    )],
                    schema=PREDICT_SCHEMA, tier="mid", effort="medium",
                    cache_prefix=cache, agent="skill_predictor", max_tokens=4000,
                )
                run_obj.cost_usd += res.usage.cost_usd
                s.prediction = _to_prediction(res.data or {}, fb)
            except QuotaExhausted:
                raise
            except Exception:  # noqa: BLE001
                s.prediction = _fallback_prediction(s, fb)

    await asyncio.gather(*(predict(s) for s in jobs))
    await run_obj._finish("skill_predict", t0, f"{len(jobs)} predictions made", items=len(jobs))


# --------------------------------------------------------------------------
# mapping
# --------------------------------------------------------------------------
def _to_jd(data: dict[str, Any], s: ScoredJob) -> JDAnalysis:
    def reqs(items: list, kind: str) -> list[Requirement]:
        out = []
        for it in items or []:
            if isinstance(it, str):
                out.append(Requirement(text=it, keyword=it, kind=kind))
            elif isinstance(it, dict):
                out.append(Requirement(
                    text=it.get("text", ""), keyword=it.get("keyword") or it.get("text", ""),
                    kind=kind,
                    under_required_heading=bool(it.get("under_required_heading")),
                ))
        return out

    return JDAnalysis(
        company=s.job.company, role_title=s.job.role_title,
        team=data.get("team", ""), location=s.job.location,
        work_mode=data.get("work_mode", ""), seniority=data.get("seniority", ""),
        must_haves=reqs(data.get("must_haves"), "must"),
        nice_to_haves=reqs(data.get("nice_to_haves"), "nice"),
        domain_keywords=reqs(data.get("domain_keywords"), "domain"),
        hiring_problem=data.get("hiring_problem", ""),
        years_required=data.get("years_required"),
        source="llm",
    )


def _to_research(data: dict[str, Any], company: str, citations: list[str]) -> CompanyResearch:
    rows = []
    for r in data.get("demand_map") or []:
        if not isinstance(r, dict) or not r.get("skill"):
            continue
        try:
            rows.append(DemandRow(**{
                "skill": r.get("skill", ""), "named_by": r.get("named_by", ""),
                "centrality": r.get("centrality", "important"),
                "candidate_level": r.get("candidate_level", "none"),
                "destination": r.get("destination", "honest_gap"),
                "evidence_url": r.get("evidence_url") or None,
                "note": r.get("note", ""),
            }))
        except Exception:  # noqa: BLE001
            continue

    return CompanyResearch(
        company=company,
        what_they_do=data.get("what_they_do", ""),
        engineering_reality=data.get("engineering_reality", ""),
        current_projects=data.get("current_projects") or [],
        future_direction=data.get("future_direction") or [],
        team_shape=data.get("team_shape", ""),
        pressures=data.get("pressures") or [],
        day_job_months_1_3=data.get("day_job_months_1_3", ""),
        day_job_month_12=data.get("day_job_month_12", ""),
        demand_map=rows,
        fit_narrative=data.get("fit_narrative", ""),
        questions_to_ask=data.get("questions_to_ask") or [],
        sources=list(dict.fromkeys((data.get("sources") or []) + citations)),
    )


def _to_prediction(data: dict[str, Any], fb) -> SkillPrediction:
    must = data.get("must_have") or []
    has = data.get("she_has") or []
    # Trust but verify: a skill she cannot claim never counts as held, whatever
    # the model said.
    has = [h for h in has if fb.claimable(str(h).lower()) or fb.has_token(str(h).lower())]
    coverage = (len(has) / len(must)) if must else 0.0
    p = float(data.get("probability") or 0.0)
    return SkillPrediction(
        must_have=must,
        should_have=data.get("should_have") or [],
        nice_to_have=data.get("nice_to_have") or [],
        she_has=has,
        she_lacks=data.get("she_lacks") or [],
        must_have_coverage=round(min(1.0, coverage), 3),
        probability=round(min(1.0, max(0.0, p)), 3),
        probability_band=_band(p),
        rationale=data.get("rationale", ""),
        lift_if_learned=data.get("lift_if_learned") or [],
    )


def _fallback_prediction(s: ScoredJob, fb) -> SkillPrediction:
    """Deterministic coverage, labelled as an estimate made without a model."""
    terms = [r.keyword or r.text for r in (s.jd.must_haves if s.jd else [])]
    has = [t for t in terms if fb.claimable(t.lower())]
    lacks = [t for t in terms if not fb.claimable(t.lower())]
    cov = (len(has) / len(terms)) if terms else 0.0
    p = round(min(0.8, cov * 0.8), 3)
    return SkillPrediction(
        must_have=terms, she_has=has, she_lacks=lacks,
        must_have_coverage=round(cov, 3), probability=p, probability_band=_band(p),
        rationale=(
            f"Estimated without AI: you can claim {len(has)} of {len(terms)} of the "
            "terms this ad repeats most."
        ),
    )
