"""Orchestration for the specialist agents.

Routing is deterministic: the workflow decides which specialist runs, not a
model. That keeps a run's cost predictable and means a routing bug is a code
bug rather than a prompt bug. Models are used for judgement inside a step, never
to choose the next step.

Isolation: the hiring-manager agent must only ever see the job description and
public company research. It is called through `run_isolated`, which accepts a
fixed, narrow payload and cannot be handed the candidate profile. The rule comes
from AGENTS.md and is asserted by tests/test_ai_agents.py.
"""

from __future__ import annotations

import json
import operator
import time
from pathlib import Path
from typing import Annotated, Any, TypedDict

from backend.ai import catalog, claude_code, models
from backend.ai.agents.specialists import GROUNDING, REGISTRY, Specialist


# Provider errors quote request URLs, key-management links and account IDs. None
# of that belongs in text shown to the user, so failures are reported by class.
_ERROR_BY_STATUS = {
    401: "the API key was rejected",
    402: "the account is out of credits",
    403: "the account is not permitted to use this model",
    404: "the model is not available to this account",
    429: "the provider's rate limit or quota is exhausted",
}


def describe_provider_error(error: Exception) -> str:
    """A short, safe description of why a provider call failed."""
    status = getattr(error, "status_code", None) or getattr(
        getattr(error, "response", None), "status_code", None
    )
    if status is None:
        text = str(error)
        for code in _ERROR_BY_STATUS:
            if f"Error code: {code}" in text or f"({code})" in text:
                status = code
                break
    if status in _ERROR_BY_STATUS:
        return _ERROR_BY_STATUS[status]
    # SDKs differ: some raise typed errors carrying no HTTP status.
    name = type(error).__name__
    for marker, description in (
        ("RateLimit", "the provider's rate limit or quota is exhausted"),
        ("ResourceExhausted", "the provider's rate limit or quota is exhausted"),
        ("PermissionDenied", "the account is not permitted to use this model"),
        ("Authentication", "the API key was rejected"),
        ("NotFound", "the model is not available to this account"),
        ("Timeout", "the provider could not be reached"),
        ("Connection", "the provider could not be reached"),
    ):
        if marker in name:
            return description
    return f"the provider returned an unexpected {name}"


class AgentError(RuntimeError):
    """A specialist could not produce a usable result."""


class AgentTeam:
    """Runs specialists against the configured provider, tier by tier.

    `tiers` maps "strong"/"cheap" to a (provider_id, model) pair. The caller
    supplies it from saved preferences so the choice stays a runtime setting.
    """

    def __init__(self, root: Path, tiers: dict, on_usage=None):
        self.root = Path(root)
        self.tiers = tiers
        self.on_usage = on_usage

    @classmethod
    def from_preferences(cls, root: Path, preferences: dict, on_usage=None) -> "AgentTeam":
        tiers = {}
        for tier in catalog.TIERS:
            chosen = (preferences.get("tiers") or {}).get(tier) or {}
            provider = chosen.get("provider") or "openrouter"
            tiers[tier] = (provider, chosen.get("model") or catalog.default_model(provider, tier))
        return cls(root, tiers, on_usage)

    def _record(self, agent: Specialist, raw, started: float) -> None:
        if not self.on_usage:
            return
        usage = raw if isinstance(raw, dict) else getattr(raw, "usage_metadata", None) or {}
        self.on_usage({
            "agent": agent.name,
            "tier": agent.tier,
            "provider": self.tiers[agent.tier][0],
            "model": self.tiers[agent.tier][1],
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "seconds": round(time.time() - started, 2),
        })

    def run(self, agent_name: str, payload: Any, *, max_tokens: int = 4096):
        """Run one specialist and return its parsed, schema-valid result."""
        agent = REGISTRY[agent_name]
        if agent.isolated:
            raise AgentError(
                f"{agent.name} is isolated from candidate data and must be called via run_isolated()"
            )
        return self._invoke(agent, payload, max_tokens)

    def run_isolated(self, agent_name: str, *, job_description: str, public_research: str = "",
                     max_tokens: int = 4096):
        """Run an isolated specialist. Only the two fields below can reach it."""
        agent = REGISTRY[agent_name]
        if not agent.isolated:
            raise AgentError(f"{agent.name} is not an isolated agent")
        payload = {"job_description": job_description, "public_company_research": public_research}
        return self._invoke(agent, payload, max_tokens)

    def _invoke(self, agent: Specialist, payload: Any, max_tokens: int):
        provider, model = self.tiers[agent.tier]
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
        if provider == claude_code.ID:
            return self._invoke_local(agent, text, provider, model)
        llm = models.build(self.root, provider, model, max_tokens=max_tokens)
        structured = llm.with_structured_output(agent.schema, include_raw=True)
        started = time.time()
        try:
            result = structured.invoke(agent.prompt(text))
        except Exception as error:  # provider, network or quota failure
            raise AgentError(
                f"{agent.name} could not run on {provider}/{model}: {describe_provider_error(error)}"
            ) from error
        self._record(agent, result.get("raw"), started)
        if result.get("parsing_error") or result.get("parsed") is None:
            raise AgentError(f"{agent.name} returned output that did not match its schema")
        return result["parsed"]

    def _invoke_local(self, agent: Specialist, text: str, provider: str, model: str):
        """The same step through the local Claude Code CLI instead of LangChain.

        The specialist's system text and schema are passed as they are; the
        isolation rules above apply unchanged because the payload is built
        before this point.
        """
        from pydantic import ValidationError

        started = time.time()
        try:
            raw, usage = claude_code.run(
                text, agent.schema.model_json_schema(), model=model,
                web=agent.needs_web, system=agent.system + "\n\n" + GROUNDING,
            )
        except ValueError as error:
            raise AgentError(f"{agent.name} could not run on {provider}/{model}: {error}") from error
        self._record(agent, usage, started)
        try:
            return agent.schema.model_validate(raw)
        except ValidationError:
            raise AgentError(f"{agent.name} returned output that did not match its schema") from None


