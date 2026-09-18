# AGENTS.md — the entry point for any AI coding tool

This file is the cross-tool contract. Claude Code, Codex, Gemini CLI, Cursor,
Windsurf, OpenCode, Zed and anything else that reads `AGENTS.md` starts here.

**Nothing in this file restates a rule.** Every rule has exactly one home, and
this points at it. That is deliberate: the dashboard assembles its prompts from
the same files at runtime (`dashboard/backend/agents/prompts.py`), so editing a
playbook changes the app, the CLI and the chat pack together. A second copy of a
rule is a rule that will drift.

## What this workspace is

A career-operations workspace for **one person, targeting the United States**.
It removes three time sinks: finding roles genuinely open to her, re-tailoring a
resume for each, and remembering who already said no.

## Read these, in this order, before doing anything

| # | File | Why |
|---|---|---|
| 1 | `CLAUDE.md` | The operating rules. The authority on folder layout, the sponsorship gate, the never-re-apply rule, and output conventions. |
| 1b | `STRUCTURE.md` | The complete file map. Where every folder and file lives, and which are generated. |
| 2 | `context/*.md` | Her real facts. **The only legal source of resume content.** Read the files, not your memory of them. |
| 3 | `system/modes/_shared.md`, then `_profile.md` | Scoring and decision thresholds. `_profile.md` overrides `_shared.md` and wins. |
| 4 | `.claude/skills/resume-tailor/references/` | Tailoring playbook, the three-pass recruiter audit, ATS rules. |
| 5 | `system/data/applications.tsv` | Who must never be surfaced again. |

## The four rules that are never negotiable

1. **The honesty wall.** If a fact is not in `context/`, it does not exist.
   Never invent a metric, date, tool, team size or publication. A skill she has
   not used cannot appear in any form, including hedges like "familiar with".
   A missing requirement is reported as a gap, never filled with a guess.
2. **The sponsorship gate.** Silence about sponsorship is a KEEP. Only an
   explicit refusal, or a citizenship/clearance/ITAR requirement, excludes.
   Details and the exact patterns: `system/config/sponsorship.yml`.
3. **Never re-apply.** Check the tracker before surfacing anything.
4. **One page**, unless explicitly asked otherwise. Never fix a spill by
   shrinking margins or fonts — cut content.

## The wall between the two fights

**Fight 1, get shortlisted** — won by the resume, from facts already in
`context/`. **Fight 2, win the interview** — won by preparation, weeks later.

A skill in a study plan is a skill she does not have yet. It never appears on a
resume, in any hedged form, until it is genuinely learned *and* written into
`context/`. Say this out loud each time you produce a study plan.

## Who you are working for

She is not a developer. She does not read code, run commands or edit YAML.
Run things yourself; never answer with "now run this". Explain in one sentence
before and one after. Confirm before anything hard to undo. This workspace
*prepares* applications — she reviews and submits every one.

## The three ways this workspace runs

| Way | For | Entry point |
|---|---|---|
| **A coding CLI** | You, right now | This file, then `CLAUDE.md` |
| **A local app** | Power use: live PDF preview, editing, tracking | `python dashboard/run.py` |
| **A chat project** | Phone or laptop, on a subscription, no API key | `python system/scripts/export_project_pack.py`, then upload `output/project-pack/` |

The third is how this reaches someone who will never open a terminal. The pack
is generated from these same files, so it cannot disagree with them.

## Useful commands

```bash
python dashboard/cli.py brief          # find jobs and build a resume for each
python dashboard/cli.py schedule       # print the OS command for a daily 9am run
python dashboard/cli.py status         # what is configured, what ran last
python system/scripts/export_project_pack.py   # rebuild the chat-app pack
python system/scripts/doctor.py        # health check; exit 0 means healthy
python -m pytest dashboard/tests -q    # the test suite
```

## Running it for someone else

Set `CAREER_OPS_ROOT` to another workspace folder and every path follows —
their `context/`, their `output/`, their tracker. One copy of the code, one
workspace per person, and nobody's private profile lives in the repository.

```bash
CAREER_OPS_ROOT=/path/to/their-workspace python dashboard/run.py
```

## Any LLM platform

The app talks to Anthropic, to the local Claude Code CLI, or to any
OpenAI-compatible endpoint — OpenAI, OpenRouter, Groq, Together, DeepSeek,
Mistral, Fireworks, Ollama, LM Studio, vLLM. Adding a platform is a base URL and
a model name in Settings, not a code change. Without any of them the
deterministic half still runs: job finding, the sponsorship gate,
never-re-apply, link checking, keyword scoring and PDF building.
