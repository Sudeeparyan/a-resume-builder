# The dashboard

A local web app with two tabs — **Job Finder** and **Resume Builder** — sitting on
top of the workspace you already have.

It does not replace anything. `context/` is still where your facts live, `output/`
is still where applications land, and `system/data/applications.tsv` is still the
record of what you applied to. The dashboard reads and writes those same files, so
Claude Code and the dashboard always agree.

## Starting it

```
python dashboard/run.py
```

That builds the page the first time (about a minute), starts the server, and opens
your browser at http://127.0.0.1:8000.

To stop it, close the terminal window.

## It works with no API key

Nothing here requires setup. Without a key you still get:

- Jobs pulled from company boards and remote feeds
- The **sponsorship check**, with tiers and the exact sentence behind every exclusion
- **Never re-applying** — anywhere you already applied is filtered out
- Apply links checked for being live
- Scoring and ranking
- A resume built from your real experience, compiled to a one-page PDF
- Every honesty check, including the fabrication guard
- `output/SUMMARY.md` kept up to date

Adding an Anthropic key in **Settings** turns on the parts that need judgement:
company research with web search, reading a job ad properly rather than by keyword,
the interview-probability estimate, tailored rewriting, the recruiter audit and the
study plan.

## Tab 1 — Job Finder

Press **Find jobs**. You will see each step as it runs, with an estimate of how much
longer it will take. The estimate comes from how long these steps have actually
taken before, so it gets more accurate as you use it.

Jobs are ordered by **sponsorship tier first, then score**:

| Tier | Meaning |
|---|---|
| **S** | Cap-exempt — can file any time of year, no lottery |
| **A** | The posting says it will sponsor |
| **B** | Has sponsored before; this posting is silent |
| **C** | Silent, no record — the normal case, and where most offers come from |

A tier-C job scoring 85 still ranks below a tier-S job scoring 75, because a
cap-exempt employer can actually hire you without the lottery.

**Ruled out** shows everything dropped, with the sentence that caused it, so you can
overrule a wrong call.

## Tab 2 — Resume Builder

Press **Build a resume** on any job. It picks the track, the framing of each role,
and one signature project — then grows the page until it is full without spilling
onto a second one.

The editor is side by side: LaTeX on the left, the live PDF on the right. It
rebuilds about a second after you stop typing. Errors appear in the margin next to
the line that caused them.

**Check & finish** runs the strict checks. Only then does Download turn on — that
is deliberate, and it is what stops a resume with an invented number going out.

## The rule that matters

A number or a tool that is not in your `context/` files cannot appear on a resume.
Not hedged, not as "familiar with", not at all. The checks are mechanical, so they
cannot be talked around:

- Every number in a bullet must already exist in your files
- Anything on your honest-gaps list is blocked, even though the word appears in
  `05-skills.md` inside the do-not-claim list
- No years-of-experience total while question 1 is open
- No publication claim while question 3 is open
- Anything in a study plan is a skill you do not have yet, so it stays off the page

## Layout

```
dashboard/
  run.py                  start here
  backend/
    paths.py              the only file that knows where the workspace is
    legacy.py             bridge to system/scripts/*.py, with three defects patched
    agents/               composer, builder, deterministic gates, prompts
    services/             fact base, guards, LaTeX render, Tectonic, sources, sync
    orchestrator/         the pipeline, live events, ETA
    api/routes.py         the HTTP surface
  frontend/               React + CodeMirror + pdf.js
  tests/                  pytest suite and runnable probes
```

The agent prompts are assembled at run time from `system/modes/*.md` and
`.claude/skills/resume-tailor/references/*.md`. Editing your playbook changes what
the dashboard does — there is only one copy of every rule.

## Checking it still works

```
python -m pytest dashboard/tests -q          # the fast suite
python dashboard/tests/probe_scan.py         # a real end-to-end scan
python dashboard/tests/probe_build.py        # build three resumes
python dashboard/tests/probe_honesty.py      # prove fabrications are blocked
```

`probe_honesty.py` needs the server running. It plants four lies in a real resume
and fails if any of them would have shipped.