class PostingState(TypedDict, total=False):
    """Shared state for the posting-evaluation workflow.

    Each specialist writes its own key so parallel branches never contend for
    one slot; only `errors` accumulates, and it does so through a reducer.
    """
    posting: dict
    page_text: str
    profile_summary: str
    verdict: dict
    relevance: dict
    company: dict
    requirements: list
    errors: Annotated[list, operator.add]


def build_posting_graph(team: AgentTeam):
    """Fan out the independent checks on one posting, then join them.

    Verification, relevance, company research and requirement extraction do not
    depend on each other, so they run as parallel branches. The caller applies
    the deterministic gates in backend/job_quality.py to the joined result; this
    graph gathers evidence and never decides to save or reject a job.
    """
    from langgraph.graph import END, START, StateGraph

    def verify(state: PostingState) -> dict:
        if not state.get("page_text"):
            return {}
        try:
            return {"verdict": team.run("posting_verifier", {
                "url": state["posting"].get("url"),
                "title": state["posting"].get("title"),
                "page_text": state["page_text"][:20000],
            }).model_dump()}
        except AgentError as error:
            return {"errors": [str(error)]}

    def relevance(state: PostingState) -> dict:
        try:
            return {"relevance": team.run("relevance_judge", {
                "posting": state["posting"],
                "candidate_summary": state.get("profile_summary", ""),
            }).model_dump()}
        except AgentError as error:
            return {"errors": [str(error)]}

    def company(state: PostingState) -> dict:
        try:
            return {"company": team.run("company_investigator", {
                "company": state["posting"].get("company"),
                "posting_url": state["posting"].get("url"),
                "posting_text": (state["posting"].get("description") or "")[:8000],
            }).model_dump()}
        except AgentError as error:
            return {"errors": [str(error)]}

    def requirements(state: PostingState) -> dict:
        description = state["posting"].get("description") or ""
        if not description.strip():
            return {}
        try:
            extracted = team.run("requirement_extractor", {"job_description": description[:20000]})
            # Drop anything whose excerpt is not actually in the saved description.
            grounded = [r.model_dump() for r in extracted.requirements if r.excerpt and r.excerpt in description]
            return {"requirements": grounded}
        except AgentError as error:
            return {"errors": [str(error)]}

    graph = StateGraph(PostingState)
    for name, node in (("verify", verify), ("relevance", relevance),
                       ("company", company), ("requirements", requirements)):
        graph.add_node(name, node)
        graph.add_edge(START, name)
        graph.add_edge(name, END)
    return graph.compile()


def evaluate_posting(team: AgentTeam, posting: dict, page_text: str = "",
                     profile_summary: str = "") -> dict:
    """Gather every independent signal about one posting in a single pass."""
    graph = build_posting_graph(team)
    return graph.invoke({
        "posting": posting,
        "page_text": page_text,
        "profile_summary": profile_summary,
        "errors": [],
    })
