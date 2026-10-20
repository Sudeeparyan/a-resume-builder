"""The local Google Antigravity CLI (``agy``) as a structured-generation provider.

The Antigravity counterpart of ``claude_code.py`` and ``kimi_cli.py``: it runs the
``agy`` CLI that ships with Google Antigravity, signed in to the user's Google
account, so every call counts against that account's Antigravity usage limits and
needs no API key.

Each call is one-shot and sealed off: ``agy -p`` (headless "print" mode) runs one
prompt in an empty temporary folder and exits. ``--output-format json`` returns one
JSON envelope; ``--json-schema`` makes the CLI enforce the schema and return the
object as ``structured_output`` (the schema travels as a file in that folder, since
schemas can be long). ``--sandbox`` keeps terminal sandbox restrictions on, and
``--dangerously-skip-permissions`` is never passed: a tool that would need approval
(a command, a file write) is refused by the CLI and the run carries on. The CLI has
no system-prompt flag, so system text is placed before the task.

As with Kimi Code on Windows, a prompt past the safe command-line length is written
to prompt.md in the sealed folder and the CLI is asked to read it, and stdout is
captured through a file rather than a pipe.

Flags follow Google's headless-mode documentation
(https://antigravity.google/docs/cli/headless/). Run ``agy -p "hi"`` once in a
terminal to sign in; an unauthenticated headless run exits with "authentication
required" instead of hanging, which is reported here as a sign-in problem.
"""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.ai import limits

ID = "antigravity_cli"
LABEL = "Google Antigravity (local, Google account)"
# "antigravity-runtime" uses the model the CLI is set to (no --model flag), so the
# choice never goes stale; the named slugs come from `agy models` and pin one model.
RUNTIME = "antigravity-runtime"
MODELS = (RUNTIME, "gemini-3.1-pro-high", "gemini-3.8-flash-high", "gemini-3.8-flash-medium")
DEFAULTS = {"strong": RUNTIME, "cheap": RUNTIME}
NOTE = ("Runs through the Antigravity CLI (agy) on this machine, signed in to your Google "
        "account. No API key; calls count against your Antigravity usage limits.")

# Where the CLI lives when it is not on PATH. Each pattern may match several
# versions; the newest wins.
BUNDLED = (
    "~/.antigravity/bin/agy.exe",
    "~/.antigravity/bin/agy",
    "~/.gemini/antigravity-cli/bin/agy.exe",
    "~/.gemini/antigravity-cli/bin/agy",
    "~/AppData/Local/Programs/Antigravity*/**/agy.exe",
    "~/AppData/Local/agy/**/agy.exe",
    "~/.local/bin/agy",
    "/usr/local/bin/agy",
    "/opt/homebrew/bin/agy",
)

# Seconds before a call is abandoned. Web research takes longer than a rewrite.
TIMEOUT = {"web": 900, "text": 600}

# Past this many characters the prompt goes to a file instead of the command
# line, which on Windows is limited to about 32k characters.
INLINE_LIMIT = 20000

FILE_HANDOFF = (
    "Your instructions are in the file prompt.md in the current working "
    "directory. Read that file first and follow it exactly. Your final answer "
    "must be only the JSON object the instructions ask for."
)


def _version(path: str) -> tuple:
    found = re.findall(r"\d+(?:\.\d+)+", path)
    return tuple(int(part) for part in found[-1].split(".")) if found else ()


def find_cli() -> Path | None:
    """The CLI binary to run, or None when Antigravity's CLI is not installed."""
    override = os.environ.get("ANTIGRAVITY_CLI")
    if override and os.path.exists(override):
        return Path(override)
    on_path = shutil.which("agy")
    if on_path:
        return Path(on_path)
    for pattern in BUNDLED:
        matches = [m for m in glob.glob(os.path.expanduser(pattern), recursive=True) if os.path.isfile(m)]
        if matches:
            return Path(max(matches, key=_version))
    return None


def available() -> bool:
    return find_cli() is not None


def launcher(cli: Path) -> list[str]:
    """A shell-free launcher for a native binary or a Windows command shim."""
    if os.name == "nt" and cli.suffix.casefold() in {".cmd", ".bat"}:
        return [os.environ.get("ComSpec", "cmd.exe"), "/d", "/s", "/c", str(cli)]
    return [str(cli)]


def command(cli: Path, prompt: str, schema_path: str, *, model: str, timeout: int) -> list:
    """The exact argument list, kept separate so tests can check it."""
    cmd = launcher(cli) + [
        "-p", prompt,
        "--output-format", "json",
        "--json-schema", schema_path,
        "--sandbox",
        # The CLI's own limit sits just under ours, so it reports a timeout itself.
        "--print-timeout", f"{max(1, timeout // 60 - 1)}m",
    ]
    if model != RUNTIME:
        cmd += ["--model", model]
    return cmd


