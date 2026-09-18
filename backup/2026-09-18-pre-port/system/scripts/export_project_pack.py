#!/usr/bin/env python3
"""
Export this workspace as a PROJECT PACK you can upload to any chat assistant.

The point: most people never touch an API. They pay for Claude or ChatGPT and
work in the app, on a phone or a laptop, inside a Project. So the whole system
has to survive as a folder of files plus one instruction block -- no server, no
Python, no key. This script produces exactly that.

    python system/scripts/export_project_pack.py

It writes output/project-pack/ and a zip beside it. Upload the files to a
Claude Project (Project knowledge) or a ChatGPT Project, paste INSTRUCTIONS.md
into the project's custom-instructions box, and then "give me 10 jobs" is a
complete request -- the instruction file supplies every default so she never has
to restate who she is or what the rules are.

Everything here is GENERATED from the live workspace. The rules are not retyped:
they are read from system/modes/*.md and the skill references, exactly as the
dashboard's prompt assembly does. Edit the playbook, re-run this, and the pack
and the app still agree. Stdlib only, so it runs anywhere Python does.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / "context"
MODES = ROOT / "system" / "modes"
SKILL_REFS = ROOT / ".claude" / "skills" / "resume-tailor" / "references"
CONFIG = ROOT / "system" / "config"
DATA = ROOT / "system" / "data"
TEMPLATES = ROOT / "system" / "templates" / "latex"
OUT = ROOT / "output" / "project-pack"


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def write(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body.rstrip() + "\n", encoding="utf-8", newline="\n")


def join(paths: list[Path], heading: bool = True) -> str:
    out: list[str] = []
    for p in paths:
        text = read(p).strip()
        if not text:
            continue
        if heading:
            out.append(f"<!-- from {p.relative_to(ROOT).as_posix()} -->")
        out.append(text)
    return "\n\n---\n\n".join(out)


# --------------------------------------------------------------------------
# facts pulled out of context/ so the instructions can be specific
# --------------------------------------------------------------------------
def candidate_name() -> str:
    text = read(CONTEXT / "01-basics.md")
    m = re.search(r"^\|\s*(?:full\s+)?name\s*\|\s*([^|]+)\|", text, re.I | re.M)
    if m:
        return m.group(1).strip().strip("*")
    m = re.search(r"full_name:\s*[\"']?([^\"'\n]+)", read(CONFIG / "profile.yml"), re.I)
    return (m.group(1).strip() if m else "the candidate")


def work_auth() -> str:
    """The Status row of the identity table in 01-basics.md."""
    for line in read(CONTEXT / "01-basics.md").splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) >= 2 and re.fullmatch(r"status|work\s*auth\w*", cells[0], re.I):
            return _plain(cells[1])
    return "F-1 OPT, active - authorised to work in the US now"


def _plain(s: str) -> str:
    """Drop markdown emphasis and backticks, keep the words."""
    return re.sub(r"\s+", " ", (s or "").replace("**", "").replace("`", "")).strip()


def wanted_titles() -> list[str]:
    """
    The roles she actually wants, from the Target roles table in
    07-preferences.md. That table is the search query, and it separates titles
    with a middle dot inside one cell per track -- so this reads the cell, not
    the bullet list the file does not have.
    """
    text = read(CONTEXT / "07-preferences.md")
    titles: list[str] = []
    grab = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            grab = bool(re.search(r"target\s+role|titles?\b", line, re.I))
            continue
        if not grab or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c]
        if len(cells) < 2 or set(cells[-1]) <= set("-: "):
            continue                                  # header rule row
        if re.fullmatch(r"track", _plain(cells[0]), re.I):
            continue                                  # header row
        for part in re.split(r"[·•;]|\s+/\s+", cells[-1]):
            t = _plain(part)
            if 2 < len(t) < 60 and not t.lower().startswith("titles"):
                titles.append(t)

    seen, out = set(), []
    for t in titles:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def blocking_questions() -> list[str]:
    """
    Only the questions the ledger itself files under "Blocking".

    The file separates "## Blocking - a resume claim depends on this" from
    "## Non-blocking - these sharpen the job search". Listing the non-blocking
    ones as claim-blockers would make the assistant refuse things it should
    simply answer.
    """
    out: list[str] = []
    blocking = False
    for raw in read(CONTEXT / "QUESTIONS-FOR-YOU.md").splitlines():
        line = raw.strip()
        m2 = re.match(r"^##\s+(.*)$", line)
        if m2 and not line.startswith("###"):
            blocking = bool(re.match(r"blocking\b", _plain(m2.group(1)), re.I))
            continue
        if blocking:
            m3 = re.match(r"^###\s*(Q\d+.*)$", line)
            if m3:
                out.append(_plain(m3.group(1)))
    return out


# --------------------------------------------------------------------------
# the instruction block -- the actual product
# --------------------------------------------------------------------------
def instructions(name: str) -> str:
    titles = wanted_titles()
    title_line = "; ".join(titles) if titles else "see 01-WHO-I-AM.md"
    qs = blocking_questions()
    q_block = "\n".join(f"- {q}" for q in qs) if qs else "- (none open)"

    return f"""# Career operations assistant for {name}

