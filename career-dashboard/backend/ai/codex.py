"""The local Codex runtime as a structured-generation provider for the specialists.

The Codex counterpart of ``claude_code.py``: it runs the ``codex`` CLI that ships
with the ChatGPT app, signed in to the user's ChatGPT plan, so a call needs no
API key. Each call is one-shot and sealed: an empty working directory, read-only
sandbox, no shell tool, no apps, and web search only when the specialist asks.

``services/agents.py`` keeps its own Codex command for the durable agent runs
(it adds the Gmail connector for the mailbox worker). This module exists so the
chat specialists — the assistant's agent loop, the resume tailor, the profile
curator — can run on Codex too, which the specialist team could not do before.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ID = "codex"
LABEL = "Codex (local, free)"
MODELS = ("codex-runtime",)
DEFAULTS = {"strong": "codex-runtime", "cheap": "codex-runtime"}
BUNDLED = "/Applications/ChatGPT.app/Contents/Resources/codex"
TIMEOUT = {"web": 900, "text": 600}


def find_cli() -> Path | None:
    """The Codex binary to run, or None when the ChatGPT app is not installed."""
    override = os.environ.get("CODEX_CLI")
    if override and os.access(override, os.X_OK):
        return Path(override)
    on_path = shutil.which("codex")
    if on_path:
        return Path(on_path)
    if os.access(BUNDLED, os.X_OK):
        return Path(BUNDLED)
    return None


def signed_in() -> bool:
    """Whether the CLI holds a ChatGPT sign-in (``codex login`` writes auth.json)."""
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    return os.path.exists(os.path.join(home, "auth.json"))


def failure_reason(stderr: str, stdout: str = "") -> str:
    """The one line worth showing from a failed ``codex exec``.

    Codex prints a banner (version, workdir, model) before anything goes wrong and
    reports API errors as JSON blobs, so the last error message is the reason;
    the banner never is. A sign-in problem is named as such.
    """
    text = (stderr or "") + "\n" + (stdout or "")
    messages = re.findall(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    reason = messages[-1] if messages else ""
    if not reason:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        errors = [line for line in lines if re.match(r"(?i)^(error|fatal|failed)\b", line)]
        reason = errors[-1] if errors else ""
    reason = " ".join(reason.replace("\\n", " ").split())
    if re.search(r"(?i)not logged in|\blog ?in\b|unauthori[sz]ed|\b401\b|\bauth(entication|orization)?\b", reason):
        return "Codex is not signed in on this Mac: open the ChatGPT app and sign in, then retry."
    return reason[:300]


def available() -> bool:
    return find_cli() is not None


def launcher(cli: Path) -> list[str]:
    """Return a shell-free launcher for a native binary or Windows command shim."""
    if os.name == "nt" and cli.suffix.casefold() in {".cmd", ".bat"}:
        return [os.environ.get("ComSpec", "cmd.exe"), "/d", "/s", "/c", str(cli)]
    return [str(cli)]


def strict_schema(schema: dict) -> dict:
    """A copy of a pydantic JSON schema in the shape strict structured-output APIs accept.

    Every object closes with ``additionalProperties: false`` and lists all of its
    properties as required; ``default`` markers go, because the model must write
    every field. Optional fields keep their ``null`` alternative, so an empty
    value is still expressible.
    """
    def walk(node):
        if isinstance(node, dict):
            node = {key: walk(value) for key, value in node.items() if key != "default"}
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            return node
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node
    return walk(schema)


def command(cli: Path, folder: Path, schema_file: Path, out: Path, *, web: bool) -> list:
    """The exact argument list, kept separate so tests can check it."""
    return launcher(cli) + [
        "exec",
        "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
        "-C", str(folder),
        "-s", "read-only",
        "-c", "features.shell_tool=false",
        "-c", "apps._default.destructive_enabled=false",
        "-c", "apps._default.open_world_enabled=false",
        "-c", "features.apps=false",
        "-c", f'web_search="{"live" if web else "disabled"}"',
        "--output-schema", str(schema_file),
        "-o", str(out),
        "-",
    ]


def run(prompt: str, schema: dict, *, model: str = "codex-runtime", web: bool = False,
        system: str | None = None, timeout: int | None = None) -> tuple[dict, dict]:
    """One structured call. Returns (parsed object, token usage) or raises ValueError."""
    cli = find_cli()
    if cli is None:
        raise ValueError("Codex is not installed on this Mac. Install the ChatGPT app, sign in, then retry.")
    if model not in MODELS:
        raise ValueError("Unsupported Codex model")
    # Codex exec has no system-prompt flag: the instructions travel first on stdin.
    text = (system.strip() + "\n\n---\n\n" if system else "") + prompt
    limit = timeout or TIMEOUT["web" if web else "text"]
    with tempfile.TemporaryDirectory(prefix="career-codex-") as temp:
        folder = Path(temp)
        schema_file, out = folder / "schema.json", folder / "result.json"
        schema_file.write_text(json.dumps(strict_schema(schema)))
        try:
            done = subprocess.run(
                command(cli, folder, schema_file, out, web=web),
                input=text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=limit, cwd=folder,
            )
        except subprocess.TimeoutExpired:
            raise ValueError("Codex reached its time limit. Nothing was saved from this call. Retry a smaller pass.") from None
        if done.returncode or not out.exists():
            said = failure_reason(done.stderr, done.stdout)
            raise ValueError("Codex could not finish" + (f": {said}" if said else "")
                             + " (open the ChatGPT app, check sign-in and usage, then retry)")
        try:
            result = json.loads(out.read_text())
        except json.JSONDecodeError:
            raise ValueError("Codex returned output that did not match the requested schema") from None
    if not isinstance(result, dict):
        raise ValueError("Codex returned output that did not match the requested schema")
    return result, {"input_tokens": None, "output_tokens": None}


def invoke(prompt: str, schema: dict, **options) -> dict:
    """The provider-gateway shape: just the parsed object."""
    return run(prompt, schema, **options)[0]
