"""
No LLM configured.

This is not an error state -- it is a supported mode. Every deterministic agent
still runs: sourcing, the sponsorship gate with tiers and triggering sentences,
never-re-apply, link verification, the competition/recency/company score
components, ATS keyword coverage, template resume assembly from context/ facts,
Tectonic compilation, the one-page gate, and every file the workspace expects.

Only the judgement stages are unavailable, and each one is reported in the UI
as SKIPPED with a plain sentence saying what it would have added.
"""

from __future__ import annotations

from typing import Any

from .provider import (
    Effort, LLMProvider, LLMResult, Message, ModelTier, ProviderUnavailable,
)

# What the user actually loses, per agent, in plain language.
SKIP_REASONS: dict[str, str] = {
    "jd_parser": (
        "Requirements were pulled out by keyword frequency instead of being read. "
        "Usually close, but it cannot spot an unstated must-have."
    ),
    "manager_agent": (
        "No hiring-manager verdict: the disqualifying bar, the projects worth "
        "building, and the questions they would ask all need a model that can "
        "read this company. What the ad repeats most is still listed."
    ),
    "resume_editor": (
        "The resume chat needs a model to turn what you type into changes. You can "
        "still edit the resume by hand, and every honesty check still runs."
    ),
    "company_intel": (
        "No company research: what they are building, where they are heading, and "
        "which of your skills they actually care about."
    ),
    "skill_predictor": "No must-have/should-have split and no interview-probability estimate.",
    "fit_scorer": "The skill-match part of the score falls back to keyword overlap.",
    "resume_writer": (
        "The resume was assembled from your context/ facts using the template, not "
        "rewritten for this specific job."
    ),
    "recruiter_audit": "No recruiter audit, so no match score, red flags or pile verdict.",
    "fabrication_guard": (
        "Only the mechanical honesty checks ran. They still catch invented tools and "
        "numbers, but not subtler overstatement."
    ),
    "study_plan": "No study plan for what to learn before they call.",
    "judge": "No quality scoring of the agent output.",
    "normalizer": "Job titles and companies were tidied by rule instead of by reading.",
    "track_classifier": "The track was chosen by keyword signal counting alone.",
    "ats_agent": "Keyword coverage was measured, but not advice on where to add a term.",
}


class NullProvider(LLMProvider):
    name = "none"
    supports_web_search = False
    supports_structured = False
    supports_caching = False

    def __init__(self, reason: str = "") -> None:
        self.reason = reason or (
            "No AI model is connected yet. Paste an Anthropic API key in Settings, "
            "or install the Claude Code command line tool, to turn on the AI agents."
        )

    async def available(self) -> tuple[bool, str]:
        return False, self.reason

    async def complete(self, **kwargs: Any) -> LLMResult:
        agent = kwargs.get("agent", "")
        raise ProviderUnavailable(
            SKIP_REASONS.get(agent, self.reason),
            "Add an API key in Settings to enable this step.",
        )

    async def complete_structured(self, **kwargs: Any) -> LLMResult:
        return await self.complete(**kwargs)


def skip_reason(agent: str) -> str:
    return SKIP_REASONS.get(
        agent, "This step needs an AI model, which is not connected yet."
    )
