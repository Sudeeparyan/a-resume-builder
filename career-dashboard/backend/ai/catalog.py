"""Live model catalogues.

Model identifiers change faster than this repository does, so the selectable
models are read from each provider rather than hard-coded. Results are cached on
disk because the catalogue only moves when a provider ships something new.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from backend.ai import keys

CACHE_TTL_SECONDS = 24 * 3600

# Two service tiers. The supervisor and anything that writes candidate-facing
# prose use `strong`; extraction, verification and classification use `cheap`.
TIERS = ("strong", "cheap")

PROVIDERS = {
    "openrouter": {
        "label": "OpenRouter",
        "key": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1/models",
        "base_url": "https://openrouter.ai/api/v1",
        "defaults": {"strong": "anthropic/claude-sonnet-5", "cheap": "google/gemini-2.5-flash-lite"},
    },
    "openai": {
        "label": "OpenAI",
        "key": "OPENAI_API_KEY",
        "url": "https://api.openai.com/v1/models",
        "base_url": None,
        "defaults": {"strong": "gpt-5.2", "cheap": "gpt-5-mini"},
    },
    "anthropic": {
        "label": "Claude",
        "key": "ANTHROPIC_API_KEY",
        "url": "https://api.anthropic.com/v1/models",
        "base_url": None,
        "defaults": {"strong": "claude-sonnet-5", "cheap": "claude-haiku-4-5"},
    },
    "gemini": {
        "label": "Gemini",
        "key": "GEMINI_API_KEY",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "base_url": None,
        "defaults": {"strong": "gemini-pro-latest", "cheap": "gemini-3.5-flash-lite"},
    },
    "kimi": {
        "label": "Kimi (Moonshot)",
        "key": "MOONSHOT_API_KEY",
        "url": "https://api.moonshot.ai/v1/models",
        "base_url": "https://api.moonshot.ai/v1",
        "defaults": {"strong": "kimi-k2-0905-preview", "cheap": "kimi-k2-0905-preview"},
    },
}


def _request(url: str, headers: dict, timeout: int = 20) -> dict:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch(provider_id: str, api_key: str) -> list:
    spec = PROVIDERS[provider_id]
    if provider_id == "gemini":
        data = _request(spec["url"] + "?key=" + api_key, {})
        return sorted(m["name"].split("/")[-1] for m in data.get("models", []))
    if provider_id == "anthropic":
        data = _request(spec["url"], {"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        return sorted(m["id"] for m in data.get("data", []))
    data = _request(spec["url"], {"Authorization": "Bearer " + api_key})
    return sorted(m["id"] for m in data.get("data", []))


def _cache_file(root: Path) -> Path:
    return Path(root) / "data" / "model-catalog.json"


def _read_cache(root: Path) -> dict:
    path = _cache_file(root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(root: Path, cache: dict) -> None:
    path = _cache_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def models(root: Path, provider_id: str, refresh: bool = False) -> dict:
    """Selectable models for one provider, with the reason when none are listed."""
    spec = PROVIDERS[provider_id]
    api_key = keys.secret(root, spec["key"])
    if not api_key:
        return {"models": [], "configured": False, "error": None, "fetched_at": None}

    cache = _read_cache(root)
    entry = cache.get(provider_id) or {}
    fresh = entry.get("fetched_at", 0) + CACHE_TTL_SECONDS > time.time()
    if entry.get("models") and fresh and not refresh:
        return {"models": entry["models"], "configured": True, "error": None,
                "fetched_at": entry["fetched_at"], "cached": True}

    try:
        listed = _fetch(provider_id, api_key)
    except urllib.error.HTTPError as error:
        # A stale list beats no list; the caller still sees why the refresh failed.
        return {"models": entry.get("models", []), "configured": True,
                "error": f"{spec['label']} returned HTTP {error.code}",
                "fetched_at": entry.get("fetched_at")}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
        return {"models": entry.get("models", []), "configured": True,
                "error": f"{spec['label']} model list unavailable ({type(error).__name__})",
                "fetched_at": entry.get("fetched_at")}

    cache[provider_id] = {"models": listed, "fetched_at": int(time.time())}
    _write_cache(root, cache)
    return {"models": listed, "configured": True, "error": None,
            "fetched_at": cache[provider_id]["fetched_at"], "cached": False}


def default_model(provider_id: str, tier: str) -> str:
    return PROVIDERS[provider_id]["defaults"][tier]
