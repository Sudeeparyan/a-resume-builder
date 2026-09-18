"""Provider and model selection for the UI.

One place that answers: which providers exist, which have a key, which models
they offer, what is currently chosen, and does the choice actually work. Key
values never appear in anything returned here.
"""

from __future__ import annotations

from backend.ai import catalog, claude_code, keys, models
from backend.ai.agents.graph import AgentTeam, describe_provider_error
from backend.ai.agents.specialists import REGISTRY

# The free local runtime is not a LangChain provider; it is offered alongside them.
CODEX = {
    "id": "codex",
    "label": "Codex (local, free)",
    "configured": True,
    "models": ["codex-runtime"],
    "defaults": {"strong": "codex-runtime", "cheap": "codex-runtime"},
    "note": "Runs through the Codex app on this Mac. No API key and no per-call cost.",
}

# The same idea on the Claude side: the signed-in Claude Code CLI, on the
# subscription's usage limits. Presence is checked live because the CLI may be
# installed or removed without a restart.
def _claude_code_entry() -> dict:
    return {
        "id": claude_code.ID,
        "label": claude_code.LABEL,
        "configured": claude_code.available(),
        "models": list(claude_code.MODELS),
        "defaults": dict(claude_code.DEFAULTS),
        "note": claude_code.NOTE,
    }


LOCAL_DEFAULTS = {"codex": CODEX["defaults"], claude_code.ID: claude_code.DEFAULTS}


def _preferences(services) -> dict:
    stored = services.pref("ai_preferences", {}) or {}
    tiers = stored.get("tiers") or {}
    resolved = {}
    for tier in catalog.TIERS:
        chosen = tiers.get(tier) or {}
        provider = chosen.get("provider") or "openrouter"
        fallback = LOCAL_DEFAULTS[provider][tier] if provider in LOCAL_DEFAULTS else catalog.default_model(provider, tier)
        resolved[tier] = {
            "provider": provider,
            "model": chosen.get("model") or fallback,
        }
    return {**stored, "tiers": resolved}


# What each agent run asks the gateway for, in the words the page uses.
ROUTES = (
    ("discovery", "Job search"),
    ("role_research", "Company research & resume advice"),
    ("document_review", "Independent resume review"),
    ("resume_chat", "Resume chat"),
    ("email", "Gmail sync"),
)


def _routes(gateway) -> list:
    """Which provider each kind of work will actually use, and why."""
    preferences = gateway.preferences()
    default, overrides = preferences["default"], preferences.get("actions") or {}
    routes = []
    for action, label in ROUTES:
        try:
            provider, model = gateway.resolve(action, require_configured=False)
            routes.append({"action": action, "label": label, "provider": provider.id, "model": model,
                           "moved": provider.id != default.get("provider"),
                           "override": action in overrides, "error": None})
        except ValueError as error:
            routes.append({"action": action, "label": label, "provider": None, "model": None,
                           "moved": False, "error": str(error)})
    return routes


def overview(services, refresh: bool = False, gateway=None) -> dict:
    """Everything the settings screen needs in one call."""
    root = services.w.root
    providers = []
    for provider_id, spec in catalog.PROVIDERS.items():
        listed = catalog.models(root, provider_id, refresh=refresh)
        providers.append({
            "id": provider_id,
            "label": spec["label"],
            "kind": "api",
            "configured": listed["configured"],
            "models": listed["models"],
            "defaults": spec["defaults"],
            "key_name": spec["key"],
            "key_source": keys.source(root, spec["key"]),
            "error": listed["error"],
            "fetched_at": listed.get("fetched_at"),
        })
    providers.append({**CODEX, "kind": "local"})
    providers.append({**_claude_code_entry(), "kind": "local"})
    if gateway is not None:
        for entry in providers:
            engine = gateway.providers.get(entry["id"])
            entry["capabilities"] = sorted(engine.capabilities) if engine else []
            entry["agent_models"] = list(engine.models) if engine else []
    return {
        "main": gateway.preferences()["default"] if gateway is not None else None,
        "routes": _routes(gateway) if gateway is not None else [],
        "providers": providers,
        "tiers": {
            "strong": "Writes text you will send: resume wording, cover letters, role review.",
            "cheap": "Reads and classifies: requirement extraction, relevance, verification, email.",
        },
        "agents": [
            {"name": name, "tier": agent.tier, "isolated": agent.isolated}
            for name, agent in sorted(REGISTRY.items())
        ],
        "preferences": _preferences(services),
    }


def save(services, values: dict) -> dict:
    """Persist the tier choices after checking each one is selectable."""
    tiers = values.get("tiers") or {}
    known = set(catalog.PROVIDERS) | set(LOCAL_DEFAULTS)
    for tier, chosen in tiers.items():
        if tier not in catalog.TIERS:
            raise ValueError(f"Unknown tier: {tier}")
        provider = (chosen or {}).get("provider")
        if provider not in known:
            raise ValueError(f"Unknown AI provider: {provider}")
        if not (chosen or {}).get("model"):
            raise ValueError(f"Choose a model for the {tier} tier")
    stored = services.pref("ai_preferences", {}) or {}
    stored["tiers"] = tiers
    services.set_pref("ai_preferences", stored)
    with services.w.connect() as db:
        services.w.record_event(db, "ai_preferences_updated", tiers=tiers)
    services.sync_projections()
    return _preferences(services)


