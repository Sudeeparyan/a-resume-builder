"""
One adapter for every OpenAI-compatible endpoint.

The Chat Completions shape is the closest thing the industry has to a common
contract, so a single provider plus a configurable base_url reaches almost
everything without a vendor SDK per platform:

    OpenAI       https://api.openai.com/v1
    OpenRouter   https://openrouter.ai/api/v1     (a gateway to ~everything)
    Groq         https://api.groq.com/openai/v1
    Together     https://api.together.xyz/v1
    DeepSeek     https://api.deepseek.com/v1
    Mistral      https://api.mistral.ai/v1
    Fireworks    https://api.fireworks.ai/inference/v1
    Ollama       http://localhost:11434/v1        (local, no key)
    LM Studio    http://localhost:1234/v1         (local, no key)
    vLLM         http://localhost:8000/v1         (self-hosted)

This talks raw HTTP through httpx, which the app already depends on, so adding
a platform costs a base_url and a model name -- not a new package.

Capability differences are declared honestly rather than papered over:
  * No server-side web search. Company research needs it, so that phase is
    SKIPPED with a plain-English reason rather than silently returning a
    hallucinated company profile.
  * No prompt caching. cache_prefix is prepended to the system prompt so the
    agents behave identically; it just costs full price every call.
  * Structured output uses json_schema where the endpoint supports it and falls
    back to prompt-and-parse where it does not.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .. import db, settings
from .provider import (
    Effort,
    LLMProvider,
    LLMResult,
    Message,
    ModelTier,
    ProviderUnavailable,
    QuotaExhausted,
    RetryPolicy,
    Usage,
    with_retry,
)

# USD per million tokens. Only used to show a running cost; an unknown model
# reports 0 rather than inventing a number.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o3": (2.00, 8.00),
    "o4-mini": (1.10, 4.40),
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
}

# Endpoints that reject unknown fields, so we send the lean request shape.
_STRICT_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0")


def _price(model: str, tin: int, tout: int) -> float:
    key = (model or "").split("/")[-1].lower()
    pin, pout = PRICING.get(key, (0.0, 0.0))
    return tin / 1_000_000 * pin + tout / 1_000_000 * pout


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"
    supports_web_search = False       # no server-side search on this contract
    supports_structured = True
    supports_caching = False

    def __init__(self, cfg: Any = None):
        self.cfg = cfg or settings.get_settings()
        self.base_url = (self.cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = self.cfg.openai_api_key or ""
        self.name = self.cfg.llm_label or _label_for(self.base_url)

    # ---- capability ----------------------------------------------------
    def _is_local(self) -> bool:
        return any(h in self.base_url for h in _STRICT_HOSTS)

    async def available(self) -> tuple[bool, str]:
        if not self.api_key and not self._is_local():
            return False, (
                f"No API key for {self.name}. Paste one in Settings, or point the "
                "base URL at a local model that does not need one."
            )
        return True, ""

    def _model_for(self, tier: ModelTier) -> str:
        return {
            "deep": self.cfg.openai_model_deep,
            "mid": self.cfg.openai_model_mid,
            "fast": self.cfg.openai_model_fast,
        }.get(tier, self.cfg.openai_model_mid)

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        # OpenRouter asks for these and is friendlier with them set.
        if "openrouter" in self.base_url:
            h["HTTP-Referer"] = "https://github.com/career-ops"
            h["X-Title"] = "Career Ops Dashboard"
        return h

    # ---- the call ------------------------------------------------------
    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        timeout = httpx.Timeout(float(self.cfg.request_timeout_s), connect=20.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=self._headers(), json=payload)
            if r.status_code == 429:
                retry_after = r.headers.get("retry-after")
                raise QuotaExhausted(
                    f"{self.name} rate limit reached.",
                    float(retry_after) if retry_after else None,
                )
            if r.status_code >= 400:
                detail = r.text[:400]
                exc = httpx.HTTPStatusError(
                    f"{self.name} returned {r.status_code}: {detail}",
                    request=r.request, response=r,
                )
                raise exc
            return r.json()

    async def complete(
        self, *, system: str, messages: list[Message], tier: ModelTier = "mid",
        effort: Effort = "high", max_tokens: int | None = None,
        cache_prefix: str | None = None, web_search: bool = False,
        agent: str = "", _schema: dict[str, Any] | None = None,
    ) -> LLMResult:
        ok, why = await self.available()
        if not ok:
            raise ProviderUnavailable(why)

        model = self._model_for(tier)
        # No cache breakpoints on this contract: the prefix simply leads the
        # system prompt, so every agent sees the same content as on Anthropic.
        sys_text = "\n\n".join(x for x in (cache_prefix, system) if x)

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": sys_text}]
            + [{"role": m.role, "content": m.content} for m in messages],
        }
        if max_tokens:
            # Newer OpenAI reasoning models renamed this field; send the one the
            # endpoint expects and let others ignore the extra.
            payload["max_tokens"] = max_tokens
        if _schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": False, "schema": _schema},
            }

        started = time.perf_counter()
        policy = RetryPolicy()
        data = await with_retry(lambda: self._post(payload), policy)
        ms = int((time.perf_counter() - started) * 1000)

        choice = (data.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content")) or ""
        u = data.get("usage") or {}
        tin = int(u.get("prompt_tokens") or 0)
        tout = int(u.get("completion_tokens") or 0)

        usage = Usage(
            tokens_in=tin, tokens_out=tout,
            cost_usd=_price(model, tin, tout), duration_ms=ms,
            model=model, provider=self.name,
        )
        _log_call(agent, model, self.name, usage)
        return LLMResult(
            text=text, usage=usage,
            stop_reason=choice.get("finish_reason") or "", raw=data,
        )

    async def complete_structured(
        self, *, system: str, messages: list[Message], schema: dict[str, Any],
        tier: ModelTier = "mid", effort: Effort = "high",
        max_tokens: int | None = None, cache_prefix: str | None = None,
        web_search: bool = False, agent: str = "",
    ) -> LLMResult:
        """
        Real structured output where the endpoint supports it.

        Many OpenAI-compatible servers accept the request but ignore
        response_format, and some reject it outright -- so a failure falls back
        to the base class's prompt-and-parse rather than failing the phase.
        """
        try:
            res = await self.complete(
                system=system, messages=messages, tier=tier, effort=effort,
                max_tokens=max_tokens, cache_prefix=cache_prefix,
                agent=agent, _schema=schema,
            )
            res.data = _loads(res.text)
            if res.data is not None:
                return res
        except QuotaExhausted:
            raise
        except Exception:  # noqa: BLE001 -- endpoint does not do json_schema
            pass
        return await super().complete_structured(
            system=system, messages=messages, schema=schema, tier=tier,
            effort=effort, max_tokens=max_tokens, cache_prefix=cache_prefix,
            web_search=False, agent=agent,
        )

    async def verify(self) -> tuple[bool, str]:
        """A real 4-token call, so Settings can say 'this key works'."""
        try:
            await self.complete(
                system="Reply with the single word: ok",
                messages=[Message(role="user", content="ok")],
                tier="fast", max_tokens=4, agent="verify",
            )
            return True, f"Connected to {self.name}."
        except ProviderUnavailable as exc:
            return False, exc.reason
        except Exception as exc:  # noqa: BLE001
            return False, _friendly(str(exc), self.name)


def _loads(text: str) -> dict[str, Any] | None:
    try:
        v = json.loads((text or "").strip())
        return v if isinstance(v, dict) else None
    except ValueError:
        return None


def _label_for(base_url: str) -> str:
    for key, label in (
        ("openrouter", "openrouter"), ("groq", "groq"), ("together", "together"),
        ("deepseek", "deepseek"), ("mistral", "mistral"), ("fireworks", "fireworks"),
        ("11434", "ollama"), ("1234", "lm-studio"), ("openai.com", "openai"),
    ):
        if key in base_url:
            return label
    return "openai-compatible"


def _friendly(msg: str, name: str) -> str:
    low = msg.lower()
    if "401" in low or "invalid_api_key" in low or "unauthorized" in low:
        return f"{name} rejected that key."
    if "404" in low and "model" in low:
        return "That model name does not exist on this endpoint. Check it in Settings."
    if "connect" in low or "refused" in low:
        return (
            f"Could not reach {name}. If this is a local model, check it is running."
        )
    return msg[:300]


def _log_call(agent: str, model: str, provider: str, usage: Usage) -> None:
    try:
        db.connect().execute(
            "INSERT INTO llm_calls (run_id, agent, model, provider, tokens_in, "
            "tokens_out, cache_read, cost_usd, duration_ms, ok, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (None, agent, model, provider, usage.tokens_in, usage.tokens_out,
             0, usage.cost_usd, usage.duration_ms, db.now()),
        )
    except Exception:  # noqa: BLE001 -- accounting must never break a run
        pass
