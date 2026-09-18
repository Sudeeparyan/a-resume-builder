"""
The provider contract, plus cost accounting and retry policy.

Three implementations sit behind this:
  anthropic_provider  -- an API key from the Settings tab. Full capability.
  claude_cli_provider -- the local Claude Code CLI, riding an existing login.
  null_provider       -- no LLM at all. Every deterministic agent still runs.

Agents never import a provider directly; they ask the registry. That is what
lets the whole app degrade to no-key mode instead of failing.
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

ModelTier = Literal["deep", "mid", "fast"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------
class LLMError(RuntimeError):
    """Base for anything the provider layer raises."""


class ProviderUnavailable(LLMError):
    """No usable provider. Carries a plain-English reason for the UI."""

    def __init__(self, reason: str, fix: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.fix = fix


class QuotaExhausted(LLMError):
    """
    A usage limit was hit and will not clear soon. The runner checkpoints the
    run and schedules a resume rather than failing the whole batch.
    """

    def __init__(self, message: str, retry_after_s: float | None = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s

    def resume_at(self, default_minutes: int = 120) -> datetime:
        secs = self.retry_after_s if self.retry_after_s else default_minutes * 60
        return datetime.now() + timedelta(seconds=secs)


class Refused(LLMError):
    """stop_reason == 'refusal'. Rare here, but must not look like a crash."""


# --------------------------------------------------------------------------
# pricing -- USD per million tokens, from the model table
# --------------------------------------------------------------------------
PRICING: dict[str, tuple[float, float, float]] = {
    # model id            input,  output, cache_read
    "claude-opus-5":      (5.00,  25.00, 0.50),
    "claude-sonnet-5":    (2.00,  10.00, 0.20),
    "claude-haiku-4-5":   (1.00,   5.00, 0.10),
    "claude-opus-4-8":    (5.00,  25.00, 0.50),
}


def price(model: str, tokens_in: int, tokens_out: int, cache_read: int = 0) -> float:
    pin, pout, pcache = PRICING.get(model, (5.00, 25.00, 0.50))
    billable_in = max(0, tokens_in - cache_read)
    return (
        billable_in / 1_000_000 * pin
        + tokens_out / 1_000_000 * pout
        + cache_read / 1_000_000 * pcache
    )


@dataclass
class Usage:
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    model: str = ""
    provider: str = ""

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            tokens_in=self.tokens_in + other.tokens_in,
            tokens_out=self.tokens_out + other.tokens_out,
            cache_read=self.cache_read + other.cache_read,
            cache_write=self.cache_write + other.cache_write,
            cost_usd=self.cost_usd + other.cost_usd,
            duration_ms=self.duration_ms + other.duration_ms,
            model=other.model or self.model,
            provider=other.provider or self.provider,
        )


@dataclass
class LLMResult:
    text: str = ""
    data: dict[str, Any] | None = None      # populated by complete_structured
    usage: Usage = field(default_factory=Usage)
    citations: list[str] = field(default_factory=list)
    stop_reason: str = ""
    raw: Any = None


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str


# --------------------------------------------------------------------------
# retry
# --------------------------------------------------------------------------
@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_delay: float = 2.0
    max_delay: float = 60.0
    # Beyond this, treat it as a real quota wall rather than a transient blip.
    quota_threshold_s: float = 300.0

    def delay_for(self, attempt: int, retry_after: float | None = None) -> float:
        if retry_after is not None:
            return min(retry_after, self.max_delay)
        exp = min(self.max_delay, self.base_delay * (2 ** attempt))
        return exp * (0.5 + random.random() * 0.5)   # jitter, avoid thundering herd


async def with_retry(fn, policy: RetryPolicy, on_retry=None):
    """
    Run an async callable, retrying transient failures.

    A long retry-after is re-raised as QuotaExhausted so the orchestrator can
    checkpoint and resume hours later instead of burning attempts.
    """
    last: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return await fn()
        except QuotaExhausted:
            raise
        except Exception as exc:                       # noqa: BLE001
            last = exc
            retry_after = _retry_after_of(exc)
            if retry_after and retry_after > policy.quota_threshold_s:
                raise QuotaExhausted(str(exc), retry_after) from exc
            if not _is_retryable(exc) or attempt == policy.max_attempts - 1:
                raise
            delay = policy.delay_for(attempt, retry_after)
            if on_retry:
                on_retry(attempt + 1, delay, exc)
            await asyncio.sleep(delay)
    raise last if last else LLMError("retry loop exhausted")


def _retry_after_of(exc: Exception) -> float | None:
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None) or {}
    for h in ("retry-after", "Retry-After", "anthropic-ratelimit-requests-reset"):
        v = headers.get(h) if hasattr(headers, "get") else None
        if v:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
    if isinstance(status, int):
        return status in (408, 409, 429) or status >= 500
    name = type(exc).__name__.lower()
    return any(k in name for k in ("connection", "timeout", "overloaded", "apistatus", "internalserver"))


# --------------------------------------------------------------------------
# the contract
# --------------------------------------------------------------------------
class LLMProvider(ABC):
    name: str = "base"
    supports_web_search: bool = False
    supports_structured: bool = False
    supports_caching: bool = False

    @abstractmethod
    async def available(self) -> tuple[bool, str]:
        """(usable, plain-English reason if not)"""

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        tier: ModelTier = "mid",
        effort: Effort = "high",
        max_tokens: int | None = None,
        cache_prefix: str | None = None,
        web_search: bool = False,
        agent: str = "",
    ) -> LLMResult:
        """Free-text completion."""

    async def complete_structured(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: dict[str, Any],
        tier: ModelTier = "mid",
        effort: Effort = "high",
        max_tokens: int | None = None,
        cache_prefix: str | None = None,
        web_search: bool = False,
        agent: str = "",
    ) -> LLMResult:
        """
        JSON matching `schema`. The default asks for JSON in the prompt and
        parses it; providers that support real structured output override this.
        """
        import json
        import re

        instruction = (
            "Reply with a single JSON object and nothing else. No prose, no code "
            "fence, no explanation before or after.\n\nSchema:\n"
            + json.dumps(schema, indent=2)
        )
        res = await self.complete(
            system=(system + "\n\n" + instruction).strip(),
            messages=messages,
            tier=tier,
            effort=effort,
            max_tokens=max_tokens,
            cache_prefix=cache_prefix,
            web_search=web_search,
            agent=agent,
        )
        res.data = _extract_json(res.text)
        return res

    async def health(self) -> dict[str, Any]:
        ok, why = await self.available()
        return {
            "provider": self.name,
            "available": ok,
            "reason": why,
            "web_search": self.supports_web_search,
            "structured": self.supports_structured,
            "caching": self.supports_caching,
        }


def _extract_json(text: str) -> dict[str, Any] | None:
    """Tolerant JSON extraction -- fences, prose wrappers, trailing commas."""
    import json
    import re

    if not text:
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", s, re.S)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except ValueError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end > start:
        chunk = s[start : end + 1]
        try:
            return json.loads(chunk)
        except ValueError:
            try:
                return json.loads(re.sub(r",\s*([}\]])", r"\1", chunk))
            except ValueError:
                return None
    return None


class Timer:
    def __enter__(self):
        self._t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = int((time.perf_counter() - self._t) * 1000)

    ms: int = 0
