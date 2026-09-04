#!/usr/bin/env python3
"""
Build a resume PDF from LaTeX, and refuse to ship a bad one.

Replaces build_pdf.sh, which was bash-only (set -euo pipefail, /tmp paths) and
so did not run on Windows.

Guards, in order:
  1. leftover {{PLACEHOLDER}} tokens        -> hard fail
  2. leftover [FILL IN ...] markers         -> hard fail
  3. unbalanced braces / \\begin..\\end      -> warn
  4. compile with Tectonic                  -> hard fail on LaTeX error
  5. PAGE COUNT != 1                        -> hard fail, with what to cut

Usage
-----
  python system/scripts/build_pdf.py output/Annie_Manoharan_Acme_01/resume.tex
  python system/scripts/build_pdf.py output/*/resume.tex
  python system/scripts/build_pdf.py --pages 2 path/to/resume.tex
  python system/scripts/build_pdf.py --check-only path/to/resume.tex

Standard library only.
"""

from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
import zlib
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
TECTONIC = ROOT / "system" / "bin" / "tectonic.exe"
if not TECTONIC.exists():
    alt = ROOT / "system" / "bin" / "tectonic"
    TECTONIC = alt if alt.exists() else TECTONIC


def find_engine() -> list[str] | None:
    if TECTONIC.exists():
        return [str(TECTONIC)]
    import shutil
    for name in ("tectonic", "latexmk", "pdflatex", "xelatex"):
        p = shutil.which(name)
        if p:
            if name == "latexmk":
                return [p, "-pdf", "-interaction=nonstopmode"]
            if name in ("pdflatex", "xelatex"):
                return [p, "-interaction=nonstopmode"]
            return [p]
    return None


# --------------------------------------------------------------------------
# PDF page counting
#
# Tectonic writes compressed cross-reference and object streams, so /Type/Page
# is usually not visible in the raw bytes. Inflate every stream we can, then
# count across raw + inflated text.
# --------------------------------------------------------------------------
def count_pages(pdf: Path) -> int:
    data = pdf.read_bytes()
    blobs = [data]

    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        chunk = data[start:end]
        for wbits in (15, -15, 47):
            try:
                blobs.append(zlib.decompress(chunk, wbits))
                break
            except zlib.error:
                continue

    joined = b"\n".join(blobs)

    # Prefer the page tree's /Count — it is authoritative.
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages\b[^>]{0,200}?/Count\s+(\d+)", joined)]
    counts += [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]{0,200}?/Type\s*/Pages\b", joined)]
    if counts:
        return max(counts)

    # Fall back to counting page objects (/Type /Page not followed by 's').
    n = len(re.findall(rb"/Type\s*/Page(?![s/\w])", joined))
    return n if n else -1


# --------------------------------------------------------------------------
def check_source(tex: Path) -> list[str]:
    """Return a list of blocking problems."""
    problems: list[str] = []
    text = tex.read_text(encoding="utf-8", errors="replace")

    tokens = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", text)))
    if tokens:
        problems.append(
            "unfilled placeholders still in the file: " + ", ".join(tokens[:12])
            + (f" (+{len(tokens)-12} more)" if len(tokens) > 12 else "")
        )

    fills = re.findall(r"\[FILL IN[^\]]*\]", text)
    if fills:
        problems.append(f"{len(fills)} [FILL IN ...] marker(s) left: {fills[0]}")

    body = re.sub(r"(?<!\\)%.*", "", text)
    if body.count("{") != body.count("}"):
        problems.append(
            f"unbalanced braces: {body.count('{')} open vs {body.count('}')} close"
        )

    begins = re.findall(r"\\begin\{(\w+\*?)\}", body)
    ends = re.findall(r"\\end\{(\w+\*?)\}", body)
    for env in set(begins) | set(ends):
        if begins.count(env) != ends.count(env):
            problems.append(
                f"\\begin{{{env}}} x{begins.count(env)} vs \\end{{{env}}} x{ends.count(env)}"
            )

    # Count on `body`, not `text` — the template's own comment mentions
    # \usepackage{hyperref} while warning about the option clash.
    hyperref = body.count("\\usepackage{hyperref}") + \
        len(re.findall(r"\\usepackage\[[^\]]*\]\{hyperref\}", body))
    if hyperref > 1:
        problems.append("hyperref loaded more than once — this is an option-clash error")

    return problems


TOO_LONG_ADVICE = """
  How to get back to one page, in the order that costs you least:
    1. Drop the LAST bullet of the OLDEST role (it is doing the least work).
    2. Drop the second project's second bullet.
    3. Merge two skill categories into one line.
    4. Drop the coursework line, unless the JD names those modules.
    5. Drop the second degree entirely for software/data roles.
  Do NOT shrink margins, reduce the font below 10pt, or delete the whitespace
  between sections — recruiters read a cramped resume as a red flag, and ATS
  parsers do worse on them.
"""


def build_one(tex: Path, want_pages: int, check_only: bool) -> bool:
    print(f"\n=== {tex}")

    if not tex.exists():
        print("  FAIL  file not found")
        return False

    problems = check_source(tex)
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        return False
    print("  ok    source checks passed")

    if check_only:
        return True

    engine = find_engine()
    if not engine:
        print("  FAIL  no LaTeX engine found.")
        print("        Expected system/bin/tectonic.exe — run the installer step,")
        print("        or paste the .tex into Overleaf and compile there.")
        return False

    proc = subprocess.run(
        engine + [tex.name],
        cwd=str(tex.parent),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        print("  FAIL  LaTeX error:")
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        for line in tail[-18:]:
            print(f"        {line}")
        return False

    pdf = tex.with_suffix(".pdf")
    if not pdf.exists():
        print("  FAIL  compiler returned 0 but produced no PDF")
        return False

    pages = count_pages(pdf)
    size_kb = pdf.stat().st_size / 1024

    if pages == -1:
        print(f"  WARN  built {pdf.name} ({size_kb:.0f} KB) — page count unreadable, check by eye")
        return True
    if pages != want_pages:
        print(f"  FAIL  {pdf.name} is {pages} pages, must be {want_pages}")
        if pages > want_pages:
            print(TOO_LONG_ADVICE)
        return False

    print(f"  ok    built {pdf.name}  ({pages} page, {size_kb:.0f} KB)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Build resume PDFs and enforce the page limit.")
    ap.add_argument("files", nargs="+", help=".tex files (globs allowed)")
    ap.add_argument("--pages", type=int, default=1, help="required page count (default 1)")
    ap.add_argument("--check-only", action="store_true", help="run the guards, do not compile")
    args = ap.parse_args()

    targets: list[Path] = []
    for pattern in args.files:
        hits = [Path(p) for p in glob.glob(pattern)] or [Path(pattern)]
        targets.extend(hits)

    ok = sum(build_one(t, args.pages, args.check_only) for t in targets)
    total = len(targets)

    print(f"\n{'=' * 46}")
    print(f"{ok}/{total} built cleanly")
    if ok < total:
        print(f"{total - ok} need attention — see above.")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
