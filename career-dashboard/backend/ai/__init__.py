"""AI provider gateway and the LangChain specialist-agent layer."""

from pathlib import Path

from .providers import AIGateway, AnthropicProvider, ClaudeCodeProvider, CodexProvider, OpenAIProvider

__all__ = [
    "AIGateway", "AnthropicProvider", "ClaudeCodeProvider", "CodexProvider", "OpenAIProvider",
    "team_for", "any_provider_configured", "ready_providers", "resolve_tiers", "main_choice", "engine",
]

# Where a tier goes when its chosen provider cannot run here: the signed-in local
# runtimes first (no key, no per-call cost), then whichever hosted key exists.
FALLBACK_ORDER = ("claude_code", "codex", "openrouter", "anthropic", "openai", "gemini", "kimi")


def ready_providers(root) -> dict:
    """Which providers can actually run on this Mac right now, by id."""
    from backend.ai import claude_code, codex, models

    ready = dict(models.available(Path(root)))
    ready[claude_code.ID] = claude_code.available()
    ready[codex.ID] = codex.available()
    return ready


def any_provider_configured(root) -> bool:
    """True when a hosted provider has a key here, or a local CLI (Claude Code, Codex) is installed."""
    return any(ready_providers(root).values())


def provider_label(provider_id: str) -> str:
    from backend.ai import catalog, claude_code, codex

    if provider_id == claude_code.ID:
        return "Claude Code"
    if provider_id == codex.ID:
        return "Codex"
    return catalog.PROVIDERS.get(provider_id, {}).get("label", provider_id)


def _default_model(provider_id: str, tier: str) -> str:
    from backend.ai import catalog, claude_code, codex

    if provider_id == claude_code.ID:
        return claude_code.DEFAULTS[tier]
    if provider_id == codex.ID:
        return codex.DEFAULTS[tier]
    return catalog.default_model(provider_id, tier)


def main_choice(preferences: dict, ready: dict) -> tuple[str, str]:
    """The provider and model every background run starts from: the Settings choice,
    else the same built-in the gateway uses (OpenAI with a key here, otherwise Codex)."""
    from backend.ai import codex

    stored = preferences.get("default") or {}
    if stored.get("provider"):
        return stored["provider"], stored.get("model") or _default_model(stored["provider"], "strong")
    if ready.get("openai"):
        return "openai", _default_model("openai", "strong")
    return codex.ID, codex.DEFAULTS["strong"]


def resolve_tiers(root, preferences: dict, ready: dict | None = None) -> tuple[dict, dict]:
    """(provider, model) per tier: the saved choice when it can run here, else the first runtime that can.

    A tier nobody chose follows the main choice, so the chat and the background
    runs share one engine until Settings says otherwise. Returns
    ``AgentTeam.tiers`` and a map naming the provider each tier was moved away
    from (empty when nothing moved). A tier whose provider has no key and no
    fallback keeps its choice, so the call fails with the provider's own clear
    message rather than a silent switch.
    """
    from backend.ai import catalog

    ready = ready if ready is not None else ready_providers(root)
    main, main_model = main_choice(preferences, ready)
    chosen = {}
    for tier in catalog.TIERS:
        stored = (preferences.get("tiers") or {}).get(tier) or {}
        provider = stored.get("provider") or main
        default = main_model if provider == main and tier == "strong" else _default_model(provider, tier)
        chosen[tier] = (provider, stored.get("model") or default)
    order = [p for p in ((main,) + FALLBACK_ORDER) if p]
    tiers, moved = {}, {}
    for tier, (provider, model) in chosen.items():
        if ready.get(provider):
            tiers[tier] = (provider, model)
            continue
        fallback = next((p for p in order if ready.get(p)), None)
        if fallback is None:
            tiers[tier] = (provider, model)
        else:
            chosen_model = main_model if fallback == main and tier == "strong" else _default_model(fallback, tier)
            tiers[tier] = (fallback, chosen_model)
            moved[tier] = provider
    return tiers, moved


def team_for(services, on_usage=None):
    """An AgentTeam built from the saved tier preferences, on a provider that is ready.

    Kept here so callers need no knowledge of where preferences are stored.
    """
    from backend.ai.agents.graph import AgentTeam

    preferences = services.pref("ai_preferences", {}) or {}
    tiers, _moved = resolve_tiers(services.w.root, preferences)
    return AgentTeam(services.w.root, tiers, on_usage)


def engine(services) -> dict:
    """What the assistant's agent loop will run on, in words the page can show.

    ``options`` lists every runtime that is ready here so the person can switch
    from the chat; choosing one goes through ``settings.choose_main`` like the
    Settings tab.
    """
    from backend.ai import catalog, claude_code, codex

    root = services.w.root
    preferences = services.pref("ai_preferences", {}) or {}
    ready = ready_providers(root)
    tiers, moved = resolve_tiers(root, preferences, ready)
    provider, model = tiers["strong"]
    moved_from = moved.get("strong")
    options = []
    for provider_id in FALLBACK_ORDER:
        if not ready.get(provider_id):
            continue
        if provider_id == claude_code.ID:
            listed = list(claude_code.MODELS)
        elif provider_id == codex.ID:
            listed = list(codex.MODELS)
        else:
            cached = (catalog._read_cache(root).get(provider_id) or {}).get("models") or []
            defaults = catalog.PROVIDERS[provider_id]["defaults"]
            listed = list(dict.fromkeys([defaults["strong"], defaults["cheap"], *cached]))[:12]
        for name in listed:
            options.append({"provider": provider_id, "model": name, "label": provider_label(provider_id) + " · " + name})
    runs_provider, runs_model = main_choice(preferences, ready)
    note = None
    if codex.ID in (provider, runs_provider) and ready.get(codex.ID) and not codex.signed_in():
        note = "Codex is installed but not signed in: open the ChatGPT app and sign in, or choose Claude Code."
    return {
        "provider": provider, "model": model, "label": provider_label(provider) + " · " + model,
        "ready": bool(ready.get(provider)),
        "moved_from": provider_label(moved_from) if moved_from else None,
        # What the runs the chat starts (discovery, research, builds) go through
        # unless Settings gave an action its own provider.
        "runs": {"provider": runs_provider, "model": runs_model,
                 "label": provider_label(runs_provider) + " · " + runs_model,
                 "ready": bool(ready.get(runs_provider))},
        "note": note,
        "options": options,
    }
