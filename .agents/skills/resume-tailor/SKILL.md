---
name: resume-tailor
description: >-
  Research a company, then tailor Annie Prasanna Manoharan's one-page resume to its job description,
  producing company research, an audited LaTeX + PDF resume with a signature project unique to that
  company, an honest match assessment, and a study plan of what to learn before they call. Use
  WHENEVER a job description, job posting, JD, role spec or job link is provided and a resume is the
  goal, even if only the JD text is pasted. Also for "update my resume for this role", "write a cover
  letter for this job", "what should I learn for this company", or "run an ATS check". Uses only facts
  in career-dashboard/data/context/ and its evidence registry; never fabricates experience, metrics
  or skills.
---

# Resume tailor

You build resumes only for **Annie Prasanna Manoharan**. The app does the mechanics; you do the
judgment. Your output is truthful application material, never a promise of an interview. `career`
means `.\career.cmd` on Windows or `./career` on macOS, Linux and Git Bash (see the root `AGENTS.md`).

## Read first

1. `career-dashboard/AGENTS.md`
2. `career-dashboard/data/context/01-basics.md` … `09-anything-else.md`, and `data/context/files/` when a
   detail is unclear
3. `data/config/profile.yml`, `data/context/evidence.yml`, `data/context/QUESTIONS-FOR-YOU.md`,
   `data/context/PROFILE-NOTES.md`
4. The modes in `career-dashboard/backend/workflows/modes/`: `_shared.md`, `_profile.md`, `evaluate.md`,
   `deep.md`, `resume.md`, `quality.md`, `upskill.md`
5. `data/signature-projects.md` and `data/templates/resume-base.tex`

The LaTeX file is a renderer, not a factual source. Never take candidate facts from a target JD, company
research or `backup/`.

## Gates before any writing

1. **Sponsorship**: an explicit refusal, or a citizenship / clearance / ITAR/EAR / permanent-residency
   requirement, stops the job with `EXCLUDED — the posting says: "<sentence>"`.
2. **Never re-apply**: same company and role; a rejection within 180 days; a ghosted company within
   90 days.
3. **Role fit**: entry level, ≤4 years, United States, one of tracks A–D. Otherwise
   `SKIP — outside Annie's profile`. Keyword overlap never rescues an ineligible role.

## Pipeline (run every step)

| # | Step | How | Output |
|---|------|-----|--------|
| 1 | Gates | `career ws sponsor-check`, `career ws check-reapply`, then save with `career add --file <job.json>` | tier or the exclusion sentence |
| 2 | Prepare the folder | `career prepare JOB_ID` | `data/output/applications/Annie_Manoharan_<Company>_<NN>/` |
| 3 | Snapshot and evaluate | verify the posting; save the full JD with URL and access date as `job-description.md` and hash it; `modes/evaluate.md`: requirement IDs (`R01`…) mapped to registry IDs or marked a gap | `evaluation.md` |
| 4 | Research (mandatory) | `modes/deep.md` and `references/company-research.md` | `company-research.md` |
| 5 | Evidence map, then tailor | `modes/resume.md`: registry wording, `% EVIDENCE:` tags, a signature project no other company owns | `evidence-map.yml`, `resume.tex` |
| 6 | Recruiter audit, three passes | `references/recruiter-audit.md`, `references/ats-rules.md` | the audited resume |
| 7 | One page, validated | Resume Studio → Fit to one page, or `career check-resume …` (below); cut content in order, never fonts or margins | `resume.pdf`, `resume-preview/page-01.png`, `qa.json` |
| 8 | Quality review | `references/quality-review.md` (fail-closed) | `PASS` or `FAIL` with reasons |
| 9 | Study plan | `career ws run --kind study_plan --job-id JOB_ID` or `modes/upskill.md` | `study-plan.md` |
| 10 | Match assessment + one next step | `modes/_shared.md` → Match assessment | in the chat |

## Projects

The **signature project** is the best-ranked resume-ready project that no other company owns and that is
not supporting-only; it leads Projects with three bullets. One **supporting project** follows with two.
Copy `resume_content` exactly; never imply work for the target employer; if nothing fits, ship the
strongest real project and write a build-now spec into the study plan.

## Tailoring the template

Change only content slots, project fields and relevance ordering. Keep a `% EVIDENCE:` tag before every
content line. Tracks A/C put Experience first; B/D put Projects first. The app's Resume Studio tailor
(`job_tailor`) may also write predicted Projects/Skills items tagged `% EVIDENCE: resume_items:<id>`;
those are review-gated in the Assurance tab (keep/remove) and never touch employers, dates, degrees or
personal details.

## Fit and validate

`career check-resume <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir
<folder>/resume-preview --qa-json <folder>/qa.json` (it runs
`career-dashboard/backend/scripts/validate_resume.py`). Release needs exactly **one page** of US Letter,
10–11pt, two distinct registered projects, no unsafe content, no AI marks, a fresh PDF, and a manual
visual review of `page-01.png`. The same command runs the `remove-ai-marks` skill, built into the app
(`.agents/skills/remove-ai-marks/SKILL.md` → "In this workspace"): the PDF leaves with only its title
and author, and a hidden or look-alike character in `resume.tex` fails the check. Retype the word it
names. Too long: cut in the documented order (supporting project's third bullet → last bullet of
the oldest role → coursework line → second degree); never shrink fonts or margins. At most three repairs.

## Hard rules

- Never state a total years of experience; never mention a publication (`PUB-001` is on hold); the ~94%
  figure stays in the Dräger bullet. No GPA, certification or banned filler.
- Never put a study-plan skill or an unbuilt project on the resume, in any wording. Say the wall out
  loud with every plan.
- A missing requirement is first a "check your memory" question (logged in `QUESTIONS-FOR-YOU.md`),
  then a gap. Never a guess.
- `[FILL IN: …]` markers are how you ask for a number only Annie knows; the validator refuses to pass a
  resume that still contains one.
- Always ship both `resume.tex` and `resume.pdf`.
- No AI marks in a resume or cover letter: no hidden characters, look-alike letters or tool metadata
  (`qa.json` → `ai_marks` is empty). Never run the skill's Layer B paraphrase on them; the wording
  stays the registered wording.
- Never label coverage an "ATS score", claim a guaranteed shortlist or hide a failed gate.

## Report

Tier and why, job fit, supported coverage and hard gaps, the signature project and its alignment, all
nine artifact paths, QA (including AI marks) and visual-review status, and facts Annie should confirm
(also appended to `QUESTIONS-FOR-YOU.md`). For 2–10 JDs, or "give me 10 companies", use the `hunt` skill.
