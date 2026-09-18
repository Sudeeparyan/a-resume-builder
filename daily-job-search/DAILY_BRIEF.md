# Annie's daily job search

Times are US Central (America/Chicago), the app's single timezone. There is no scheduled external task yet; a daily run is started by Annie, from the dashboard (Daily Search → Find suitable jobs) or from this brief.

## Outcome

Read the planner with `career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/workspace.py goals`. Find up to today's remaining application target in unique suitable postings (the default is 30 a week, Monday–Saturday; unfinished work carries forward). Re-read the active profile with `workspace.py profile` on every run. Optimize for credible applications and interviews; never promise an offer or an invented ATS score.

## Candidate evidence and targeting

Follow `career-dashboard/AGENTS.md`, then `data/context/` (Annie's own files win), `data/config/profile.yml` and `data/context/evidence.yml`. The LaTeX template is a layout, not evidence.

Entry-level US roles in four tracks: Data / Analytics Engineering, ML / AI Engineering, Software Engineering, Embedded / Test Automation. All US hubs plus Remote (US). No Senior/Staff/Lead/Principal/Manager titles, nothing asking for more than 4 years.

Annie is on active F-1 OPT: authorized to work in the US now, sponsorship needed later. Never state a total years of experience, never mention a publication (on hold until she gives the details), and keep the ~94% figure in the Dräger bullet only.

## Discovery and delivery

1. **Tracked career pages first**: `workspace.py run --kind discovery --preset portals` (no AI).
2. Then AI discovery (`--preset default` or `balanced_five`), or live web search by hand. Open the specific posting; quote any sponsorship, authorization, citizenship or clearance sentence verbatim.
3. **Sponsorship gate**: an explicit refusal, or a citizenship/clearance/ITAR/EAR/permanent-residency requirement, excludes the posting; it is logged with the sentence. Silence is shown. "Must be authorized to work in the US" never excludes.
4. **Never re-apply**: same company and role ever; a company that rejected her within 180 days; a ghosted company within 90 days (different role only after that).
5. Verify employer, title, US location, description, seniority and an active application route. Keep replacing excluded, closed, inaccessible and duplicate leads; if honest matches run out, report the shortage and coverage.
6. Save each posting with `daily-job-search/search.py add --file POSTING.json` (after `search.py start`); it runs the gates and links the saved job to today's run.
7. Prepare each draft (`career-dashboard/backend/scripts/career.py prepare JOB_ID`, or Resume Studio). Research the company, map requirements to evidence, choose the signature project (unused by any other company) and a supporting project, fit exactly one US Letter page, validate, inspect the page, and write the study plan. Required files per application folder: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`.
8. Deliver a ranked table (tier first): company, role, location, tier, direct application link, fit, key gap, resume PDF and folder. Name the best three next applications and the excluded postings with their sentences.
9. Update `history.csv` with date, company, role, canonical URL, requisition ID, location, state and artifact path. States are facts: discovered, excluded, prepared, delivered, user-confirmed applied. A resume existing is never an application.

## Local PDF runtime

Prefix validator commands with the runtime wrapper so Tectonic and the PDF tools use local caches:

```sh
python3 daily-job-search/with_resume_runtime.py career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/validate_resume.py PATH/resume.tex --compile --output PATH/resume.pdf --render-dir PATH/resume-preview --qa-json PATH/qa.json --evidence-map PATH/evidence-map.yml
```

Only after viewing the page may a follow-up validation record `--visual-review pass --visual-reviewer "<reviewer>"`.

## User interaction

Annie is not a developer: run everything, explain in plain words, hand back one next step. Research and local document preparation are authorized. Never submit applications, contact recruiters or upload her files to external portals without her explicit go-ahead.

## Shared tracking

`career-dashboard/data/career.db` owns statuses, excluded postings, signature assignments and search runs. `run.json`, `data/jobs.json`, the Markdown trackers and `data/output/SUMMARY.md` are generated views. Use `search.py notes --file NOTES.md` for coverage, rejected leads and shortages, and update `../WORKSPACE-STATE.md` after delivery.
