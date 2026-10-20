# Annie Career Workspace — agent instructions

> **Profiles.** This file is the policy of the backup profile `annie`, whose workspace is `data/` here. Other profiles live in `profiles/<id>/`, each with its own `AGENTS.md`, country pack (`backend/countries/<code>/`) and data; follow that file when working on them, and never mix data between profiles. The shell (`backend/dashboard/shell.py`) serves every profile at `/p/<id>/`; `backend/profiles.py` is the registry (Annie is locked: never reset or deleted).

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
| Explicitly **will not sponsor** ("without sponsorship now or in the future", "we do not sponsor", "will not consider candidates who require sponsorship", "Visa sponsorship: No"), or turns away OPT/CPT/F-1/H-1B holders | **EXCLUDED.** Never listed anywhere. Logged in Excluded roles with the sentence that triggered it. |
| Requires **US citizenship, a security clearance, ITAR/EAR or US-person status, permanent residency, or permanent work authorization** | **EXCLUDED.** She cannot lawfully be hired, whatever the interview outcome. |
| **Says nothing** about sponsorship | **SHOWN.** Most postings; where most offers come from. |
| Explicitly **will sponsor** | **SHOWN, ranked top.** |

**Do not over-filter.** "Must be authorized to work in the United States" does not disqualify her. "No security clearance required" does not disqualify her. A sentence that *reports the absence* of restriction wording (for example a research note saying the posting carries no sponsorship, citizenship or ITAR/EAR language) is not a restriction — those absence claims are listed in `negation_guards`. Only an explicit refusal or a citizenship/clearance requirement excludes.

**US only, everywhere.** `is_us_location` in `backend/job_quality.py` decides. A role whose location is outside the US is never saved, not by a search, not by her own Save, not from the Tracker or chat (`add_posting` blocks it as `outside_us`), and never enters the Tracker. A posting that lists the US among other places counts. A trailing "IN" or "DE" counts only after a known Indiana or Delaware city, because feeds use them for India and Germany; "Tel Aviv, IL", "Montreal, CA" and "Tbilisi, Georgia" are not American. A bare "Remote" is kept unless its own text places the work abroad only ("remote within Canada").

**Sponsorship history never excludes anyone.** H-1B records, E-Verify and cap-exempt status are ranking signals only. Tiers: **S** cap-exempt employer (universities, academic medical centers, national labs, nonprofit research institutes; no lottery) · **A** posting says it sponsors · **B** proven H-1B sponsor, silent posting · **C** silent, no record (the normal case, still worth applying).

Every exclusion is stored in `excluded_postings` with its sentence and shown under **Excluded roles** on the Dashboard and in `data/output/SUMMARY.md`. A wrong exclusion is restored from the Dashboard; a restore sticks, and neither the daily posting sweep nor a discovery pass will exclude the same posting again for the same sentence. A feed pass (`--preset portals`) reads every role an employer lists, so it gates and logs only postings inside her target (US or US-remote, an entry-level title in her tracks, not an internship); the rest are counted in the run summary, not listed one by one.

**H-1B sponsor boards.** Besides the companies in `portals.yml`, the feed pass reads the public job boards (Greenhouse, Lever, Ashby, SmartRecruiters) of employers in the USCIS H-1B data: `data/sponsors/sponsor-boards.csv`, built by `backend/scripts/build_sponsor_boards.py` (rerun monthly or when the USCIS CSV is refreshed). A board is listed only when it had a current US posting and named the same employer as the USCIS legal name (and, when that name is one common word such as "Mercury", had a posting where USCIS records the employer); `backend/services/sponsor_boards.py` holds the checks. Each pass reads the 120 boards read least recently, after her tracked companies, and remembers each read in `sponsor_board_reads`. This widens *where* the search looks; it changes nothing about the gate. A company with no board or no H-1B record is still searched by the AI pass and still shown when its posting is silent.

**Sponsorship Tracker.** Every in-target posting a pass reads, saved or not, is kept for 60 days in `market_postings` and shown on the **Sponsorship Tracker** tab. Each row has the posting's quoted sponsorship sentence, its tier, the employer's USCIS approvals/denials, advertised pay and the gate that decided it. It can be filtered and exported to CSV, and a row can be saved to her jobs (the sponsorship and never-re-apply gates still apply). Her status is joined from `jobs` at read time; the Tracker never keeps a second status list. Facts with sources, never immigration advice.