You run this person's US job search. Everything you need is in the files
attached to this project. Read them before answering anything.

| File | What it is |
|---|---|
| `01-WHO-I-AM.md` | Every verified fact about her. **The only source of resume content.** |
| `02-THE-RULES.md` | The sponsorship gate, the honesty wall, scoring, banned words |
| `03-FINDING-JOBS.md` | How to search, screen and rank openings |
| `04-BUILDING-A-RESUME.md` | Tailoring playbook, recruiter audit, ATS rules |
| `05-ALREADY-APPLIED.md` | Who must never be surfaced again |
| `06-RESUME-TEMPLATE.tex` | The LaTeX resume, ready to fill |

## Answer with almost no input

She should never have to restate who she is, what she wants, or what the rules
are. Assume all of it. If a request is ambiguous, pick the most useful reading
and say what you assumed in one line -- do not open with questions.

Defaults, applied unless she says otherwise:

- **Country:** United States only.
- **Roles:** {title_line}
- **Count:** 10 when she does not say a number.
- **Resume length:** exactly one page.
- **Work authorisation:** {work_auth()}.

## What to do when she says...

| She says | You do |
|---|---|
| "give me jobs", "find me roles", "what should I apply to" | The **job hunt** below. 10 roles, ranked, each with a working link. |
| pastes a job ad or a link | The **resume build** below, for that one job. |
| "build me a resume for X" | The resume build, researching X first. |
| "what does the hiring manager want" | The **hiring bar** below. |
| "I got rejected by X" / "I applied to X" | Update `05-ALREADY-APPLIED.md` and confirm in one line. |
| "I built X" / "I finished the X course" | Tell her exactly what to add to `01-WHO-I-AM.md`. Never claim it until it is in there. |
| "prep me for the X interview" | Map her real stories to the ad, predict questions, rehearse the honest answer to each gap. |

## The job hunt

1. Check `05-ALREADY-APPLIED.md` first. Same company + same role, ever = never
   show it. A company that rejected her = suppressed for 180 days.
2. Search for the roles above, in the US, posted in the last 30 days.
3. Run the **sponsorship gate** from `02-THE-RULES.md` on every posting. This is
   the step that matters most, and silence is a KEEP.
4. Verify the link opens. Never hand her a dead posting.
5. Rank: tier first (S, then A, B, C), score second.
6. Answer as a table: `#, Company, Role, Tier, Why it fits her, Location, Link`.
   Then, underneath, **Ruled out** -- with the exact sentence that disqualified
   each one, so a wrong exclusion is visible and she can correct it.
7. **Finish with a `careerops` block**, so she can paste the answer straight
   back into her dashboard and have every job tracked. Put it last, after the
   prose, fenced exactly like this:

