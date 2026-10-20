---
name: hunt
description: >-
  The whole loop in one request: find sponsorship-safe US jobs for Annie Prasanna Manoharan, then
  build a tailored one-page resume (LaTeX + PDF) and a study plan for each. Use for "give me 10
  companies", "hunt 10", "find 5 jobs and make the resumes", "make 10 tailored resumes", or a batch
  of 2-10 JDs or links. Optional words narrow it: a number (how many, default 10), "remote",
  "cap-exempt", or a role or track ("data engineer", "embedded"). Never applies for her.
---

# Hunt: find jobs, then build every application

Read the request loosely:
- a bare number → how many applications to prepare (default **10**)
- `remote` → Remote (US) only
- `cap-exempt` → universities, national labs, nonprofit research institutes, academic medical centers only
- anything else → a role or track filter (e.g. `data engineer`, `embedded`)

Run every step without asking permission in between; she asked for the whole thing. `career` means
`.\career.cmd` on Windows or `./career` on macOS, Linux and Git Bash (see the root `AGENTS.md`).

## 1. Load the facts

Read `career-dashboard/AGENTS.md`, then `career-dashboard/data/context/` (all nine files plus
`QUESTIONS-FOR-YOU.md`), `data/config/profile.yml`, `portals.yml`, `regions.yml`, `sponsorship.yml`,
and `backend/workflows/modes/_shared.md` → `_profile.md` → `batch-resumes.md`. She is on
**active F-1 OPT**: authorized to work now, sponsorship needed later.

## 2. Age the tracker

`career ws age` (applications quiet 21 days become ghosted). `career ws summary` shows what is saved,
applied and excluded.

## 3. Find roles (~1.5× the target, the gate will cut some)

1. Tracked career pages first, no AI: `career ws run --kind discovery --preset portals`.
2. Then AI discovery (`career ws run --kind discovery`, which runs on the app's Auto route: her Kimi,
   Codex and Claude plans first) and live search (Indeed `search_jobs` with country `US`, then the
   employer or ATS page). Always include a cap-exempt pass and sponsorship-positive queries.
3. Unless the request narrows it, aim for the batch mix in `profile.yml`: **4 Data · 2 ML/AI ·
   2 Software · 2 Embedded**.
4. Excluded, duplicate, expired and inaccessible leads do not count toward the number; keep searching
   until it is met or the search is honestly exhausted. Do not ask her to paste JDs when current
   postings can be found and verified.

## 4. Pull the full JD and gate it

For each lead found by hand, save the full JD to a scratch file and run
`career ws sponsor-check --company "<name>" --file <jd.txt>` and
`career ws check-reapply --company "<name>" --title "<role>"`. Save survivors (and exclusions, so they
are logged with their sentence) with `career add --file <job.json>` (fields: company, title, location,
url, description, requisition_id). Leads found by the app were gated already.

## 5. Verify the link

`career verify-url --url "<url>"` (the `verify-job-url` skill). Drop dead links.

## 6. Rank and pick

Tier first (**S → A → B → C**), then score. Take the top N **distinct companies**. Assign N different
signature projects across the batch (`career-dashboard/data/signature-projects.md` shows who already
owns what; supporting-only projects such as the Pacman coursework can only support). Where the bank
runs short, say so and put a build-now spec in that company's study plan.

## 7. Build each application (the `resume-tailor` skill, once per company)

1. `career prepare JOB_ID [--project PROJ-ID]` →
   `career-dashboard/data/output/applications/Annie_Manoharan_<Company>_<NN>/`.
2. Research → `company-research.md` (`modes/deep.md`). Mandatory, every time.
3. Tailor with the `resume-tailor` skill: registry facts only, recruiter audit, fit exactly **one US
   Letter page** (cut content in the documented order; never shrink fonts below 10pt or touch margins).
4. Validate: `career check-resume <folder>/resume.tex --compile --output <folder>/resume.pdf
   --render-dir <folder>/resume-preview --qa-json <folder>/qa.json`. Look at `page-01.png`. It also
   removes AI marks (the `remove-ai-marks` skill, built in): the PDF keeps only its title and author,
   and a hidden or look-alike character in `resume.tex` fails the check.
5. Study plan → `study-plan.md`: `career ws run --kind study_plan --job-id JOB_ID` (or `modes/upskill.md`
   by hand).

Each company is built in isolation: its own folder, its own context. A worker passes only when the nine
artifacts exist (`job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`,
`evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`) and QA passes;
at most three evidence-safe layout repairs per worker.

For a batch run through the batch scripts (`modes/batch-resumes.md`), folders go under
`career-dashboard/data/output/batches/{run-id}/` and the whole batch is checked with
`career batch-check career-dashboard/data/output/batches/{run-id}/batch.yml --json
career-dashboard/data/output/batches/{run-id}/batch-qa.json`. Any failure is unreleased; repair only
the affected worker.

## 8. Report back

`career-dashboard/data/output/SUMMARY.md` regenerates itself. Print:

| # | Company | Role | Tier | Score | Location | Folder | Apply |

Then briefly: how many were found, kept and excluded, **and the sentence behind each exclusion**; the
single skill most of these roles wanted that she does not have yet; **one plain next step**.

## If your AI app reaches its usage limit mid-hunt

Write an "In progress" line in `WORKSPACE-STATE.md` (how many are done, the job IDs and folders, the next
step) before you stop, so another AI app (Claude, Codex, Kimi) opened in this folder can continue from
the same database without redoing work.

## Non-negotiable

- Both `resume.tex` and `resume.pdf` in every folder.
- Every resume exactly one page, verified, with no AI marks (`qa.json` → `ai_marks` empty).
- Ten companies means ten different signature projects.
- Never surface an excluded, already-applied or recently-rejecting company.
- Never invent a listing, a link or a fact. If fewer than asked, say so and why. Never apply for her.
