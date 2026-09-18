# Career workspace architecture

SQLite at `data/career.db` is the sole mutable authority. The JSON and Markdown
files beside it are regenerated projections, never independent state.

## Five folders

| Folder | Holds |
|---|---|
| `frontend/` | React and TypeScript client; `npm run dev` for development. |
| `backend/` | All Python, self-contained: its own `.venv`, `run.py`, requirements, the FastAPI app, domain services, CLI, agent prompts, and the AI layer. |
| `data/` | The database, the candidate's own config and evidence, LaTeX templates, generated applications, and recovery snapshots. |
| `tests/` | Python and API tests. Frontend component tests live beside their components. |
| `docs/` | This directory. |

`backend/paths.py` is the directory map. Code asks it where things are rather
than counting parent directories, so a future move is one file.

Inside `backend/`: `dashboard/` (HTTP), `services/` (domain), `scripts/` (CLI
and validators), `workflows/` (agent briefs as Markdown), `ai/` (providers and
the specialist agents), plus the standalone modules `migrations.py`,
`job_quality.py`, `assessment.py`, `chat_changes.py` and `resume_rules.py`.

## Write path

Every mutation commits to SQLite, records an activity event where appropriate,
then calls `CareerServices.sync_projections()`. Posting expiry never deletes a
row. Resume and Profile chats go through revision-bound `chat_change_sets`;
resume changes create `studio_versions`, and Profile changes stay reviewable
knowledge entries until confirmed.

## What AI decides, and what it does not

Models supply judgement inside a step: which requirements a job description
states, whether a page reads as closed, how to reword a summary. They never
produce a score or a state. Every number comes from deterministic code in
`backend/assessment.py` and `backend/job_quality.py`, so a model change cannot
move a score. Requirement excerpts are checked against the saved job
description and discarded when they do not match.

## Isolation

The hiring-manager agent receives only the job description and public company
research. It is reached through `run_isolated()`, which accepts those two
fields and nothing else; the ordinary `run()` refuses it outright. Candidate
data enters only in the separate comparison step. See `AI-AGENTS.md`.

API keys are read server-side from the environment, either `.env`, or
`keys.txt`. They are never returned to the browser, written to SQLite, or
included in an error message.