## Never re-apply

`backend/services/reapply.py`, with limits in `profile.yml reapply`:

- Same company **and** same role: never surfaced again, at any status, including excluded postings and anything archived by a fresh start.
- Company **rejected** her: the whole company is hidden for **180 days**; that exact role never again.
- **Applied** and silent for **21 days**: the hourly scheduler marks it **ghosted**. The company is eligible again after **90 days**, for a **different** role only. A reply (a status change or a confirmed email) takes it out of ghosted.

- **Removed with a reason that teaches** (the Dashboard's removal dialog, `REMOVAL_REASONS`): "Not this company" or "This company won't sponsor me" keeps every later role at that company out of automatic searches; "Wrong kind of role" keeps that job title out at every company. "Too senior", "Wrong location" and "Not suitable" apply to that vacancy only. A job Annie saves herself (Save a job, the Tracker, chat) is never blocked by a lesson; it only gets a note.

This overrides the previous edition's "never age an application automatically"; Annie's rule wins.

## Evidence and scope

- **Never fabricate.** If it is not in `data/context/`, it does not go on a resume. A missing requirement is reported as a gap, never filled with a guess.
- **The one carve-out: predicted Projects and Skills.** Per job, the Resume Studio tailor (`job_tailor`) may propose company-aligned projects and skills derived from the posting and employer research. They live only in the Projects and Technical Skills sections, are stored in `resume_items` with origin `predicted` (verified items are copied from the registry unchanged), and sit in the Assurance tab as pending until Annie keeps or removes them — before she applies. Employers, dates, degrees and personal details are never touched; predicted items never use the never-claim list, dates, percentages or banned filler; and nothing on the resume is marked "predicted" — the label exists only in the database and the review UI.
- **Never state a total years of experience.** `EXP-TOTAL-YEARS` is missing by design.
- **Never claim a publication.** Annie says she has one or more, but `PUB-001` stays on hold until she gives the title, venue, year and author position (Q3).
- The ~94% test-automation figure belongs to **Dräger** (Q4, answered 2026-09-18) and is worded "approximately 94%". It may appear only in the Dräger bullet; the validator rejects it anywhere else.
- Soliton is two roles (Q1, answered 2026-09-18): Engineering Intern Jul 2022 – May 2023, then Project Engineer Jun 2023 – Jun 2024.
- InsOps is a **Data Engineering Intern** role. The superseded "Data Science Intern / InsOpsAI" framing is held and never reused.
- MiGa and DualFit are **AICV Lab research**, not side projects. Preserve her hedges ("Contributed to", "Supported"); never upgrade a hedge to ownership.
- Target four tracks (`profile.yml role_tracks`): **A** Data / Analytics Engineering, **B** ML / AI Engineering, **C** Software Engineering, **D** Embedded / Test Automation. Entry level only: no Senior/Staff/Lead/Principal/Manager/Director titles, nothing asking for more than 4 years. Full-time only: no internships, co-ops or roles that require current enrollment (she completed her MS in May 2026).
- **Never write to `data/context/`** except `QUESTIONS-FOR-YOU.md`, or when Annie asks you to record something ("I built X", "I finished the AWS course"); then say exactly which file changed.
- Never submit applications or send outreach without her explicit go-ahead. Preparing a resume is not a submission.

## The two fights, and the wall between them

**Fight 1: get shortlisted.** Won by the resume, using only facts already in `data/context/`.
**Fight 2: win the interview**, three to six weeks later. Won by preparation: `study-plan.md` in each application folder, written by the study-plan agent from the honest gaps.

**The wall is absolute.** A skill in a study plan is a skill she does not have yet. It never appears on a resume, not as "familiar with", not as "exposure to", in no hedged form, until it is learned **and** written into `data/context/` — with one exception: per-company tailoring may propose it as a predicted Skills/Projects item under the 60/40 carve-out, which Annie reviews in Assurance before applying. The never-claim list (`SKILL-NEVER-001`) stays hard even for predicted items. Say this each time you hand over a study plan.

## Resume contract

The contract is read from `data/config/profile.yml resume_contract` by `backend/resume_contract.py`; every validator, the fitter and the batch runner use it.

- **Exactly one US Letter page**, body text 10–11pt, fixed margins. **Never fix length by shrinking margins or fonts; cut content**, in the documented order: third bullet of the supporting project → last bullet of the oldest role → coursework line → second degree. Resume Studio's **Fit to one page** does this and never goes below 10pt.
- Sections: Education, Technical Skills, Professional Experience, Projects. Tracks A and C put Experience first; B and D put Projects first.
- **One signature project per company**, first in Projects, chosen for that employer alone and never reused as another company's signature (`signature_assignments`, projected to `data/signature-projects.md`). One supporting project may repeat freely. Projects registered `signature_eligible: false` (Pacman coursework) can only support. If nothing unused fits, ship the strongest real project and write a **build-now spec** into that company's `study-plan.md`. An unbuilt project goes on a resume only as a predicted, review-gated item under the 60/40 carve-out above — never as experience, never with dates or metrics.
- Every content line carries a `% EVIDENCE:` tag naming registry IDs; company research never creates candidate experience. Predicted items tag their lines `% EVIDENCE: resume_items:<row id>`; an unresolved tag in Projects or Technical Skills is a validator **warning** (review queue), while Experience, Education and header tags stay hard failures. The Assurance tab (`GET /p/annie/api/v2/assurance/<job_id>`, or `--report` on the validator) merges that claim scan with the keep/remove decisions.
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

## Daily Search, readiness and the AI route (ported from the Template, October 2026)

Daily Search runs `services/pipeline.py`: find 1-5 jobs, then take each one end to end (posting re-read with the sponsorship gate, research with the hiring-manager view and the requirement check, tailor, one-page PDF, independent review, study plan) and finish with the ready-to-submit check (`services/readiness.py`). Readiness is a verdict (ready / needs review / not ready) and a score from fit, coverage and readability; it is never an interview prediction, and nothing is submitted. A resume is not ready while a predicted item waits in Assurance or the independent review of that exact PDF has no passing verdict. The Dashboard's **Needs you** lists only what Annie must do (a signed-out AI app, pending profile entries, Assurance items, open questions).

Cover letters (`services/cover_letters.py`) are written from registered evidence only, checked for every number, name and skill, audited by a second AI, and never mention visas, OPT, H-1B, green cards, citizenship or sponsorship; otherwise they are built from her registered sentences. Word copies of the resume and letter come from the same checked revision as the PDF.

Choosing **Auto** in Settings routes every AI step across her plans (Kimi Code, Codex, Claude Code, Antigravity), resting a plan at its usage limit until the reset time it printed; Azure is paid and last. The daily AI limit counts paid calls only. Agent runs are traced locally (`data/traces.db`); prompts and resume text never leave the PC.

## Layout and state

The repo mirrors the reference layout: `career-dashboard/` (this app), `../daily-job-search/` (Tectonic runtime wrapper, `search.py`, dated run projections, `history.csv`, and `morning_run.py` — the 07:00 scheduled daily run that discovers up to 5 jobs, tailors each resume and compiles the PDFs), `../backup/` (the pre-port snapshot and any fresh-start snapshots).

Inside `career-dashboard/`: `frontend/` is the React UI; `backend/` holds all Python with its own `.venv` and `run.py` (`dashboard/` API, `services/` application services including `sponsorship.py` and `reapply.py`, `scripts/` executables, `workflows/` agent playbooks, `ai/` LangChain specialists); `data/` holds everything that is Annie's or generated (`career.db` is the single mutable authority; `context/`, `config/`, `templates/`, `sponsors/`, `output/`). `backend/paths.py` is the directory map and the single timezone (America/Chicago).

The Markdown trackers in `data/` are read-only projections. `data/career.db` owns jobs, statuses, excluded postings, signature assignments, re-apply history, knowledge, goals, email evidence and agent runs. Use `backend/scripts/workspace.py` (`summary`, `goals`, `profile`, `mail`, `runs`, `run --kind discovery|research|email|study_plan`, `export`) rather than editing projections.

Verified exact Gmail confirmations establish application status; receipt time stays separate from a stated submission date. Gmail workers expose only read tools. The independent hiring worker never receives candidate context. Gmail sync is optional and needs Codex signed in on this Mac.

## Development checks

Use a disposable workspace in tests. Run `backend/.venv/bin/python -m pytest tests -q` and `backend/.venv/bin/python backend/scripts/validate_workspace.py`. The dashboard binds only to loopback, rejects foreign browser origins and serves output files through a path-constrained route. Keep the profile and registry revisions aligned; any changed claim needs a revision bump and rebuilt artifacts.
