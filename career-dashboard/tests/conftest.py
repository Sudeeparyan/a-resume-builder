"""Keep every test off this PC's own AI apps, its traces and its AI plans' health file.

Codex and Kimi Code list the models a plan offers from files in their home folders
(~/.codex/models_cache.json, ~/.kimi-code/config.toml), and the Kimi card looks for the
VS Code extension. Each test starts with empty homes and no extension, so results never
depend on what is installed here; a test that needs a list writes its own.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "backend/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(autouse=True)
def spans():
    """Every test traces into memory, never into Annie's data folder; a test can read its spans."""
    from backend import telemetry

    if not telemetry.AVAILABLE:
        yield None
        return
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = telemetry.make_provider([exporter], synchronous=True)
    telemetry.use_provider(provider)
    try:
        yield exporter
    finally:
        provider.shutdown()
        telemetry.use_provider(None)


@pytest.fixture(autouse=True)
def no_hosted_tracing(monkeypatch):
    """Inherited developer settings must never upload test data."""
    from backend import HOSTED_TRACING

    monkeypatch.delenv("CAREER_ALLOW_LANGSMITH", raising=False)
    monkeypatch.delenv("CAREER_TRACE_CONTENT", raising=False)
    monkeypatch.delenv("CAREER_OTEL_ENDPOINT", raising=False)
    for name in HOSTED_TRACING:
        monkeypatch.setenv(name, "false")


@pytest.fixture(autouse=True)
def empty_ai_app_homes(tmp_path_factory, monkeypatch):
    from backend.ai import kimi_cli

    homes = tmp_path_factory.mktemp("ai-homes")
    monkeypatch.setenv("CODEX_HOME", str(homes / "codex"))
    monkeypatch.setenv("KIMI_CODE_HOME", str(homes / "kimi-code"))
    monkeypatch.setattr(kimi_cli, "EXTENSION", str(homes / "no-vscode-extension-*"))
    return homes


@pytest.fixture(autouse=True)
def no_auto_by_default(monkeypatch):
    """Auto (the router) would reach the Kimi, Codex, Claude and Antigravity apps installed on
    this PC. Tests keep the older built-in default instead; a test of Auto turns it back on."""
    from backend.ai import router

    monkeypatch.setattr(router, "DEFAULT_WHEN_UNSET", False)


@pytest.fixture(autouse=True)
def template_cover_letters(monkeypatch):
    """Cover letters never reach the AI apps installed on this PC; a test of the AI writer
    passes its own stub team."""
    from backend.services import cover_letters

    monkeypatch.setattr(cover_letters, "writer_team", lambda services: None)


@pytest.fixture(autouse=True)
def rules_only_fit_check(monkeypatch):
    """The requirement check looks for a free AI plan on its own; tests stay on the rules path.
    A test of the AI check hands it a stub team or patches fit.fit_team itself."""
    from backend.services import fit

    real = fit.fit_team
    monkeypatch.setattr(fit, "fit_team", lambda services: None)
    return real


@pytest.fixture(autouse=True)
def private_plan_health(tmp_path_factory, monkeypatch):
    """Rests and usage windows a test records never reach the real .ai-plan-health.json."""
    from backend import paths
    from backend.ai import limits

    real, app = limits._path_for, paths.APP_ROOT.resolve()
    spare = tmp_path_factory.mktemp("plan-health")

    def redirect(root):
        path = real(root)
        try:
            path.resolve().relative_to(app)
        except ValueError:
            return path
        return spare / path.name

    monkeypatch.setattr(limits, "_path_for", redirect)
