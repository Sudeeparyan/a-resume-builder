# Annie Career Workspace — agent instructions

This workspace belongs to **Annie Prasanna Manoharan** and targets the **United States job market only**. It exists to remove three time sinks: finding roles that are actually open to her, re-tailoring a resume for each one, and remembering who already said no, so she never applies twice.

Read, in order: `data/config/profile.yml`, `data/context/evidence.yml`, `data/context/QUESTIONS-FOR-YOU.md`, `data/context/PROFILE-NOTES.md`, then the numbered files `data/context/01-basics.md` … `09-anything-else.md`. The registry (`evidence.yml`) is the external-wording authority; the numbered files are Annie's own words and win any disagreement. New notes in `data/context/UPDATES.md` stay pending until reviewed into the registry.

## Who you are working for

**Annie is not a developer.** She does not read code, run terminal commands, or edit YAML or LaTeX.

- **You run everything.** Never answer "now run this command" or "open this file and change…".
- **Plain language, briefly.** One sentence before a step, one after. Define a term in half a sentence the first time.
- **Ask like a person, not a form.**
- **Confirm before anything hard to undo**: sending an email, submitting an application. This workspace *prepares* applications; Annie reviews and submits each one.
- **When you are done, hand back one plain next step.**

## The sponsorship rule — read before surfacing any job

She is on **active F-1 OPT** and **is authorized to work in the US now**. The gate is `backend/services/sponsorship.py`, configured by `data/config/sponsorship.yml`.

| What the posting says | What happens |
|---|---|
| Explicitly **will not sponsor** ("without sponsorship now or in the future", "we do not sponsor") | **EXCLUDED.** Never listed anywhere. Logged in Excluded roles with the sentence that triggered it. |
| Requires **US citizenship, a security clearance, ITAR/EAR or US-person status, or permanent residency** | **EXCLUDED.** She cannot lawfully be hired, whatever the interview outcome. |
| **Says nothing** about sponsorship | **SHOWN.** Most postings; where most offers come from. |
| Explicitly **will sponsor** | **SHOWN, ranked top.** |

**Do not over-filter.** "Must be authorized to work in the United States" does not disqualify her. "No security clearance required" does not disqualify her. Only an explicit refusal or a citizenship/clearance requirement excludes.

**Sponsorship history never excludes anyone.** H-1B records, E-Verify and cap-exempt status are ranking signals only. Tiers: **S** cap-exempt employer (universities, academic medical centers, national labs, nonprofit research institutes; no lottery) · **A** posting says it sponsors · **B** proven H-1B sponsor, silent posting · **C** silent, no record (the normal case, still worth applying).

Every exclusion is stored in `excluded_postings` with its sentence and shown under **Excluded roles** on the Dashboard and in `data/output/SUMMARY.md`. A wrong exclusion is restored from the Dashboard; a restore sticks, and the daily posting sweep will not exclude the same posting again for the same sentence.

## Never re-apply

`backend/services/reapply.py`, with limits in `profile.yml reapply`:

- Same company **and** same role: never surfaced again, at any status, including excluded postings and anything archived by a fresh start.
- Company **rejected** her: the whole company is hidden for **180 days**; that exact role never again.
- **Applied** and silent for **21 days**: the hourly scheduler marks it **ghosted**. The company is eligible again after **90 days**, for a **different** role only. A reply (a status change or a confirmed email) takes it out of ghosted.

This overrides the previous edition's "never age an application automatically"; Annie's rule wins.

## Evidence and scope

- **Never fabricate.** If it is not in `data/context/`, it does not go on a resume. A missing requirement is reported as a gap, never filled with a guess.
- **Never state a total years of experience.** `EXP-TOTAL-YEARS` is missing by design.
- **Never claim a publication.** Annie says she has one or more, but `PUB-001` stays on hold until she gives the title, venue, year and author position (Q3).
- The ~94% test-automation figure belongs to **Dräger** (Q4, answered 2026-09-18) and is worded "approximately 94%". It may appear only in the Dräger bullet; the validator rejects it anywhere else.
- Soliton is two roles (Q1, answered 2026-09-18): Engineering Intern Jul 2022 – May 2023, then Project Engineer Jun 2023 – Jun 2024.
- InsOps is a **Data Engineering Intern** role. The superseded "Data Science Intern / InsOpsAI" framing is held and never reused.
- MiGa and DualFit are **AICV Lab research**, not side projects. Preserve her hedges ("Contributed to", "Supported"); never upgrade a hedge to ownership.
- Target four tracks (`profile.yml role_tracks`): **A** Data / Analytics Engineering, **B** ML / AI Engineering, **C** Software Engineering, **D** Embedded / Test Automation. Entry level only: no Senior/Staff/Lead/Principal/Manager titles, nothing asking for more than 4 years.
- **Never write to `data/context/`** except `QUESTIONS-FOR-YOU.md`, or when Annie asks you to record something ("I built X", "I finished the AWS course"); then say exactly which file changed.
- Never submit applications or send outreach without her explicit go-ahead. Preparing a resume is not a submission.

## The two fights, and the wall between them

**Fight 1: get shortlisted.** Won by the resume, using only facts already in `data/context/`.
**Fight 2: win the interview**, three to six weeks later. Won by preparation: `study-plan.md` in each application folder, written by the study-plan agent from the honest gaps.