````
```careerops
{{"version": 1, "jobs": [
  {{"company": "Example Inc",
   "role_title": "Data Engineer",
   "url": "https://example.com/jobs/123",
   "location": "Austin, TX",
   "jd_text": "the full text of the ad, if you have it",
   "note": "one line on why it fits her"}}
]}}
```
````

   Include every job you listed above. `company` and `role_title` are required;
   everything else is optional but `url` and `jd_text` are what make the entry
   useful. Do not put your tier or score in the block -- her dashboard recomputes
   both locally from the ad text and the sponsorship data, and a claimed tier
   would be discarded anyway.

## The resume build

Given one job ad:

1. Research the company: what they build, what they actually run in
   engineering, what they are heading toward, why this role is open.
2. Choose the track and the framing from `04-BUILDING-A-RESUME.md`.
3. Pick exactly **one signature project** for this employer -- first in
   Projects, one extra bullet, carrying the ad's top two must-haves truthfully.
4. Fill `06-RESUME-TEMPLATE.tex`. Every bullet copied from `01-WHO-I-AM.md`,
   word for word. Never rewrite a claim into something stronger.
5. Run the three-pass recruiter audit and report the score breakdown, never a
   bare total.
6. Then give her, separately, a **study plan**: what to learn before they call.
   Say out loud that nothing in it may appear on the resume until she has
   genuinely learned it and it is written into `01-WHO-I-AM.md`.

## The hiring bar

When she asks what a hiring manager wants, answer **as that manager**, and do
it **without reference to her profile**. The value of this answer is that it is
an outside view, not a flattering one. Give: what disqualifies a candidate on
sight; what makes them sit up; two to four concrete projects a stranger could
build that would earn a yes; the questions they would ask; and what makes them
close the tab. Only afterwards, if she asks, compare her against it.

## Rules you cannot bend

1. **The honesty wall.** If a fact is not in `01-WHO-I-AM.md`, it does not
   exist. Never invent a metric, a date, a tool, a team size or a publication.
   A skill she has not used cannot appear in any form -- not "familiar with",
   not "exposure to". A missing requirement is reported as a gap, never filled.
2. **Never re-apply.** Check `05-ALREADY-APPLIED.md` before surfacing anything.
3. **One page**, unless she asks for two. Never fix a spill by shrinking margins
   or fonts -- cut content.
4. **No fabricated links.** If you cannot verify a posting exists, say so.
5. **Never state a total years-of-experience figure** while the questions below
   are open.

### Open questions that block specific claims

{q_block}

Until she answers these, do not assert anything that depends on them. Ask her
once, in passing, when it is actually relevant -- never as a wall of questions.

## Voice

Plain US English. Short sentences. No filler: never "passionate about",
"results-oriented", "proven track record", "leveraged", "spearheaded",
"robust", "seamless", "cutting-edge", "responsible for", "worked on",
"helped with". Write like a competent person talking, not a brochure.
"""


def start_here(name: str) -> str:
    return f"""# Start here

This folder is {name}'s job search, packaged so it works inside any AI chat
app -- Claude, ChatGPT, or anything else with projects and file upload. No API
key, no server, no terminal. It runs on your normal subscription.

## Set it up once (about two minutes)

**Claude**
1. claude.ai, then **Projects**, then **Create project**.
2. Open **Project knowledge** and upload every `.md` and `.tex` file in this
   folder except `INSTRUCTIONS.md`.
3. Open **Set project instructions**, paste in all of `INSTRUCTIONS.md`, save.

**ChatGPT**
1. **Projects**, then **New project**.
2. Upload the same files.
3. Put `INSTRUCTIONS.md` into the project's instructions box.

**Anything else** -- upload the files, paste `INSTRUCTIONS.md` as the system
prompt or custom instruction.

## Then just talk to it

- "give me 10 jobs"
- "build me a resume for this" (paste the ad or the link)
- "what does the hiring manager actually want here?"
- "I got rejected by Databricks"
- "I finished the AWS course"

You never need to explain who you are. The pack already says.

## Keeping it current

Two files change over time: `01-WHO-I-AM.md` when you gain experience, and
`05-ALREADY-APPLIED.md` as you apply. Edit them in the project directly, or
re-run the exporter in the full workspace and re-upload:

    python system/scripts/export_project_pack.py

