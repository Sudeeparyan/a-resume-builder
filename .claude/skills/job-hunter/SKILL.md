---
name: job-hunter
description: >-
  Find, verify, sponsorship-screen, rank and save US job openings for Annie. Use when asked to
  "find jobs", "search for roles", "what should I apply to this week", "scan companies", "refresh
  the job list", "give me 10 jobs", or to check a specific company's openings. Runs the hard
  sponsorship gate and the never-re-apply rules through the career-dashboard app, so an excluded,
  already-applied or recently-rejecting company is never surfaced. United States only. Never
  invents a listing or a link.
---

# Job hunter

Everything runs through the app in `career-dashboard/`; `PY` means `career-dashboard/backend/.venv/bin/python`, `WS` means `$PY career-dashboard/backend/scripts/workspace.py`.

## Read first

`career-dashboard/AGENTS.md`, then `career-dashboard/data/context/` (especially `07-preferences.md` and `01-basics.md`), `data/config/profile.yml`, and `backend/workflows/modes/scan.md` (the full procedure). If a preference is still open in `QUESTIONS-FOR-YOU.md`, ask her plainly and offer to record the answer.

## The rules you enforce

- **Sponsorship gate** (`WS sponsor-check --company "<name>" --file <jd.txt>`): an explicit refusal, or a citizenship/clearance/ITAR/EAR/permanent-residency requirement, excludes the posting; it is logged with its sentence. Silence is shown. "Must be authorized to work in the US" never excludes: she is authorized (F-1 OPT).
- **Never re-apply** (`WS check-reapply --company "<name>" --title "<role>"`): same company and role never again; rejected → company hidden 180 days; ghosted → different role only, after 90 days.
- **Role fit**: four tracks, entry level, ≤4 years, United States or Remote (US).
- **Ranking**: tier S (cap-exempt) → A (says it sponsors) → B (proven H-1B sponsor) → C (silent), then score.

## Steps

1. Tracked career pages: `WS run --kind discovery --preset portals` (no AI call).
2. AI discovery: `WS run --kind discovery` (or `--preset balanced_five`).
3. By hand: Indeed `search_jobs` (country `US`) and `get_job_details` for the full JD; employer/ATS pages beat aggregators. Quote restrictive sentences verbatim.
4. Gate, then save: `$PY career-dashboard/backend/scripts/career.py add --file <job.json>` (it runs the gate and the re-apply check itself).
5. Verify links with the `verify-job-url` skill.
6. Report a ranked table (tier, score, company, role, location, link), the excluded postings with their sentences, and one plain next step. `career-dashboard/data/output/SUMMARY.md` refreshes itself.

For "give me N jobs **and** resumes", switch to `/hunt`.