**The wall is absolute.** A skill in a study plan is a skill she does not have yet. It never appears on a resume, not as "familiar with", not as "exposure to", in no hedged form, until it is learned **and** written into `data/context/`. Say this each time you hand over a study plan.

## Resume contract

The contract is read from `data/config/profile.yml resume_contract` by `backend/resume_contract.py`; every validator, the fitter and the batch runner use it.

- **Exactly one US Letter page**, body text 10–11pt, fixed margins. **Never fix length by shrinking margins or fonts; cut content**, in the documented order: third bullet of the supporting project → last bullet of the oldest role → coursework line → second degree. Resume Studio's **Fit to one page** does this and never goes below 10pt.
- Sections: Education, Technical Skills, Professional Experience, Projects. Tracks A and C put Experience first; B and D put Projects first.
- **One signature project per company**, first in Projects, chosen for that employer alone and never reused as another company's signature (`signature_assignments`, projected to `data/signature-projects.md`). One supporting project may repeat freely. Projects registered `signature_eligible: false` (Pacman coursework) can only support. If nothing unused fits, ship the strongest real project and write a **build-now spec** into that company's `study-plan.md`. An unbuilt project never goes on a resume, in any tense.
- Every content line carries a `% EVIDENCE:` tag naming registry IDs; company research never creates candidate experience.
- **Banned filler:** passionate about, results-oriented, proven track record, leveraged, spearheaded, synergies, robust, seamless, cutting-edge, dynamic professional, plus everything in `data/context/08-voice.md` ("Responsible for", "Worked on", "Helped with").

Each application folder is `data/output/applications/Annie_Manoharan_<Company>_<NN>/` (company with spaces and punctuation removed; NN counts per company) and holds:

- `job-description.md`
- `evaluation.md`
- `company-research.md`
- `study-plan.md`
- `evidence-map.yml`
- `resume.tex` and `resume.pdf` (always both: the PDF to apply, the `.tex` to edit in Overleaf)
- `resume-preview/page-01.png`
- `qa.json`

The dashboard prepares a deterministic draft by selecting existing registry wording and marks role eligibility and requirement review pending. Complete the evaluation, sourced employer research and evidence mapping without fabrication.

Validate with `backend/.venv/bin/python backend/scripts/validate_resume.py <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir <folder>/resume-preview --qa-json <folder>/qa.json`. Look at the rendered page. Only after inspecting the current output, rerun with `--visual-review pass --visual-reviewer <reviewer>`. A failed or pending review is not release-ready.

Job fit, supported requirement coverage and artifact QA are different things; never describe keyword counts as ATS scores or probabilities.

## The front page

`data/output/SUMMARY.md` is generated from the database after every change, with six sections: **Last run**, **Your resumes** (tier, status, apply link), **Pipeline** (days quiet), **Companies found, no resume yet**, **Excluded** (with the sentence), **What to study this week** (gaps ranked by how many open applications need them). Never hand-edit it; it is what Annie reads.

## Batch requests

"Give me 10 companies" (or `/hunt`) means: discover and verify up to ten eligible, live US postings that pass the sponsorship gate and the never-re-apply check; research, tailor, compile, render, inspect and deliver ten isolated one-page folders plus study plans. Keep replacing excluded, duplicate, expired or ineligible leads. If the honest search yields fewer, report the shortage and the search coverage. Use `backend/workflows/modes/batch-resumes.md` and the batch scripts. Never invent matches to reach a count.

## Layout and state

The repo mirrors the reference layout: `career-dashboard/` (this app), `../daily-job-search/` (Tectonic runtime wrapper, `search.py`, dated run projections, `history.csv`), `../backup/` (the pre-port snapshot and any fresh-start snapshots).

Inside `career-dashboard/`: `frontend/` is the React UI; `backend/` holds all Python with its own `.venv` and `run.py` (`dashboard/` API, `services/` application services including `sponsorship.py` and `reapply.py`, `scripts/` executables, `workflows/` agent playbooks, `ai/` LangChain specialists); `data/` holds everything that is Annie's or generated (`career.db` is the single mutable authority; `context/`, `config/`, `templates/`, `sponsors/`, `output/`). `backend/paths.py` is the directory map and the single timezone (America/Chicago).

The Markdown trackers in `data/` are read-only projections. `data/career.db` owns jobs, statuses, excluded postings, signature assignments, re-apply history, knowledge, goals, email evidence and agent runs. Use `backend/scripts/workspace.py` (`summary`, `goals`, `profile`, `mail`, `runs`, `run --kind discovery|research|email|study_plan`, `export`) rather than editing projections.

Verified exact Gmail confirmations establish application status; receipt time stays separate from a stated submission date. Gmail workers expose only read tools. The independent hiring worker never receives candidate context. Gmail sync is optional and needs Codex signed in on this Mac.

## Development checks

Use a disposable workspace in tests. Run `backend/.venv/bin/python -m pytest tests -q` and `backend/.venv/bin/python backend/scripts/validate_workspace.py`. The dashboard binds only to loopback, rejects foreign browser origins and serves output files through a path-constrained route. Keep the profile and registry revisions aligned; any changed claim needs a revision bump and rebuilt artifacts.