def test_provider(services, provider_id: str, model: str) -> dict:
    """Make the smallest possible real call, so a bad key fails here not mid-run."""
    if provider_id == "codex":
        return {"ok": True, "provider": provider_id, "model": model,
                "detail": "The local Codex runtime is used directly and needs no key."}
    if provider_id == claude_code.ID:
        ping = {"type": "object", "properties": {"word": {"type": "string"}},
                "required": ["word"], "additionalProperties": False}
        try:
            answer = claude_code.invoke("Reply with the single word: ready", ping, model=model)
        except ValueError as error:
            return {"ok": False, "provider": provider_id, "model": model, "detail": str(error)}
        return {"ok": True, "provider": provider_id, "model": model,
                "detail": f"Answered: {str(answer.get('word', ''))[:40]}"}
    if provider_id not in catalog.PROVIDERS:
        raise ValueError(f"Unknown AI provider: {provider_id}")
    from pydantic import BaseModel

    class Ping(BaseModel):
        word: str

    try:
        llm = models.build(services.w.root, provider_id, model, max_tokens=64)
        answer = llm.with_structured_output(Ping).invoke(
            "Reply with the single word: ready"
        )
    except models.ProviderNotConfigured as error:
        return {"ok": False, "provider": provider_id, "model": model, "detail": str(error)}
    except Exception as error:
        return {"ok": False, "provider": provider_id, "model": model,
                "detail": f"{catalog.PROVIDERS[provider_id]['label']}: {describe_provider_error(error)}"}
    return {"ok": True, "provider": provider_id, "model": model,
            "detail": f"Answered: {answer.word[:40]}"}


def team(services, on_usage=None) -> AgentTeam:
    return AgentTeam.from_preferences(services.w.root, _preferences(services), on_usage)


def choose_main(services, gateway, provider_id: str, model: str) -> dict:
    """One choice for every agent: the gateway default and, where it can, both tiers.

    Per-action overrides are cleared so nothing silently keeps an older choice.
    Work the chosen provider cannot do (web search, Gmail) is routed by the
    gateway to one that can, and the page shows where it went.
    """
    provider = gateway.providers.get(provider_id)
    if provider is None:
        raise ValueError(f"Unknown AI provider: {provider_id}")
    if not provider.configured:
        raise ValueError("That provider is not ready yet. Add its API key (or install it) first.")
    if model not in provider.models:
        raise ValueError("That model is not offered by this provider")
    stored = services.pref("ai_preferences", {}) or {}
    stored["default"] = {"provider": provider_id, "model": model}
    stored["actions"] = {}
    if provider_id in LOCAL_DEFAULTS or provider_id in catalog.PROVIDERS:
        if provider_id == "codex":
            pass  # the chat specialists cannot run on Codex; their tiers stay as they were
        else:
            cheap = claude_code.DEFAULTS["cheap"] if provider_id == claude_code.ID else catalog.default_model(provider_id, "cheap")
            stored["tiers"] = {"strong": {"provider": provider_id, "model": model},
                               "cheap": {"provider": provider_id, "model": cheap}}
    services.set_pref("ai_preferences", stored)
    with services.w.connect() as db:
        services.w.record_event(db, "ai_main_provider_chosen", provider=provider_id, model=model)
    services.sync_projections()
    return overview(services, gateway=gateway)


def save_key(services, provider_id: str, value: str) -> dict:
    """Store a key typed on the page, then prove it with a free model-list call."""
    if provider_id not in catalog.PROVIDERS:
        raise ValueError("This provider does not use an API key")
    spec = catalog.PROVIDERS[provider_id]
    keys.save(services.w.root, spec["key"], value)
    with services.w.connect() as db:
        # The provider only. The key itself is never logged or stored in SQLite.
        services.w.record_event(db, "ai_key_saved", provider=provider_id)
    services.sync_projections()
    listed = catalog.models(services.w.root, provider_id, refresh=True)
    ok = not listed["error"] and bool(listed["models"])
    return {"provider": provider_id, "ok": ok,
            "detail": (f"Key saved and working: {len(listed['models'])} models available."
                       if ok else f"Key saved, but the check failed: {listed['error'] or 'no models were listed'}."),
            "source": keys.source(services.w.root, spec["key"])}


def remove_key(services, provider_id: str) -> dict:
    if provider_id not in catalog.PROVIDERS:
        raise ValueError("This provider does not use an API key")
    spec = catalog.PROVIDERS[provider_id]
    still = keys.remove(services.w.root, spec["key"])
    with services.w.connect() as db:
        services.w.record_event(db, "ai_key_removed", provider=provider_id)
    services.sync_projections()
    return {"provider": provider_id, "source": still,
            "detail": (f"Removed from the app. Another {spec['key']} is still set in {still}; edit that file to remove it."
                       if still else "Key removed.")}
