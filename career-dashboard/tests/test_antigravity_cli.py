"""Google Antigravity's CLI (agy) as a local, signed-in provider beside Claude Code, Codex and Kimi Code.

No real CLI runs here: subprocess.run is replaced by a stand-in that writes the JSON
envelope documented for headless mode (https://antigravity.google/docs/cli/headless/)
to the stdout file the provider hands over.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from backend.ai import FALLBACK_ORDER, antigravity_cli, ready_providers, settings as ai_settings  # noqa: E402
from backend.ai.agents import schemas  # noqa: E402
from backend.ai.agents.graph import AgentError, AgentTeam  # noqa: E402
from backend.ai.providers import CAPABLE_ORDER, AIGateway  # noqa: E402
from test_career_workspace import workspace  # noqa: E402,F401
from test_workspace_v2 import service  # noqa: E402,F401

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
          "additionalProperties": False}


def fake_cli(tmp_path, name="agy.exe"):
    path = tmp_path / name
    path.write_text("binary")
    return path


def envelope(status="SUCCESS", structured=None, response="", error=None):
    data = {"conversation_id": "c1", "status": status, "response": response, "duration_seconds": 1.2, "num_turns": 1,
            "usage": {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}}
    if structured is not None:
        data["structured_output"] = structured
    if error:
        data["error"] = error
    return json.dumps(data, indent=2)


def fake_run(out="", err="", code=0, seen=None):
    def run(cmd, **options):
        if seen is not None:
            seen.update(cmd=cmd, cwd=options["cwd"], timeout=options["timeout"],
                        files=sorted(p.name for p in Path(options["cwd"]).iterdir()))
            schema_path = Path(cmd[cmd.index("--json-schema") + 1])
            seen["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
            prompt_file = Path(options["cwd"], "prompt.md")
            seen["prompt_file"] = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else None
        options["stdout"].write(out)
        options["stdout"].flush()
        return subprocess.CompletedProcess(cmd, code, stdout=None, stderr=err)
    return run


def test_the_cli_is_found_on_path_by_override_or_not_at_all(tmp_path, monkeypatch):
    override = fake_cli(tmp_path)
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(override))
    assert antigravity_cli.find_cli() == override
    monkeypatch.delenv("ANTIGRAVITY_CLI")
    monkeypatch.setattr(antigravity_cli.shutil, "which", lambda name: str(override) if name == "agy" else None)
    assert antigravity_cli.find_cli() == override
    monkeypatch.setattr(antigravity_cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(antigravity_cli, "BUNDLED", ())
    assert antigravity_cli.available() is False
    with pytest.raises(ValueError, match="not installed"):
        antigravity_cli.invoke("hi", SCHEMA)


def test_the_command_is_headless_json_sandboxed_and_never_auto_approves(tmp_path):
    cmd = antigravity_cli.command(fake_cli(tmp_path), "the prompt", "schema.json", model="antigravity-runtime", timeout=600)
    assert cmd[1:3] == ["-p", "the prompt"]
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert cmd[cmd.index("--json-schema") + 1] == "schema.json"
    assert "--sandbox" in cmd and cmd[cmd.index("--print-timeout") + 1] == "9m"
    assert "--dangerously-skip-permissions" not in cmd
    assert "--model" not in cmd  # the runtime choice uses the CLI's own model
    pinned = antigravity_cli.command(fake_cli(tmp_path), "p", "s.json", model="gemini-3.1-pro-high", timeout=900)
    assert pinned[pinned.index("--model") + 1] == "gemini-3.1-pro-high"


def test_a_structured_answer_and_its_usage_come_back(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(fake_cli(tmp_path)))
    seen = {}
    monkeypatch.setattr(antigravity_cli.subprocess, "run", fake_run(out=envelope(structured={"ok": True}), seen=seen))
    result, usage = antigravity_cli.run("the task", SCHEMA, system="Be brief.")
    assert result == {"ok": True} and usage == {"input_tokens": 120, "output_tokens": 30}
    prompt = seen["cmd"][seen["cmd"].index("-p") + 1]
    assert prompt.startswith("Be brief.") and prompt.endswith("the task")
    assert seen["schema"] == SCHEMA and seen["timeout"] == antigravity_cli.TIMEOUT["text"]
    assert seen["files"] == ["result.json", "schema.json"]  # a sealed, empty working folder


def test_a_long_prompt_travels_in_a_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(fake_cli(tmp_path)))
    seen = {}
    monkeypatch.setattr(antigravity_cli.subprocess, "run", fake_run(out=envelope(structured={"ok": False}), seen=seen))
    long_prompt = "x" * (antigravity_cli.INLINE_LIMIT + 10)
    assert antigravity_cli.invoke(long_prompt, SCHEMA, web=True) == {"ok": False}
    assert seen["cmd"][seen["cmd"].index("-p") + 1] == antigravity_cli.FILE_HANDOFF
    assert seen["prompt_file"] == long_prompt and seen["timeout"] == antigravity_cli.TIMEOUT["web"]


def test_the_response_text_is_parsed_when_structured_output_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(fake_cli(tmp_path)))
    banner = "agy 1.4.0\n" + envelope(response='```json\n{"ok": true}\n```')
    monkeypatch.setattr(antigravity_cli.subprocess, "run", fake_run(out=banner))
    assert antigravity_cli.invoke("hi", SCHEMA) == {"ok": True}
    monkeypatch.setattr(antigravity_cli.subprocess, "run", fake_run(out=envelope(response="I could not do that")))
    with pytest.raises(ValueError, match="did not match"):
        antigravity_cli.invoke("hi", SCHEMA)


@pytest.mark.parametrize("error,stderr,expected", [
    ("authentication required", "", "not signed in"),
    ("RESOURCE_EXHAUSTED: quota exceeded", "", "usage limit"),
    ("unknown model 'gemini-9'", "", "does not offer that model"),
    ("", "agy: something odd happened", "could not finish"),
])
def test_failures_say_what_to_do(tmp_path, monkeypatch, error, stderr, expected):
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(fake_cli(tmp_path)))
    monkeypatch.setattr(antigravity_cli.subprocess, "run", fake_run(out=envelope(status="ERROR", error=error), err=stderr, code=1))
    with pytest.raises(ValueError, match=expected):
        antigravity_cli.invoke("hi", SCHEMA)


def test_timeouts_and_unknown_models_fail_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_CLI", str(fake_cli(tmp_path)))

    def timeout(cmd, **options):
        raise subprocess.TimeoutExpired(cmd, options["timeout"])

    monkeypatch.setattr(antigravity_cli.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="time limit"):
        antigravity_cli.invoke("hi", SCHEMA, web=True)
    with pytest.raises(ValueError, match="Unsupported Antigravity model"):
        antigravity_cli.invoke("hi", SCHEMA, model="gpt-9")


def test_antigravity_is_a_local_runtime_in_every_list(service, monkeypatch):
    monkeypatch.setattr(antigravity_cli, "available", lambda: True)
    assert "antigravity_cli" in FALLBACK_ORDER and "antigravity_cli" in CAPABLE_ORDER
    assert ready_providers(service.w.root)["antigravity_cli"] is True
    gateway = AIGateway(service, lambda *a, **k: {})
    provider, model = gateway.resolve("discovery", "antigravity_cli", "antigravity-runtime")
    assert provider.id == "antigravity_cli" and "web" in provider.capabilities
    with pytest.raises(ValueError):
        gateway.resolve("email", "antigravity_cli", "antigravity-runtime")  # Gmail stays on Codex
    calls = []
    gateway.providers["antigravity_cli"].invoke = lambda prompt, schema, **o: calls.append(o) or {"ok": True}
    assert gateway.generate("discovery", "find", SCHEMA, provider="antigravity_cli", model="antigravity-runtime") == {"ok": True}
    assert calls == [{"model": "antigravity-runtime", "web": True}]
    listed = {p["id"]: p for p in ai_settings.overview(service, gateway=gateway)["providers"]}
    assert listed["antigravity_cli"]["configured"] and listed["antigravity_cli"]["kind"] == "local"
    saved = ai_settings.save(service, {"tiers": {"strong": {"provider": "antigravity_cli", "model": "antigravity-runtime"},
                                                 "cheap": {"provider": "antigravity_cli", "model": "gemini-3.8-flash-medium"}}})
    assert saved["tiers"]["cheap"] == {"provider": "antigravity_cli", "model": "gemini-3.8-flash-medium"}


def test_settings_test_button_reports_install_and_answers(service, monkeypatch):
    monkeypatch.setattr(antigravity_cli, "available", lambda: False)
    result = ai_settings.test_provider(service, "antigravity_cli", "antigravity-runtime")
    assert not result["ok"] and "agy install" in result["detail"]
    monkeypatch.setattr(antigravity_cli, "available", lambda: True)
    monkeypatch.setattr(antigravity_cli, "invoke", lambda prompt, schema, **o: {"word": "ready"})
    assert ai_settings.test_provider(service, "antigravity_cli", "antigravity-runtime")["ok"] is True


def test_specialists_run_through_the_cli_and_are_schema_checked(tmp_path, monkeypatch):
    seen, recorded = {}, []

    def run(prompt, schema, **options):
        seen.update(prompt=prompt, schema=schema, **options)
        return {"role_family_matches": True, "seniority_suitable": True, "location_matches": True,
                "hard_blockers": [], "reasons": ["analyst role"]}, {"input_tokens": 5, "output_tokens": 2}

    monkeypatch.setattr(antigravity_cli, "run", run)
    team = AgentTeam(tmp_path, {"strong": ("antigravity_cli", "antigravity-runtime"),
                                "cheap": ("antigravity_cli", "antigravity-runtime")}, on_usage=recorded.append)
    verdict = team.run("relevance_judge", {"posting": {"title": "Data Analyst"}, "candidate_summary": "BI"})
    assert isinstance(verdict, schemas.RelevanceVerdict) and verdict.reasons == ["analyst role"]
    assert seen["model"] == "antigravity-runtime" and seen["web"] is False
    assert "Data Analyst" in seen["prompt"] and "Data Analyst" not in seen["system"]
    assert recorded[0]["provider"] == "antigravity_cli"

    def down(*a, **k):
        raise ValueError("Your Antigravity usage limit is reached. Wait for it to reset, then retry.")

    monkeypatch.setattr(antigravity_cli, "run", down)
    with pytest.raises(AgentError, match="usage limit"):
        team.run("relevance_judge", {})
