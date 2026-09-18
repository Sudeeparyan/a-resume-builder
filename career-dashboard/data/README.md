# Career records

`career.db` is the authoritative local SQLite store for saved opportunities, statuses, sponsorship tiers, excluded postings (with the sentence that excluded each one), signature-project assignments, re-apply history, profile knowledge, goals, email evidence and agent runs. It is gitignored; back it up before replacing a workspace (`backend/scripts/fresh_start.py` snapshots it for you).

`pipeline.md`, `application-tracker.md`, `applied-companies.md`, `signature-projects.md`, `jobs.json`, `activity.json` and `../daily-job-search/YYYY-MM-DD/run.json` are generated projections. Update records through the dashboard, `backend/scripts/workspace.py` or `backend/scripts/career.py`; `workspace.py export` refreshes every projection. Only recorded application dates or confirmed email evidence establish a submission.

- `config/` — `profile.yml` (identity, tracks, resume contract), `sponsorship.yml` (the gate), `portals.yml` (tracked career pages), `regions.yml` (US hubs).
- `context/` — Annie's own files and the evidence registry. See `context/QUESTIONS-FOR-YOU.md` for what is still open.
- `sponsors/` — public USCIS H-1B employer history and its rebuildable SQLite index (`index.db`, gitignored).
- `templates/` — the one-page base resume and batch/evidence-map examples.
- `output/` — `SUMMARY.md` (the front page), `base/` and `applications/`.
- `interview-prep/` — the interview story bank.
