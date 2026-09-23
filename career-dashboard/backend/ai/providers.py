"""Server-only OpenAI, Anthropic, Codex and Claude Code structured generation providers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.ai import claude_code, kimi_cli


ACTIONS = {
    "resume_chat": {"structured": True, "web": False, "apps": False},
    "profile_chat": {"structured": True, "web": False, "apps": False},
    "discovery": {"structured": True, "web": True, "apps": False},
    "role_research": {"structured": True, "web": True, "apps": False},
    "requirement_extraction": {"structured": True, "web": False, "apps": False},
    "document_review": {"structured": True, "web": False, "apps": False},
    "email": {"structured": True, "web": False, "apps": True},
}


def _project_env(root: Path) -> dict[str, str]:
    path = root / ".env"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _secret(root: Path, name: str) -> str:
    # The same lookup as the Settings page: environment, then career-dashboard/.env
    # (where keys typed on that page go), then the root .env and keys.txt.
    from backend.ai import keys

    return os.environ.get(name) or _project_env(root).get(name, "") or keys.secret(root, name)


def _json_request(url: str, payload: dict, headers: dict, timeout: int = 90) -> dict:
    request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ValueError(f"AI provider returned HTTP {exc.code}") from None
    except (URLError, TimeoutError):
        raise ValueError("AI provider could not be reached before the timeout") from None


class OpenAIProvider:
    id = "openai"
    models = ("gpt-5.4", "gpt-5.4-mini")
    capabilities = {"structured", "web"}

    def __init__(self, root: Path, transport=_json_request):
        self.root, self.transport = root, transport

    @property
    def configured(self) -> bool:
        return bool(_secret(self.root, "OPENAI_API_KEY"))

    def generate(self, prompt: str, schema: dict, *, model: str, web=False, **_options) -> dict:
        key = _secret(self.root, "OPENAI_API_KEY")
        if not key:
            raise ValueError("OpenAI is not configured on the server")
        if model not in self.models:
            raise ValueError("Unsupported OpenAI model")
        payload = {"model": model, "input": prompt, "text": {"format": {"type": "json_schema", "name": "career_result", "schema": schema, "strict": True}}}
        if web:
            payload["tools"] = [{"type": "web_search"}]
        data = self.transport("https://api.openai.com/v1/responses", payload, {"Authorization": "Bearer " + key})
        text = data.get("output_text")
        if not text:
            for output in data.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        text = content.get("text")
                        break
        try:
            return json.loads(text or "")
        except json.JSONDecodeError:
            raise ValueError("OpenAI returned invalid structured output") from None


class AnthropicProvider:
    id = "anthropic"
    models = ("claude-sonnet-4-6", "claude-haiku-4-5")
    capabilities = {"structured"}

    def __init__(self, root: Path, transport=_json_request):
        self.root, self.transport = root, transport

    @property
    def configured(self) -> bool:
        return bool(_secret(self.root, "ANTHROPIC_API_KEY"))

    def generate(self, prompt: str, schema: dict, *, model: str, web=False, **_options) -> dict:
        key = _secret(self.root, "ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("Claude is not configured on the server")
        if web:
            raise ValueError("Claude is not enabled for actions requiring built-in web access")
        if model not in self.models:
            raise ValueError("Unsupported Claude model")
        payload = {"model": model, "max_tokens": 4096, "messages": [{"role": "user", "content": prompt}], "output_config": {"format": {"type": "json_schema", "schema": schema}}}
        data = self.transport("https://api.anthropic.com/v1/messages", payload, {"x-api-key": key, "anthropic-version": "2023-06-01"})
        text = "".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("Claude returned invalid structured output") from None


class CodexProvider:
    id = "codex"
    models = ("codex-runtime",)
    capabilities = {"structured", "web", "apps"}

    def __init__(self, invoke):
        self.invoke = invoke

    @property
    def configured(self) -> bool:
        return True

    def generate(self, prompt: str, schema: dict, *, model="codex-runtime", **options) -> dict:
        if model not in self.models:
            raise ValueError("Unsupported Codex model")
        return self.invoke(prompt, schema, **{key: options[key] for key in ("web", "apps") if key in options})


class ClaudeCodeProvider:
    """The local Claude Code CLI, signed in to the user's subscription.

    Mirrors CodexProvider: no key, runs on the plan's usage limits. It has web
    search but no Gmail access, so the mailbox worker stays on Codex.
    """

    id = claude_code.ID
    models = claude_code.MODELS
    capabilities = {"structured", "web"}

    def __init__(self, invoke=claude_code.invoke):
        self.invoke = invoke

    @property
    def configured(self) -> bool:
        return claude_code.available()

    # Same convention as the Codex runtime: the web is on unless an action
    # (hiring review, resume chat) switches it off.
    def generate(self, prompt: str, schema: dict, *, model="sonnet", web=True, **_options) -> dict:
        if model not in self.models:
            raise ValueError("Unsupported Claude Code model")
        return self.invoke(prompt, schema, model=model, web=web)


class KimiCliProvider:
    """The local Kimi Code CLI, signed in to the user's membership.

    Mirrors ClaudeCodeProvider: no key, calls count against the membership's
    usage limits. Web search comes from the CLI's built-in tools; it has no
    Gmail access, so the mailbox worker stays on Codex.
    """

    id = kimi_cli.ID
    models = kimi_cli.MODELS
    capabilities = {"structured", "web"}

    def __init__(self, invoke=kimi_cli.invoke):
        self.invoke = invoke

    @property
    def configured(self) -> bool:
        return kimi_cli.available()

    # Same convention as the Codex runtime: the web is on unless an action
    # (hiring review, resume chat) switches it off.
    def generate(self, prompt: str, schema: dict, *, model="kimi-runtime", web=True, **_options) -> dict:
        if model not in self.models:
            raise ValueError("Unsupported Kimi Code model")
        return self.invoke(prompt, schema, model=model, web=web)


class HostedProvider:
    """Any other provider in the Settings catalogue, reached through LangChain.

    Adding a key on the Settings page is enough to make OpenRouter, Gemini or
    Kimi run the agents. These APIs have no built-in web search here, so the
    gateway sends research and discovery to a provider that has one.
    """

    capabilities = {"structured"}

    def __init__(self, root: Path, provider_id: str):
        from backend.ai import catalog

        self.root, self.id, self.spec = root, provider_id, catalog.PROVIDERS[provider_id]

    @property
    def configured(self) -> bool:
        return bool(_secret(self.root, self.spec["key"]))

    @property
    def models(self) -> tuple:
        # The cached live list, never a network call: resolve() runs on every request.
        from backend.ai import catalog

        listed = (catalog._read_cache(self.root).get(self.id) or {}).get("models") or []
        return tuple(dict.fromkeys([*self.spec["defaults"].values(), *listed]))

    def generate(self, prompt: str, schema: dict, *, model: str, **_options) -> dict:
        from backend.ai import models as chat_models
        from backend.ai.agents.graph import describe_provider_error

        if model not in self.models:
            raise ValueError(f"Unsupported {self.spec['label']} model")
        try:
            llm = chat_models.build(self.root, self.id, model, max_tokens=8192, timeout=300)
            shaped = {"title": "career_result", "description": "The requested result.", **schema}
            method = {} if self.id == "gemini" else {"method": "function_calling"}
            result = llm.with_structured_output(shaped, **method).invoke(prompt)
        except chat_models.ProviderNotConfigured as error:
            raise ValueError(str(error)) from None
        except Exception as error:  # provider, network or quota failure
            raise ValueError(f"{self.spec['label']}: {describe_provider_error(error)}") from None
        if not isinstance(result, dict):
            raise ValueError(f"{self.spec['label']} returned output that did not match the requested schema")
        return result


# Where a web- or Gmail-needing action goes when the chosen provider cannot do it.
CAPABLE_ORDER = ("claude_code", "codex", "kimi_cli", "openai")


class AIGateway:
    def __init__(self, service, codex_invoke):
        from backend.ai import catalog

        self.s = service
        self.providers = {provider.id: provider for provider in (OpenAIProvider(service.w.root), AnthropicProvider(service.w.root), CodexProvider(codex_invoke), ClaudeCodeProvider(), KimiCliProvider())}
        for provider_id in catalog.PROVIDERS:
            self.providers.setdefault(provider_id, HostedProvider(service.w.root, provider_id))

    def preferences(self) -> dict:
        # The Settings tab keeps its tier choices under the same key, so read
        # only this gateway's part of it and fill in what is missing.
        configured_default = "openai" if self.providers["openai"].configured else "codex"
        stored = self.s.pref("ai_preferences", {}) or {}
        return {
            "default": stored.get("default") or {"provider": configured_default, "model": self.providers[configured_default].models[0]},
            "actions": stored.get("actions") or {},
            "fallback": stored.get("fallback"),
        }

    def catalog(self, action: str | None = None) -> dict:
        needs = ACTIONS.get(action or "", {})
        providers = []
        for provider in self.providers.values():
            compatible = all(not needed or capability in provider.capabilities for capability, needed in needs.items())
            providers.append({"id": provider.id, "configured": provider.configured, "compatible": compatible, "models": list(provider.models), "capabilities": sorted(provider.capabilities)})
        return {"providers": providers, "actions": ACTIONS, "preferences": self.preferences()}

    def save_preferences(self, values: dict) -> dict:
        default = values.get("default", {})
        self.resolve("requirement_extraction", default.get("provider"), default.get("model"), require_configured=False)
        for action, choice in values.get("actions", {}).items():
            if action not in ACTIONS:
                raise ValueError("Unknown AI action")
            self.resolve(action, choice.get("provider"), choice.get("model"), require_configured=False)
        fallback = values.get("fallback")
        if fallback:
            self.resolve("requirement_extraction", fallback.get("provider"), fallback.get("model"), require_configured=False)
        # Keep the Settings tab's tiers, which share this key.
        stored = self.s.pref("ai_preferences", {}) or {}
        stored.update({"default": default, "actions": values.get("actions", {}), "fallback": fallback})
        self.s.set_pref("ai_preferences", stored)
        with self.s.w.connect() as db:
            self.s.w.record_event(db, "ai_preferences_updated", preferences=values)
        self.s.sync_projections()
        return self.preferences()

    def resolve(self, action: str, provider_id=None, model=None, *, require_configured=True):
        if action not in ACTIONS:
            raise ValueError("Unknown AI action")
        preferences = self.preferences()
        override = preferences.get("actions", {}).get(action)
        choice = override or preferences.get("default", {})
        explicit = bool(provider_id or override)
        provider_id = provider_id or choice.get("provider")
        provider = self.providers.get(provider_id)
        if not provider:
            raise ValueError("Unknown AI provider")
        needs = ACTIONS[action]
        if not explicit and any(needed and name not in provider.capabilities for name, needed in needs.items()):
            # The main choice cannot do this action (no web search, no Gmail):
            # use the first ready provider that can, rather than fail the run.
            for candidate in CAPABLE_ORDER:
                other = self.providers[candidate]
                if other.configured and all(not needed or name in other.capabilities for name, needed in needs.items()):
                    provider, provider_id, model = other, candidate, other.models[0]
                    break
        model = model or choice.get("model") or provider.models[0]
        if model not in provider.models:
            raise ValueError("This model is not available for the selected provider")
        needs = ACTIONS[action]
        missing = [name for name, needed in needs.items() if needed and name not in provider.capabilities]
        if missing:
            raise ValueError(f"{provider_id} is not compatible with {action}: missing {', '.join(missing)}")
        if require_configured and not provider.configured:
            raise ValueError(f"{provider_id} is not configured on the server")
        return provider, model

    def generate(self, action: str, prompt: str, schema: dict, *, provider=None, model=None, **options) -> dict:
        selected, model = self.resolve(action, provider, model)
        try:
            return selected.generate(prompt, schema, model=model, **options)
        except ValueError as error:
            # Graceful fallback: the Settings page can name a backup provider.
            # One retry, recorded, and the UI surfaces that it happened.
            fallback = self.preferences().get("fallback") or {}
            fallback_id = fallback.get("provider")
            if not fallback_id or fallback_id == selected.id:
                raise
            try:
                backup, backup_model = self.resolve(action, fallback_id, fallback.get("model"))
            except ValueError:
                raise error from None
            try:
                result = backup.generate(prompt, schema, model=backup_model, **options)
            except ValueError:
                raise error from None
            with self.s.w.connect() as db:
                self.s.w.record_event(
                    db, "provider_fallback", ai_action=action,
                    from_provider=selected.id, to_provider=backup.id,
                    reason=str(error)[:300],
                )
            return result
