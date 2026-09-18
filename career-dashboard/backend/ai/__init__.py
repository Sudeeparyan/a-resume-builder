"""AI provider gateway and the LangChain specialist-agent layer."""

from pathlib import Path

from .providers import AIGateway, AnthropicProvider, ClaudeCodeProvider, CodexProvider, OpenAIProvider

__all__ = [
    "AIGateway", "AnthropicProvider", "ClaudeCodeProvider", "CodexProvider", "OpenAIProvider",
    "team_for", "any_provider_configured",
]


def any_provider_configured(root) -> bool:
    """True when a hosted provider has a key here, or the local Claude Code CLI is installed."""
    from backend.ai import claude_code, models

    return any(models.available(Path(root)).values()) or claude_code.available()


def team_for(services, on_usage=None):
    """An AgentTeam built from the saved tier preferences.

    Kept here so callers need no knowledge of where preferences are stored.
    """
    from backend.ai.agents.graph import AgentTeam

    preferences = services.pref("ai_preferences", {}) or {}
    return AgentTeam.from_preferences(services.w.root, preferences, on_usage)