Generated {date.today().isoformat()} from the career-ops workspace.
"""


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
def build_pack(dest: Path, make_zip: bool = True) -> list[Path]:
    name = candidate_name()
    # Overwrite the files rather than removing the folder. On Windows a synced
    # folder (OneDrive, Dropbox) is frequently held open, and rmtree on the
    # directory itself fails with Access is denied even though every file in it
    # is writable.
    dest.mkdir(parents=True, exist_ok=True)
    for stale in dest.iterdir():
        if stale.is_file():
            try:
                stale.unlink()
            except OSError:
                pass

    written: list[Path] = []

    def emit(fname: str, body: str) -> None:
        p = dest / fname
        write(p, body)
        written.append(p)

    emit("START-HERE.md", start_here(name))
    emit("INSTRUCTIONS.md", instructions(name))

    # Her facts, flattened into one file. A project reads one document far more
    # reliably than nine, and the numbering here is the numbering the
    # instruction file refers to.
    emit("01-WHO-I-AM.md", "# Who I am - every verified fact\n\n"
         "This is the ONLY source of resume content. If something is not written\n"
         "here, it does not go on a resume, in any tense or any hedge.\n\n"
         + join([
             CONTEXT / "01-basics.md",
             CONTEXT / "02-education.md",
             CONTEXT / "03-experience.md",
             CONTEXT / "04-projects.md",
             CONTEXT / "05-skills.md",
             CONTEXT / "06-achievements.md",
             CONTEXT / "07-preferences.md",
             CONTEXT / "08-voice.md",
             CONTEXT / "09-anything-else.md",
             CONTEXT / "QUESTIONS-FOR-YOU.md",
         ]))

    emit("02-THE-RULES.md", "# The rules\n\n"
         "The sponsorship gate and the scoring weights, exactly as the full\n"
         "workspace applies them.\n\n"
         + join([MODES / "_shared.md", MODES / "_profile.md",
                 CONFIG / "sponsorship.yml"]))

    emit("03-FINDING-JOBS.md", "# Finding jobs\n\n"
         + join([MODES / "scan.md", MODES / "evaluate.md", MODES / "deep.md"]))

    emit("04-BUILDING-A-RESUME.md", "# Building a resume\n\n"
         + join([SKILL_REFS / "tailoring-playbook.md",
                 SKILL_REFS / "recruiter-audit.md",
                 SKILL_REFS / "ats-rules.md",
                 MODES / "upskill.md"]))

    applied = read(DATA / "applied-companies.md").strip()
    emit("05-ALREADY-APPLIED.md",
         "# Already applied - never surface these again\n\n"
         "Same company AND same role: never show it again, whatever the status.\n"
         "A company that rejected her: suppressed for 180 days.\n"
         "No reply for 21 days: it has gone quiet, and that company becomes\n"
         "eligible again after 90 days for a DIFFERENT role only.\n\n"
         "When she tells you an outcome, edit this file and confirm in one line.\n\n"
         + (applied or "_Nothing applied to yet._"))

    tpl = read(TEMPLATES / "resume-track-a.tex")
    if tpl:
        p = dest / "06-RESUME-TEMPLATE.tex"
        write(p, tpl)
        written.append(p)

    if make_zip:
        z = dest.parent / "project-pack.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(written):
                zf.write(p, arcname=p.name)
        written.append(z)

    return written


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Package this workspace for a Claude or ChatGPT project."
    )
    ap.add_argument("--out", default=str(OUT), help="where to write the pack")
    ap.add_argument("--no-zip", action="store_true")
    args = ap.parse_args()

    if not CONTEXT.exists():
        print(f"No context/ folder at {ROOT}. Run this from the workspace.", file=sys.stderr)
        return 2

    dest = Path(args.out)
    written = build_pack(dest, make_zip=not args.no_zip)

    print(f"Project pack written to {dest}")
    for p in written:
        kb = p.stat().st_size / 1024
        print(f"  {p.name:<28} {kb:7.1f} KB")
    print()
    print("Next: open START-HERE.md and follow the two-minute setup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
