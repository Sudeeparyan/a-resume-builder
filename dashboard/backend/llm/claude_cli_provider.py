"""
The local Claude Code CLI as an LLM backend.

This exists for the case the user described: no API key yet, but an existing
Claude Code login. It shells out to `claude -p ... --output-format json`, so it
rides whatever credentials the CLI already has and costs nothing per token.

Trade-offs, stated honestly rather than discovered later:
  * Slower per call -- process startup on every request.
  * No server-side structured output; JSON comes from prompt-and-parse.
  * It has its own WebSearch tool, so company research does work here.
  * The CLI is not on PATH on this machine today, so available() returns a
    plain-English install instruction rather than a stack trace.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from typing import Any

from .. import db, paths, settings
from .provider import (
    Effort, LLMProvider, LLMResult, Message, ModelTier, ProviderUnavailable,
    Timer, Usage, _extract_json,
)

_CANDIDATES = ("claude", "claude.cmd", "claude.exe")


def find_cli() -> str | None:
    for name in _CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    # npm global installs on Windows are often not on the bash PATH
    for guess in (
        os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
        os.path.expanduser("~/AppData/Roaming/npm/claude.cmd"),
        os.path.expanduser("~/.local/bin/claude"),
        "/usr/local/bin/claude",
    ):
        if guess and os.path.exists(guess):
            return guess
    return None


class ClaudeCLIProvider(LLMProvider):
    name = "claude_cli"
    supports_web_search = True      # the CLI's own WebSearch tool
    supports_structured = False     # prompt-and-parse only
    supports_caching = False        # handled inside the CLI, not controllable here

    def __init__(self) -> None:
        self.cfg = settings.get_settings()
        self.exe = find_cli()

    def _model_for(self, tier: ModelTier) -> str:
        return {
            "deep": self.cfg.model_deep,
            "mid": self.cfg.model_mid,
            "fast": self.cfg.model_fast,
        }.get(tier, self.cfg.model_mid)

    async def available(self) -> tuple[bool, str]:
        self.exe = self.exe or find_cli()
        if not self.exe:
            return False, (
                "The Claude Code command line tool was not found. Install it with "
                "'npm install -g @anthropic-ai/claude-code', or paste an API key in Settings."
            )
        return True, ""

    async def complete(
        self, *, system: str, messages: list[Message], tier: ModelTier = "mid",
        effort: Effort = "high", max_tokens: int | None = None,
        cache_prefix: str | None = None, web_search: bool = False,
        agent: str = "", run_id: str | None = None,
    ) -> LLMResult:
        ok, why = await self.available()
        if not ok:
            raise ProviderUnavailable(why, "Install the CLI or use an API key.")

        parts: list[str] = []
        if cache_prefix:
            parts.append(cache_prefix)
        if system:
            parts.append(system)
        for m in messages:
            parts.append(m.content if m.role == "user" else f"[assistant] {m.content}")
        prompt = "\n\n".join(p for p in parts if p)

        cmd = [
            self.exe, "-p", "--output-format", "json",
            "--model", self._model_for(tier),
        ]
        if not web_search:
            cmd += ["--disallowed-tools", "WebSearch,WebFetch"]

        timer = Timer()
        with timer:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(paths.ROOT),
            )
            try:
                out, err = await asyncio.wait_for(
                    proc.communicate(prompt.encode("utf-8")),
                    timeout=float(self.cfg.request_timeout_s),
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise ProviderUnavailable(
                    "The Claude Code CLI did not respond in time.",
                    "Try a smaller batch, or use an API key for long research runs.",
                )

        stdout = out.decode("utf-8", errors="replace")
        stderr = err.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise ProviderUnavailable(
                f"The Claude Code CLI failed: {(stderr or stdout)[:300]}",
                "Check that you are logged in by running 'claude' once in a terminal.",
            )

        text, usage = _parse_cli_json(stdout)
        usage.duration_ms = timer.ms
        usage.model = self._model_for(tier)
        usage.provider = self.name
        try:
            db.connect().execute(
                "INSERT INTO llm_calls (run_id, agent, model, provider, tokens_in,"
                " tokens_out, cache_read, cost_usd, duration_ms, ok, at)"
                " VALUES (?,?,?,?,?,?,?,?,?,1,?)",
                (run_id, agent, usage.model, self.name, usage.tokens_in,
                 usage.tokens_out, usage.cache_read, 0.0, usage.duration_ms, db.now()),
            )
        except Exception:  # noqa: BLE001
            pass

        return LLMResult(text=text, usage=usage, stop_reason="end_turn", raw=stdout)


def _parse_cli_json(stdout: str) -> tuple[str, Usage]:
    """
    The CLI prints one JSON object with `result` plus a usage block. Older
    versions stream JSONL, so fall back to the last parseable object.
    """
    usage = Usage()
    obj: dict[str, Any] | None = None
    try:
        obj = json.loads(stdout)
    except ValueError:
        for line in reversed(stdout.strip().splitlines()):
            try:
                cand = json.loads(line)
            except ValueError:
                continue
            if isinstance(cand, dict) and ("result" in cand or "text" in cand):
                obj = cand
                break

    if not isinstance(obj, dict):
        return stdout.strip(), usage

    text = obj.get("result") or obj.get("text") or ""
    if isinstance(text, list):
        text = "\n".join(
            b.get("text", "") for b in text if isinstance(b, dict) and b.get("type") == "text"
        )
    u = obj.get("usage") or {}
    if isinstance(u, dict):
        usage.tokens_in = int(u.get("input_tokens") or 0)
        usage.tokens_out = int(u.get("output_tokens") or 0)
        usage.cache_read = int(u.get("cache_read_input_tokens") or 0)
    # cost_usd stays 0: the CLI bills against a subscription, not per token.
    return str(text).strip(), usage
