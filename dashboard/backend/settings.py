"""
Configuration, and the API key.

She is not a developer, so nothing here ever requires editing a file: the
Settings tab writes dashboard/.env through save_key(). The .env is gitignored
and the key is never returned to the browser in full -- only a masked hint.
"""

from __future__ import annotations

import os
import re
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import paths

ProviderName = Literal["anthropic", "claude_cli", "openai", "none"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(paths.ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM -------------------------------------------------------------
    anthropic_api_key: str = ""
    llm_provider: ProviderName | Literal["auto"] = "auto"

    # --- any OpenAI-compatible platform ----------------------------------
    # One base URL reaches OpenAI, OpenRouter, Groq, Together, DeepSeek,
    # Mistral, Fireworks, Ollama, LM Studio and vLLM. Adding a platform costs a
    # URL and a model name, not a package.
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_deep: str = "gpt-5"
    openai_model_mid: str = "gpt-5-mini"
    openai_model_fast: str = "gpt-5-nano"
    llm_label: str = ""              # what to call it in the UI; blank = inferred

    # --- the morning brief -----------------------------------------------
    daily_enabled: bool = False
    daily_at: str = "09:00"          # local time, 24h
    daily_job_count: int = 10
    daily_build_resumes: bool = True
    daily_last_run: str = ""         # ISO date of the last completed brief

    # Opus where judgement and honesty matter, Sonnet for extraction,
    # Haiku for mechanical work. See agents/base.py for the per-agent mapping.
    model_deep: str = "claude-opus-5"
    model_mid: str = "claude-sonnet-5"
    model_fast: str = "claude-haiku-4-5"

    max_output_tokens: int = 16000
    request_timeout_s: int = 600

    # --- job sources -----------------------------------------------------
    enable_ats_boards: bool = True        # greenhouse / lever / ashby -- free, no key
    enable_feeds: bool = True             # remotive / remoteok / arbeitnow -- free, no key
    enable_usajobs: bool = False          # federal only; needs an email header
    enable_adzuna: bool = False
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    usajobs_email: str = ""
    enable_workspace_import: bool = True  # read what /hunt already produced
    enable_web_discovery: bool = False    # Claude web search finds NEW companies; costs tokens

    # --- behaviour -------------------------------------------------------
    default_job_count: int = 10
    max_parallel_llm: int = 4
    max_parallel_http: int = 8
    max_parallel_tectonic: int = 2
    link_check_delay_s: float = 2.0       # be polite to job boards
    verify_links: bool = True

    # --- server ----------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ])

    # --- resilience ------------------------------------------------------
    max_retries: int = 5
    quota_retry_minutes: int = 120        # a hard usage limit: wait, checkpoint, resume

    def key_hint(self) -> str:
        k = self.anthropic_api_key.strip()
        if not k:
            return ""
        return f"{k[:11]}…{k[-4:]}" if len(k) > 18 else "set"

    def has_key(self) -> bool:
        return bool(self.anthropic_api_key.strip())


_settings: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    global _settings
    if _settings is None or reload:
        _settings = Settings()
        # An exported env var still wins, matching normal SDK behaviour.
        env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if env_key and not _settings.anthropic_api_key:
            _settings.anthropic_api_key = env_key
    return _settings


_KEY_RE = re.compile(r"^sk-ant-[A-Za-z0-9_\-]{20,}$")


def validate_key_shape(key: str) -> tuple[bool, str]:
    k = (key or "").strip()
    if not k:
        return False, "The key is empty."
    if not k.startswith("sk-ant-"):
        return False, "An Anthropic key starts with 'sk-ant-'. Check you copied the whole thing."
    if not _KEY_RE.match(k):
        return False, "That does not look like a complete key — it may have been cut short."
    return True, ""


def _read_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not paths.ENV_FILE.exists():
        return out
    for line in paths.read_text(paths.ENV_FILE).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def write_env(updates: dict[str, Any]) -> None:
    """Merge into dashboard/.env, preserving anything already there."""
    env = _read_env()
    for k, v in updates.items():
        key = k.upper()
        if v is None or v == "":
            env.pop(key, None)
        else:
            env[key] = str(v)
    body = (
        "# Written by the dashboard Settings tab. Gitignored — never commit this.\n"
        + "\n".join(f"{k}={v}" for k, v in sorted(env.items()))
        + "\n"
    )
    paths.write_text(paths.ENV_FILE, body)
    get_settings(reload=True)


def save_key(key: str) -> tuple[bool, str]:
    ok, why = validate_key_shape(key)
    if not ok:
        return False, why
    write_env({"ANTHROPIC_API_KEY": key.strip()})
    return True, "Key saved."


def clear_key() -> None:
    write_env({"ANTHROPIC_API_KEY": ""})