def payload(prompt: str, system: str | None) -> str:
    """System text first, then the task. The schema goes through --json-schema."""
    return (system.strip() + "\n\n---\n\n" + prompt) if system else prompt


def describe_failure(data: dict, stderr: str, returncode: int) -> str:
    """Why a failed call failed, in words the user can act on."""
    error = data.get("error")
    if isinstance(error, dict):
        error = error.get("message") or json.dumps(error)
    text = " ".join(f"{error or ''} {data.get('response') or ''} {stderr or ''}".split())
    folded = text.casefold()
    if re.search(r"authentication required|not (logged|signed) in|unauthori[sz]ed|\b401\b|sign[ -]?in|log ?in"
                 r"|credentials? (expired|missing|not found)", folded):
        return ("Antigravity is not signed in on this machine. Open a terminal, run `agy` once and sign in "
                "with your Google account, then retry.")
    if re.search(r"usage limit|quota|rate limit|resource[_ ]exhausted|\b429\b|out of (extra )?usage", folded):
        # Keep the CLI's own reset time, so the Auto router rests this plan until then.
        return limits.with_hint("Your Antigravity usage limit is reached. Wait for it to reset, then retry.", text)
    if re.search(r"unknown model|invalid model|model .{0,40}not (found|available|supported)", folded):
        return "Antigravity does not offer that model on this account. Choose 'antigravity-runtime' in Settings."
    status = data.get("status") or "no result"
    detail = text[:200]
    return (f"Antigravity could not finish ({status}, exit {returncode})"
            + (f": {detail}" if detail else "")
            + ". Retry; if it repeats, run `agy` in a terminal and check sign-in and usage.")


def _envelope(stdout: str) -> dict:
    """The JSON envelope print mode writes; tolerant of a banner line before it."""
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def _result(data: dict) -> dict:
    """The structured object: ``structured_output``, else the ``response`` text parsed."""
    result = data.get("structured_output")
    if isinstance(result, dict):
        return result
    response = data.get("response")
    if isinstance(response, dict):
        return response
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(response or "").strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        try:
            parsed = json.loads(cleaned[start:end + 1]) if start != -1 and end > start else None
        except json.JSONDecodeError:
            parsed = None
    if not isinstance(parsed, dict):
        raise ValueError("Antigravity returned output that did not match the requested schema")
    return parsed


def run(prompt: str, schema: dict, *, model: str = RUNTIME, web: bool = False,
        system: str | None = None, timeout: int | None = None) -> tuple[dict, dict]:
    """One structured call. Returns (parsed object, token usage) or raises ValueError."""
    cli = find_cli()
    if cli is None:
        raise ValueError(
            "Google Antigravity's CLI (agy) is not installed on this machine. Install Antigravity "
            "from https://antigravity.google, run `agy install` and sign in, then retry."
        )
    if model not in MODELS:
        raise ValueError("Unsupported Antigravity model")
    full = payload(prompt, system)
    limit = timeout or TIMEOUT["web" if web else "text"]
    # An empty working directory: nothing for the file tools to read but the
    # schema and, when needed, the handoff prompt.
    with tempfile.TemporaryDirectory(prefix="career-agy-") as folder:
        schema_path = Path(folder, "schema.json")
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        argv_prompt = full
        if len(full) > INLINE_LIMIT:
            Path(folder, "prompt.md").write_text(full, encoding="utf-8")
            argv_prompt = FILE_HANDOFF
        out_file = Path(folder, "result.json")
        try:
            with out_file.open("w", encoding="utf-8") as stream:
                done = subprocess.run(
                    command(cli, argv_prompt, str(schema_path), model=model, timeout=limit),
                    text=True, encoding="utf-8", errors="replace",
                    stdout=stream, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                    timeout=limit, cwd=folder,
                )
        except subprocess.TimeoutExpired:
            raise ValueError(
                "Antigravity reached its time limit. Nothing was saved from this call. Retry a smaller pass."
            ) from None
        except OSError as error:
            raise ValueError(f"Antigravity could not be started: {error}") from None
        stdout_text = out_file.read_text(encoding="utf-8", errors="replace")
    data = _envelope(stdout_text)
    if done.returncode or str(data.get("status") or "").upper() != "SUCCESS":
        if not data and not done.returncode:
            said = " ".join((done.stderr or stdout_text or "").split())[:200]
            raise ValueError("Antigravity did not return a result" + (f" ({said})" if said else "")
                             + ". Run `agy` in a terminal, check it is signed in, and retry.")
        raise ValueError(describe_failure(data, done.stderr, done.returncode))
    used = data.get("usage") or {}
    return _result(data), {"input_tokens": used.get("input_tokens"), "output_tokens": used.get("output_tokens")}


def invoke(prompt: str, schema: dict, **options) -> dict:
    """The provider-gateway shape: just the parsed object."""
    from backend import telemetry

    result, usage = run(prompt, schema, **options)
    telemetry.record_usage((usage or {}).get("input_tokens"), (usage or {}).get("output_tokens"))
    return result
