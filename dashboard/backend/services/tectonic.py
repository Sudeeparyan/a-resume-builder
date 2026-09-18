"""
The LaTeX compile service.

Two modes, and the distinction is the whole answer to "how does a strict
one-page gate coexist with a live preview":

  draft  -- compile anything. {{TOKENS}} and [FILL IN: ...] become warnings, a
            two-page result is reported rather than refused. This is what the
            editor auto-compiles on every pause in typing.
  ship   -- the real gate. build_pdf.check_source() problems are errors and
            pages != 1 is an error. Only a passing ship compile enables Download.

Tectonic writes .aux/.log/.pdf next to the source, so two compiles in one
directory corrupt each other: every compile gets its own scratch directory and
a semaphore caps concurrency. Scratch never touches output/, so a broken edit
cannot leave a bad PDF where SUMMARY.md points at it.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from typing import Any

from .. import legacy, paths, settings

_sem: asyncio.Semaphore | None = None
_inflight: dict[str, asyncio.Task] = {}

# LaTeX errors worth surfacing, in the order we prefer to report them.
_ERR_PATTERNS = [
    (re.compile(r"^!\s*(.+)$"), "latex"),
    (re.compile(r"^error:\s*(.+)$", re.I), "engine"),
    (re.compile(r"^\s*l\.(\d+)\s*(.*)$"), "line"),
]
_OVERFULL_RE = re.compile(r"Overfull \\[hv]box .*? at lines? (\d+)")


def _semaphore() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(settings.get_settings().max_parallel_tectonic)
    return _sem


def sha_of(tex: str) -> str:
    return hashlib.sha256(tex.encode("utf-8")).hexdigest()[:16]


@dataclass
class CompileOut:
    ok: bool = False
    mode: str = "draft"
    sha: str = ""
    pages: int = 0
    text_chars: int = 0
    underfilled: bool = False
    pdf_path: str | None = None
    pdf_b64: str | None = None
    log_tail: str = ""
    problems: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    cache_hit: bool = False
    engine: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d.pop("pdf_path", None)
        return d


def parse_log(log: str) -> list[dict[str, Any]]:
    """Turn a Tectonic/LaTeX log into line-anchored diagnostics."""
    problems: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None

    for raw in log.splitlines():
        line = raw.rstrip()
        m = re.match(r"^!\s*(.+)$", line)
        if m:
            pending = {
                "severity": "error", "kind": "LATEX",
                "message": m.group(1).strip(), "line": None, "raw": line,
            }
            problems.append(pending)
            continue
        m = re.match(r"^\s*l\.(\d+)\s*(.*)$", line)
        if m and pending is not None and pending.get("line") is None:
            pending["line"] = int(m.group(1))
            if m.group(2).strip():
                pending["raw"] = f"{pending['raw']}  ->  {m.group(2).strip()}"
            pending = None
            continue
        m = re.match(r"^error:\s*(.+)$", line, re.I)
        if m:
            problems.append({
                "severity": "error", "kind": "ENGINE",
                "message": m.group(1).strip(), "line": None, "raw": line,
            })
            continue
        m = _OVERFULL_RE.search(line)
        if m:
            problems.append({
                "severity": "warning", "kind": "OVERFULL",
                "message": "This line runs past the margin — it often causes a page overflow.",
                "line": int(m.group(1)), "raw": line.strip(),
            })
    return problems


def _locate_markers(tex: str) -> list[dict[str, Any]]:
    """
    Give {{TOKEN}} and [FILL IN: ...] real line numbers.

    build_pdf.check_source() reports them as prose with no location, which is
    useless in an editor.
    """
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(tex.splitlines(), start=1):
        if raw.lstrip().startswith("%"):
            continue          # a marker in a comment is documentation, not a gap
        for m in re.finditer(r"\{\{[A-Z0-9_]+\}\}", raw):
            out.append({
                "severity": "error", "kind": "PLACEHOLDER", "line": i,
                "message": f"{m.group(0)} was never filled in.", "raw": raw.strip()[:160],
            })
        for m in re.finditer(r"\[FILL IN[^\]]*\]", raw):
            out.append({
                "severity": "error", "kind": "FILL_IN", "line": i,
                "message": f"{m.group(0)} still needs a real number from you.",
                "raw": raw.strip()[:160],
            })
    return out


async def compile_tex(
    tex: str,
    *,
    mode: str = "draft",
    resume_id: str = "scratch",
    want_pages: int = 1,
    allow_fewer: bool = False,
    timeout_s: int = 60,
    return_pdf: bool = True,
) -> CompileOut:
    """Compile `tex` and report structured results. Never raises on LaTeX errors."""
    started = time.perf_counter()
    sha = sha_of(tex)
    out = CompileOut(mode=mode, sha=sha)

    engine = legacy.build_pdf.find_engine()
    if not engine:
        out.problems = [{
            "severity": "error", "kind": "ENGINE", "line": None,
            "message": (
                "The LaTeX engine is missing. It should be at "
                "system/bin/tectonic.exe — that file is not committed to git, so "
                "it needs downloading once."
            ),
            "raw": "",
        }]
        out.duration_ms = int((time.perf_counter() - started) * 1000)
        return out
    out.engine = os.path.basename(engine[0])

    # Source problems, located. In draft mode these are informative only.
    marker_problems = _locate_markers(tex)
    if mode == "ship":
        out.problems.extend(marker_problems)
    else:
        out.problems.extend({**p, "severity": "warning"} for p in marker_problems)

    scratch = paths.TMP / "compile" / resume_id / sha
    cached_pdf = scratch / "resume.pdf"
    if cached_pdf.exists() and cached_pdf.stat().st_size > 0:
        out.cache_hit = True
    else:
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True, exist_ok=True)
        src = scratch / "resume.tex"
        src.write_text(tex, encoding="utf-8", newline="\n")

        # Deliberately NOT overriding TECTONIC_CACHE_DIR. Pointing it at a fresh
        # directory makes Tectonic re-download its entire package bundle, turning
        # a 1.7 second compile into a multi-minute one. The user-level cache is
        # already warm; leave it alone.
        env = os.environ.copy()

        async with _semaphore():
            try:
                proc = await asyncio.create_subprocess_exec(
                    *engine, str(src),
                    cwd=str(scratch),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env,
                )
            except OSError as exc:
                out.problems.append({
                    "severity": "error", "kind": "ENGINE", "line": None,
                    "message": f"Could not start the LaTeX engine: {exc}", "raw": "",
                })
                out.duration_ms = int((time.perf_counter() - started) * 1000)
                return out

            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                out.problems.append({
                    "severity": "error", "kind": "TIMEOUT", "line": None,
                    "message": f"The build took longer than {timeout_s} seconds and was stopped.",
                    "raw": "",
                })
                out.duration_ms = int((time.perf_counter() - started) * 1000)
                return out

        log = stdout.decode("utf-8", errors="replace")
        out.log_tail = "\n".join(log.splitlines()[-60:])
        out.problems.extend(parse_log(log))

    pdf = scratch / "resume.pdf"
    if not pdf.exists() or pdf.stat().st_size == 0:
        if not any(p["severity"] == "error" for p in out.problems):
            out.problems.append({
                "severity": "error", "kind": "LATEX", "line": None,
                "message": "The build produced no PDF. The log below says why.", "raw": "",
            })
        out.duration_ms = int((time.perf_counter() - started) * 1000)
        return out

    out.pdf_path = str(pdf)
    out.pages = legacy.count_pdf_pages(pdf)
    out.text_chars = legacy.pdf_text_chars(pdf)
    out.underfilled = out.text_chars < legacy.MIN_FILL_CHARS * max(1, want_pages)

    over = out.pages > want_pages
    under = out.pages < want_pages
    if over or (under and not allow_fewer):
        sev = "error" if mode == "ship" else "warning"
        out.problems.append({
            "severity": sev, "kind": "PAGES", "line": None,
            "message": (
                f"This is {out.pages} page{'s' if out.pages != 1 else ''}, and this resume "
                f"is set to be exactly {want_pages}. "
                + ("Cut content — never shrink the margins or the font."
                   if over else
                   "Add real content from your context files — never stretch what is there.")
            ),
            "raw": "",
        })
    elif out.underfilled:
        out.problems.append({
            "severity": "warning", "kind": "UNDERFILL", "line": None,
            "message": (
                f"The page is only about {out.text_chars} characters of text. A thin one-pager "
                "reads as thin experience — add real content rather than leaving white space."
            ),
            "raw": "",
        })

    if return_pdf:
        out.pdf_b64 = base64.b64encode(pdf.read_bytes()).decode("ascii")

    out.ok = not any(p["severity"] == "error" for p in out.problems)
    out.duration_ms = int((time.perf_counter() - started) * 1000)
    return out


async def compile_debounced(tex: str, resume_id: str, **kw) -> CompileOut:
    """Cancel any in-flight compile for the same document before starting a new one."""
    prev = _inflight.get(resume_id)
    if prev and not prev.done():
        prev.cancel()
    task = asyncio.create_task(compile_tex(tex, resume_id=resume_id, **kw))
    _inflight[resume_id] = task
    try:
        return await task
    except asyncio.CancelledError:
        raise
    finally:
        if _inflight.get(resume_id) is task:
            _inflight.pop(resume_id, None)


def engine_status() -> dict[str, Any]:
    engine = legacy.build_pdf.find_engine()
    t = paths.tectonic()
    return {
        "available": bool(engine),
        "engine": os.path.basename(engine[0]) if engine else None,
        "path": str(t) if t else None,
        "note": "" if engine else (
            "system/bin/tectonic.exe is missing. It is deliberately not committed to "
            "git because it is 51 MB, so it has to be downloaded once."
        ),
    }
