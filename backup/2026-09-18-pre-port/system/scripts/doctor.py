#!/usr/bin/env python3
"""
doctor.py — one command to check your workspace is healthy before you rely on it.

    python3 system/scripts/doctor.py

It checks the things that actually break a resume run, in plain language:
  1. Have you filled in your context/ folder? (where every fact on a resume comes from)
  2. Is your identity filled in? (the few tokens a resume can't be made without)
  3. Do the config files parse?
  4. Do the LaTeX templates lint clean? (balanced braces, one hyperref)
  5. Did any resume you generated go out with {{PLACEHOLDERS}} or [FILL IN] markers still in it?
  6. How many "did you forget to add it?" items are waiting in context/QUESTIONS-FOR-YOU.md?

Stdlib only — no install needed. Exit 0 = healthy, 1 = something wants your attention.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

# scripts live at <workspace>/system/scripts/, so the workspace root is three levels up
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import init_profile  # reuse the token scanner + the BLOCKING set  # noqa: E402

# Windows terminals default to cp1252 and choke on ✓/✗. Prefer UTF-8; fall back to ASCII.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass
_UNI = (getattr(sys.stdout, "encoding", "") or "").lower().replace("-", "").startswith("utf")
CHECK = "✓" if _UNI else "OK"
CROSS = "✗" if _UNI else "X"
DOT = "•" if _UNI else "-"

TOKEN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
FILLIN = re.compile(r"\[FILL IN[^\]]*\]", re.IGNORECASE)

problems: list[str] = []   # must fix — blocks a good resume
nudges: list[str] = []     # worth doing, not blocking


def ok(msg: str) -> None:
    print(f"  {CHECK} {msg}")


def bad(msg: str) -> None:
    problems.append(msg)
    print(f"  {CROSS} {msg}")


def nudge(msg: str) -> None:
    nudges.append(msg)
    print(f"  {DOT} {msg}")


# ---- 0. the context folder ----------------------------------------------------
CONTEXT_FILES = [
    ("01-basics.md", "your name, contact and right to work", True),
    ("02-education.md", "degrees and - importantly - every module you took", False),
    ("03-experience.md", "jobs, internships, placements", False),
    ("04-projects.md", "everything you have built; each resume leads with a different one", True),
    ("05-skills.md", "tools and software, at three honesty levels", True),
    ("06-achievements.md", "certificates, awards, publications, languages", False),
    ("07-preferences.md", "what jobs you want and where - this steers the job search", True),
    ("08-voice.md", "how you want to sound", False),
    ("09-anything-else.md", "anything that did not fit elsewhere", False),
]


def _looks_empty(text: str) -> bool:
    """Empty = still marked Status: EMPTY, or carrying no prose of the user's own."""
    if "Status: EMPTY" in text:
        return True
    body = []
    for line in text.splitlines():
        st = line.strip()
        if not st or st.startswith(("#", ">", "|", "<!--", "-->", "---")):
            continue
        if st in ("-", "*") or (st.startswith(("- ", "* ")) and len(st) <= 3):
            continue
        body.append(st)
    return len(" ".join(body).strip()) < 40


def check_context() -> None:
    print("Your context folder")
    base = ROOT / "context"
    if not base.exists():
        bad("context/ is missing - that is where everything about you lives")
        return
    filled, empty_required, empty_optional = [], [], []
    for name, what, required in CONTEXT_FILES:
        f = base / name
        if not f.exists() or _looks_empty(f.read_text(encoding="utf-8", errors="replace")):
            (empty_required if required else empty_optional).append((name, what))
        else:
            filled.append(name)
    fdir = base / "files"
    docs = [d for d in fdir.glob("*") if d.is_file() and d.name != "README.md"] if fdir.exists() else []

    if filled:
        ok(f"{len(filled)} of {len(CONTEXT_FILES)} filled in: " + ", ".join(filled))
    if docs:
        ok(f"{len(docs)} document(s) in context/files/ to read: "
           + ", ".join(d.name for d in docs[:4]) + (" ..." if len(docs) > 4 else ""))
    for name, what in empty_required:
        bad(f"context/{name} is empty - {what}")
    for name, what in empty_optional:
        nudge(f"context/{name} is empty - {what}")
    if not filled:
        print('      -> ask the assistant: "help me fill in my context" and just answer its questions')


# ---- 1. identity filled -------------------------------------------------------
def check_identity() -> None:
    print("Identity")
    # Only the live profile/config layer must be token-free. system/templates/**
    # is SUPPOSED to keep its {{TOKENS}} — that is what makes it a template —
    # and so is system/PLACEHOLDERS.md, which documents them.
    tokens, _ = init_profile.scan(dirs=["system/profile", "system/config", "system/data"])
    blocking = sorted(t for t in tokens if t in init_profile.BLOCKING)
    if not blocking:
        ok("the essentials are filled — you can generate a resume")
    else:
        bad(f"{len(blocking)} essential field(s) still blank: "
            + ", ".join("{{" + t + "}}" for t in blocking))
        print("      → ask the assistant to run profile-intake — it reads context/ and fills these")


