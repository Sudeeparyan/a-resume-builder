---
description: Find sponsorship-safe US jobs for Annie and build a tailored one-page resume (LaTeX + PDF) and study plan for each
argument-hint: "[count] [track|remote|cap-exempt|role title]"
---

# /hunt — the whole loop, one command

Arguments: `$ARGUMENTS` (may be empty). Parse loosely:
- a bare number → how many applications to prepare (default **10**)
- `remote` → Remote (US) only
- `cap-exempt` → universities, national labs, nonprofit research institutes, academic medical centers only
- anything else → a role/track filter (e.g. `data engineer`, `embedded`)

Run every step without asking permission in between; she asked for the whole thing. `PY` below means `career-dashboard/backend/.venv/bin/python` and `WS` means `$PY career-dashboard/backend/scripts/workspace.py`.

## 1. Load the facts

Read `career-dashboard/AGENTS.md`, then `career-dashboard/data/context/` (all nine files plus `QUESTIONS-FOR-YOU.md`), `data/config/profile.yml`, `portals.yml`, `regions.yml`, `sponsorship.yml`, and `backend/workflows/modes/_shared.md` → `_profile.md` → `batch-resumes.md`. She is on **active F-1 OPT**: authorized to work now, sponsorship needed later.

## 2. Age the tracker

`WS age` (applications quiet 21 days become ghosted). `WS summary` shows what is saved, applied and excluded.

## 3. Find roles (~1.5× the target, the gate will cut some)

1. Tracked career pages first, no AI: `WS run --kind discovery --preset portals`.
2. Then AI discovery (`WS run --kind discovery`) and live search (Indeed `search_jobs` with country `US`, then the employer/ATS page). Always include a cap-exempt pass and sponsorship-positive queries.
3. Unless the arguments narrow it, aim for the batch mix in `profile.yml`: **4 Data · 2 ML/AI · 2 Software · 2 Embedded**.

## 4. Pull the full JD and gate it

For each lead found by hand, save the full JD to a scratch file and run `WS sponsor-check --company "<name>" --file <jd.txt>` and `WS check-reapply --company "<name>" --title "<role>"`. Save survivors (and exclusions, so they are logged with their sentence) with `$PY career-dashboard/backend/scripts/career.py add --file <job.json>` (fields: company, title, location, url, description, requisition_id). Leads found by the app were gated already.

## 5. Verify the link

`$PY career-dashboard/.agents/skills/verify-job-url/scripts/verify_job_url.py --url "<url>"`. Drop dead links.

## 6. Rank and pick

Tier first (**S → A → B → C**), then score. Take the top N **distinct companies**. Assign N different signature projects across the batch (`career-dashboard/data/signature-projects.md` shows who already owns what; Pacman coursework can only support).

## 7. Build each application

1. `$PY career-dashboard/backend/scripts/career.py prepare JOB_ID [--project PROJ-ID]` → `data/output/applications/Annie_Manoharan_<Company>_<NN>/`.
2. Research → `company-research.md` (`modes/deep.md`). Mandatory, every time.
3. Tailor with the `resume-tailor` skill: registry facts only, recruiter audit, fit exactly **one US Letter page** (cut content in the documented order; never shrink fonts below 10pt or touch margins).
4. Validate: `$PY career-dashboard/backend/scripts/validate_resume.py <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir <folder>/resume-preview --qa-json <folder>/qa.json`. Look at `page-01.png`.
5. Study plan → `study-plan.md`: `WS run --kind study_plan --job-id JOB_ID` (or `modes/upskill.md` by hand).

## 8. Report back

`data/output/SUMMARY.md` regenerates itself. Print:

| # | Company | Role | Tier | Score | Location | Folder | Apply |

Then briefly: how many were found, kept and excluded, **and the sentence behind each exclusion**; the single skill most of these roles wanted that she does not have yet; **one plain next step**.

## Non-negotiable

- Both `resume.tex` and `resume.pdf` in every folder.
- Every resume exactly one page, verified.
- Ten companies means ten different signature projects.
- Never surface an excluded, already-applied or recently-rejecting company.
- Never invent a listing, a link or a fact. If fewer than asked, say so and why. Never apply for her.
