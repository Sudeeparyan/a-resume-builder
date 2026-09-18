# Backups

## 2026-09-18-pre-port/

The workspace as it was before it was rebuilt on the newer career-dashboard app. Nothing here is read by the app; it is kept for reference and history.

| Folder / file | What it was | Where it went |
|---|---|---|
| `system/` | Config, modes, structured profile, LaTeX templates, stdlib scripts (sponsor check, tracker, PDF build), USCIS sponsor data | Config, sponsor data and rules → `career-dashboard/data/config/` and `data/sponsors/`; modes → `career-dashboard/backend/workflows/modes/`; scripts replaced by `backend/services/sponsorship.py`, `reapply.py`, `portals.py` and the validators |
| `dashboard/` | The older FastAPI + React dashboard | Replaced by `career-dashboard/` |
| `output/` | `SUMMARY.md` and two application folders (USC, Databricks) | Both applications re-saved through the sponsorship gate and rebuilt as fresh one-page drafts in `career-dashboard/data/output/applications/`. **Do not send the old PDFs**: they predate the Q1 and Q4 answers, and the Databricks one names Medtronic for the ~94% figure and prints a leaked "see Q4" note |
| `.claude/` | Skills and the `/hunt` command | Rewritten at the repo root `.claude/` against the new app |
| `.github/` | Copilot agents | Rewritten in `career-dashboard/.github/agents/` (US Job Hunter, Resume Builder, Interview Coach, …) |
| `AGENTS.md`, `CLAUDE.md`, `README.md`, … | Old root docs | Policy merged into `career-dashboard/AGENTS.md`; new root docs written |

Annie's `context/` folder was moved, not copied, to `career-dashboard/data/context/`, so it has one home.

## <date>-fresh-start/ (created on demand)

`career-dashboard/backend/scripts/fresh_start.py --yes` snapshots the database, projections and application folders here before clearing the job list. Each has its own README explaining how to restore it.
