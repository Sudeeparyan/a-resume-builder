"""
The Anthropic API provider -- the primary path once a key is in Settings.

Notes that are easy to get wrong and are load-bearing here:
  * thinking is {"type": "adaptive"}. budget_tokens is REJECTED with a 400 on
    Opus 5 and Sonnet 5.
  * effort lives inside output_config, not at the top level.
  * structured output is output_config["format"], not the deprecated
    output_format parameter.
  * the context/ fact base is identical across every agent in a run, so it goes
    first behind a cache_control breakpoint. Caching is prefix-match: tools,
    then system, then messages -- anything volatile must come after.
  * web search is the server-side tool web_search_20260209, which is what makes
    the company research agent possible at all.
"""

from __future__ import annotations

from typing import Any

from .. import db, settings
from .provider import (
    Effort, LLMResult, Message, ModelTier, ProviderUnavailable, Refused,
    RetryPolicy, Timer, Usage, LLMProvider, price, with_retry,
)

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}
WEB_FETCH_TOOL = {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8}


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    supports_web_search = True
    supports_structured = True
    supports_caching = True

    def __init__(self, api_key: str | None = None):
        self.cfg = settings.get_settings()
        self.api_key = (api_key or self.cfg.anthropic_api_key or "").strip()
        self._client: Any = None
        self._verified: bool | None = None

    # -- plumbing ---------------------------------------------------------
    def _model_for(self, tier: ModelTier) -> str:
        return {
            "deep": self.cfg.model_deep,
            "mid": self.cfg.model_mid,
            "fast": self.cfg.model_fast,
        }.get(tier, self.cfg.model_mid)

    def client(self):
        if self._client is None:
            if not self.api_key:
                raise ProviderUnavailable(
                    "No Anthropic API key is set.",
                    "Open the Settings tab and paste a key beginning with sk-ant-.",
                )
            try:
                from anthropic import AsyncAnthropic
            except ImportError as exc:
                raise ProviderUnavailable(
                    "The anthropic package is not installed.",
                    "Run: python -m pip install anthropic",
                ) from exc
            self._client = AsyncAnthropic(
                api_key=self.api_key, timeout=float(self.cfg.request_timeout_s), max_retries=0
            )
        return self._client

    async def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "No API key set. Paste one in Settings to turn on the AI agents."
        try:
            self.client()
        except ProviderUnavailable as exc:
            return False, exc.reason
        return True, ""

    async def verify(self) -> tuple[bool, str]:
        """A real one-token call, so Settings can say 'this key works'."""
        ok, why = await self.available()
        if not ok:
            return False, why
        try:
            await self.client().messages.create(
                model=self.cfg.model_fast,
                max_tokens=4,
                messages=[{"role": "user", "content": "hi"}],
            )
            self._verified = True
            return True, "Key works."
        except Exception as exc:  # noqa: BLE001
            self._verified = False
            status = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if status == 401:
                return False, "That key was rejected. Check it was copied in full."
            if status == 429:
                return False, "The key is valid but is currently rate limited."
            if status == 400 and "credit" in str(exc).lower():
                return False, "The key is valid but the account has no credit."
            return False, f"Could not reach the Claude API: {exc}"

    # -- requests ---------------------------------------------------------
    def _build(
        self,
        *,
        system: str,
        messages: list[Message],
        tier: ModelTier,
        effort: Effort,
        max_tokens: int | None,
        cache_prefix: str | None,
        web_search: bool,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # The stable prefix goes first and carries the breakpoint; the volatile
        # per-job instructions follow it so the cache survives across agents.
        system_blocks: list[dict[str, Any]] = []
        if cache_prefix:
            system_blocks.append({
                "type": "text",
                "text": cache_prefix,
                "cache_control": {"type": "ephemeral"},
            })
        if system:
            system_blocks.append({"type": "text", "text": system})

        req: dict[str, Any] = {
            "model": self._model_for(tier),
            "max_tokens": max_tokens or self.cfg.max_output_tokens,
            "system": system_blocks or system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
        }
        if web_search:
            req["tools"] = [WEB_SEARCH_TOOL, WEB_FETCH_TOOL]
        if schema is not None:
            req["output_config"]["format"] = {
                "type": "json_schema", "schema": schema,
            }
        return req

    async def _send(self, req: dict[str, Any], agent: str, run_id: str | None) -> LLMResult:
        policy = RetryPolicy(max_attempts=self.cfg.max_retries)
        client = self.client()
        timer = Timer()

        async def call():
            # Streaming keeps long research calls under the HTTP timeout.
            async with client.messages.stream(**req) as stream:
                return await stream.get_final_message()

        with timer:
            msg = await with_retry(call, policy)

        text_parts: list[str] = []
        citations: list[str] = []
        for block in getattr(msg, "content", []) or []:
            btype = getattr(block, "type", "")
            if btype == "text":
                text_parts.append(getattr(block, "text", "") or "")
                for c in getattr(block, "citations", None) or []:
                    url = getattr(c, "url", None)
                    if url:
                        citations.append(url)
            elif btype == "web_search_tool_result":
                content = getattr(block, "content", None)
                if isinstance(content, list):
                    for r in content:
                        url = getattr(r, "url", None)
                        if url:
                            citations.append(url)

        u = getattr(msg, "usage", None)
        tin = getattr(u, "input_tokens", 0) or 0
        tout = getattr(u, "output_tokens", 0) or 0
        cread = getattr(u, "cache_read_input_tokens", 0) or 0
        cwrite = getattr(u, "cache_creation_input_tokens", 0) or 0
        model = req["model"]
        usage = Usage(
            tokens_in=tin + cread + cwrite, tokens_out=tout,
            cache_read=cread, cache_write=cwrite,
            cost_usd=price(model, tin, tout, cread),
            duration_ms=timer.ms, model=model, provider=self.name,
        )

        stop = getattr(msg, "stop_reason", "") or ""
        _log_call(run_id, agent, model, self.name, usage, ok=True)
        if stop == "refusal":
            raise Refused(f"The model declined this request ({agent or 'agent'}).")

        return LLMResult(
            text="\n".join(p for p in text_parts if p).strip(),
            usage=usage,
            citations=list(dict.fromkeys(citations)),
            stop_reason=stop,
            raw=msg,
        )

    async def complete(
        self, *, system: str, messages: list[Message], tier: ModelTier = "mid",
        effort: Effort = "high", max_tokens: int | None = None,
        cache_prefix: str | None = None, web_search: bool = False,
        agent: str = "", run_id: str | None = None,
    ) -> LLMResult:
        req = self._build(
            system=system, messages=messages, tier=tier, effort=effort,
            max_tokens=max_tokens, cache_prefix=cache_prefix, web_search=web_search,
        )
        return await self._send(req, agent, run_id)

    async def complete_structured(
        self, *, system: str, messages: list[Message], schema: dict[str, Any],
        tier: ModelTier = "mid", effort: Effort = "high",
        max_tokens: int | None = None, cache_prefix: str | None = None,
        web_search: bool = False, agent: str = "", run_id: str | None = None,
    ) -> LLMResult:
        # Server-side structured output and server-side tools are not combinable,
        # so a research call falls back to prompt-and-parse.
        if web_search:
            return await super().complete_structured(
                system=system, messages=messages, schema=schema, tier=tier,
                effort=effort, max_tokens=max_tokens, cache_prefix=cache_prefix,
                web_search=True, agent=agent,
            )
        req = self._build(
            system=system, messages=messages, tier=tier, effort=effort,
            max_tokens=max_tokens, cache_prefix=cache_prefix, web_search=False,
            schema=schema,
        )
        try:
            res = await self._send(req, agent, run_id)
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            if status != 400:
                raise
            return await super().complete_structured(
                system=system, messages=messages, schema=schema, tier=tier,
                effort=effort, max_tokens=max_tokens, cache_prefix=cache_prefix,
                agent=agent,
            )
        from .provider import _extract_json
        res.data = _extract_json(res.text)
        return res


def _log_call(
    run_id: str | None, agent: str, model: str, provider: str,
    usage: Usage, ok: bool, error: str | None = None,
) -> None:
    try:
        db.connect().execute(
            "INSERT INTO llm_calls (run_id, agent, model, provider, tokens_in, tokens_out,"
            " cache_read, cost_usd, duration_ms, ok, error, at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, agent, model, provider, usage.tokens_in, usage.tokens_out,
             usage.cache_read, usage.cost_usd, usage.duration_ms, 1 if ok else 0,
             error, db.now()),
        )
    except Exception:  # noqa: BLE001 -- accounting must never break a run
        pass