# ---- 2. configs parse ---------------------------------------------------------
def check_configs() -> None:
    print("Config files")
    cfgs = ["system/config/regions.yml", "system/config/portals.yml", "system/config/profile.yml"]
    try:
        import yaml  # type: ignore
    except ImportError:
        for f in cfgs:
            p = ROOT / f
            if not p.exists():
                bad(f"{f} is missing")
            elif "\t" in p.read_text(encoding="utf-8"):
                bad(f"{f} contains a TAB — YAML needs spaces, not tabs")
        ok("present (install pyyaml for a full parse check)")
        return
    for f in cfgs:
        p = ROOT / f
        if not p.exists():
            bad(f"{f} is missing")
            continue
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
            ok(f"{f} parses")
        except Exception as e:  # noqa: BLE001
            bad(f"{f} does not parse: {str(e).splitlines()[0]}")


# ---- 3. LaTeX templates lint --------------------------------------------------
def _strip_tex_comments(s: str) -> str:
    out = []
    for line in s.splitlines():
        res, esc = [], False
        for ch in line:
            if ch == "%" and not esc:
                break
            res.append(ch)
            esc = (ch == "\\") and not esc
        out.append("".join(res))
    return "\n".join(out)


def _tex_problems(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    s = _strip_tex_comments(raw)
    probs, depth, esc = [], 0, False
    for ch in s:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                probs.append("a }} with no matching {{")
                depth = 0
    if depth:
        probs.append(f"{depth} unclosed {{")
    b = Counter(re.findall(r"\\begin\{([^}]+)\}", s))
    e = Counter(re.findall(r"\\end\{([^}]+)\}", s))
    for env in set(b) | set(e):
        if b[env] != e[env]:
            probs.append(f"\\begin/\\end mismatch on '{env}'")
    if len(re.findall(r"\\usepackage(\[[^\]]*\])?\{hyperref\}", s)) > 1:
        probs.append("hyperref loaded twice (option clash on Overleaf)")
    return probs


def check_templates() -> None:
    print("LaTeX templates")
    bases = sorted((ROOT / "system" / "templates" / "latex").glob("*.tex"))
    if not bases:
        bad("no .tex templates found in system/templates/latex/")
        return
    for p in bases:
        probs = _tex_problems(p)
        rel = p.relative_to(ROOT)
        (ok if not probs else bad)(f"{rel}" + ("" if not probs else " — " + "; ".join(probs)))


# ---- 4. generated resumes are fully filled ------------------------------------
def check_generated() -> None:
    print("Generated resumes")
    out = ROOT / "output"
    resumes = sorted(out.glob("*/resume.tex")) if out.exists() else []
    if not resumes:
        ok("none yet — nothing to check")
        return
    dirty = [(p.relative_to(ROOT), sorted(set(TOKEN.findall(p.read_text(encoding="utf-8")))))
             for p in resumes]
    dirty = [(rel, toks) for rel, toks in dirty if toks]
    if not dirty:
        ok(f"all {len(resumes)} filled — no leftover placeholders")
    else:
        for rel, toks in dirty:
            bad(f"{rel} still has {len(toks)} placeholder(s): {', '.join(toks[:5])}"
                + (" …" if len(toks) > 5 else ""))

    # [FILL IN: …] markers are numbers only the candidate can supply. The recruiter audit leaves
    # them deliberately empty rather than guessing, so none may survive into a sent resume.
    unfilled = [(p.relative_to(ROOT), sorted(set(FILLIN.findall(p.read_text(encoding="utf-8")))))
                for p in resumes]
    unfilled = [(rel, marks) for rel, marks in unfilled if marks]
    if not unfilled:
        ok("no [FILL IN] markers awaiting real numbers")
    else:
        for rel, marks in unfilled:
            bad(f"{rel} needs {len(marks)} real number(s): {'; '.join(marks[:3])}"
                + (" …" if len(marks) > 3 else ""))
        bad("  → ask the user for these figures, save them into context/, then regenerate")


# ---- 5. the forgot-to-add ledger ----------------------------------------------
def check_ledger() -> None:
    print("Forgot-to-add ledger")
    p = ROOT / "context" / "QUESTIONS-FOR-YOU.md"
    if not p.exists():
        nudge("context/QUESTIONS-FOR-YOU.md not found (created on first ⚠️ flag)")
        return
    open_items = len(re.findall(r"^- \[ \]", p.read_text(encoding="utf-8"), re.M))
    if open_items == 0:
        ok("nothing waiting")
    else:
        nudge(f"{open_items} item(s) in context/QUESTIONS-FOR-YOU.md — facts a job wanted that "
              "aren't in your profile yet. Backfilling them lifts future matches.")


def main() -> int:
    print("\nWorkspace health check\n" + "=" * 24)
    for fn in (check_context, check_identity, check_configs, check_templates, check_generated,
               check_ledger):
        fn()
        print()
    print("=" * 24)
    if problems:
        print(f"{CROSS} {len(problems)} thing(s) to fix before you rely on this:")
        for m in problems:
            print(f"    - {m}")
    else:
        print(f"{CHECK} Healthy — you're ready to generate resumes.")
    if nudges:
        print(f"\n{len(nudges)} optional nudge(s):")
        for m in nudges:
            print(f"    - {m}")
    print()
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
