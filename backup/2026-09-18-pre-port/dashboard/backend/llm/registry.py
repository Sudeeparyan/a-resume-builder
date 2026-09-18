"""
Picks the provider. Agents ask here, never for a concrete class.

Resolution order when llm_provider is "auto":
  1. an Anthropic API key from Settings   -- full capability
  2. a local Claude Code CLI on PATH      -- rides an existing login
  3. NullProvider                         -- deterministic agents only

The choice is re-resolved whenever Settings change, so pasting a key turns the
AI agents on without restarting anything.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .. import settings
from .anthropic_provider import AnthropicProvider
from .claude_cli_provider import ClaudeCLIProvider
from .openai_provider import OpenAICompatibleProvider
from .null_provider import NullProvider, skip_reason
from .provider import LLMProvider

_current: LLMProvider | None = None
_lock = asyncio.Lock()


async def resolve(force: bool = False) -> LLMProvider:
    global _current
    if _current is not None and not force:
        return _current
    async with _lock:
        if _current is not None and not force:
            return _current
        cfg = settings.get_settings(reload=force)
        choice = cfg.llm_provider

        if choice == "anthropic":
            _current = AnthropicProvider()
        elif choice == "claude_cli":
            _current = ClaudeCLIProvider()
        elif choice == "openai":
            _current = OpenAICompatibleProvider(cfg)
        elif choice == "none":
            _current = NullProvider("AI agents are switched off in Settings.")
        else:
            _current = await _auto(cfg)
        return _current


async def _auto(cfg) -> LLMProvider:
    if cfg.has_key():
        p = AnthropicProvider()
        ok, _ = await p.available()
        if ok:
            return p
    # An OpenAI-compatible endpoint counts as configured when it has a key, or
    # when it points somewhere local that needs none.
    if cfg.openai_api_key or _is_local(cfg.openai_base_url):
        o = OpenAICompatibleProvider(cfg)
        ok, _ = await o.available()
        if ok:
            return o
    cli = ClaudeCLIProvider()
    ok, _ = await cli.available()
    if ok:
        return cli
    return NullProvider()


def _is_local(url: str) -> bool:
    return any(h in (url or "") for h in ("localhost", "127.0.0.1", "0.0.0.0"))


def invalidate() -> None:
    """Call after Settings change so the next request re-resolves."""
    global _current
    _current = None


async def health() -> dict[str, Any]:
    p = await resolve()
    h = await p.health()
    cfg = settings.get_settings()

    key_ok, key_msg = None, ""
    if isinstance(p, (AnthropicProvider, OpenAICompatibleProvider)):
        key_ok, key_msg = await p.verify()

    cli = ClaudeCLIProvider()
    cli_ok, cli_why = await cli.available()

    h.update({
        "mode": cfg.llm_provider,
        "key_set": cfg.has_key(),
        "key_hint": cfg.key_hint(),
        "key_verified": key_ok,
        "key_message": key_msg,
        "cli_available": cli_ok,
        "cli_reason": cli_why,
        "models": (
            {"deep": cfg.openai_model_deep, "mid": cfg.openai_model_mid,
             "fast": cfg.openai_model_fast}
            if isinstance(p, OpenAICompatibleProvider) else
            {"deep": cfg.model_deep, "mid": cfg.model_mid, "fast": cfg.model_fast}
        ),
        "base_url": getattr(p, "base_url", ""),
        "degraded": not h["available"],
        "degraded_note": (
            "" if h["available"] else
            "Running without an AI model. Job finding, the sponsorship gate, "
            "never-re-apply, link checking, keyword scoring and PDF building all "
            "still work. Add a key in Settings to switch on research and tailoring."
        ),
    })
    return h


async def available() -> bool:
    ok, _ = await (await resolve()).available()
    return ok


__all__ = ["resolve", "invalidate", "health", "available", "skip_reason", "LLMProvider"]
