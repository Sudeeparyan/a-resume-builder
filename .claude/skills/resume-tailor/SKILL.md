---
name: resume-tailor
description: >-
  Research a company, then tailor Annie's one-page resume to its job description — producing company
  research, an audited LaTeX + PDF resume with a signature project unique to that company, an honest
  match assessment, and a study plan of what to learn before they call. Use WHENEVER a job
  description, job posting, JD, role spec or job link is provided and a resume is the goal, even if
  only the JD text is pasted. Also for "update my resume for this role", "write a cover letter for
  this job", "what should I learn for this company", or "run an ATS check". Uses only facts in
  career-dashboard/data/context/ and its evidence registry — never fabricates experience, metrics
  or skills.
---

# Resume tailor

The app does the mechanics; you do the judgment. `PY` means `career-dashboard/backend/.venv/bin/python`.

## Read first

`career-dashboard/AGENTS.md`, all of `career-dashboard/data/context/`, `data/context/evidence.yml`, and the modes in `career-dashboard/backend/workflows/modes/`: `_shared.md`, `_profile.md`, `evaluate.md`, `deep.md`, `resume.md`, `quality.md`, `upskill.md`.

## Pipeline (run every step)

| # | Step | How | Output |
|---|------|-----|--------|
| 1 | Gates | `workspace.py sponsor-check`, `workspace.py check-reapply`, then save with `career.py add --file <job.json>` | tier or the exclusion sentence |
| 2 | Prepare the folder | `$PY career-dashboard/backend/scripts/career.py prepare JOB_ID` | `data/output/applications/Annie_Manoharan_<Company>_<NN>/` |
| 3 | Evaluate | `modes/evaluate.md` | `evaluation.md` |
| 4 | Research (mandatory) | `modes/deep.md` | `company-research.md` |
| 5 | Evidence map, then tailor | `modes/resume.md`: registry wording, `% EVIDENCE:` tags, signature project no other company owns | `evidence-map.yml`, `resume.tex` |
| 6 | Recruiter audit, three passes | `references/recruiter-audit.md` | the audited resume |
| 7 | One page, validated | Resume Studio → Fit to one page, or `validate_resume.py … --compile`; cut content in order, never fonts/margins | `resume.pdf`, `resume-preview/page-01.png`, `qa.json` |
| 8 | Study plan | `workspace.py run --kind study_plan --job-id JOB_ID` or `modes/upskill.md` | `study-plan.md` |
| 9 | Match assessment + one next step | `modes/_shared.md` → Match assessment | in the chat |

## Hard rules

- Never state a total years of experience; never mention a publication (`PUB-001` is on hold); the ~94% figure stays in the Dräger bullet.
- Never put a study-plan skill or an unbuilt project on the resume, in any wording. Say the wall out loud with every plan.
- A missing requirement is first a "check your memory" question (logged in `QUESTIONS-FOR-YOU.md`), then a gap. Never a guess.
- `[FILL IN: …]` markers are how you ask for a number only Annie knows; the validator refuses to pass a resume that still contains one.
- Always ship both `resume.tex` and `resume.pdf`.
