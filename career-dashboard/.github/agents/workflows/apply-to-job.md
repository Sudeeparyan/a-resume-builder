---
description: "Evaluate one US role and prepare truthful, one-page application materials for Annie after it passes the sponsorship gate, the never-re-apply check and the profile gate. Prepares only; Annie submits."
---

# Apply-to-Job Preparation

This workflow prepares materials. It never submits an application.

## 1. Gate, verify and classify

- Run the sponsorship gate (`backend/scripts/workspace.py sponsor-check --company "<name>" --file <jd.txt>`). EXCLUDED stops here and is recorded with its sentence.
- Run the never-re-apply check (`workspace.py check-reapply --company "<name>" --title "<role>"`).
- Confirm the specific job page is active and in the United States.
- Classify as track A, B, C or D, or out of scope (senior, >4 years, web/full-stack, DevOps/platform).
- Save it through the dashboard or `backend/scripts/career.py add --file <job.json>`, then prepare it (Resume Studio, or `career.py prepare JOB_ID`), which creates `data/output/applications/Annie_Manoharan_<Company>_<NN>/` with the JD snapshot.

## 2. Evaluate

Run `backend/workflows/modes/evaluate.md`: 80+ apply today, 70–79 this week, 55–69 only with manageable gaps shown, below 55 skip. Save `evaluation.md`.

## 3. Research

Run `backend/workflows/modes/deep.md`; save `company-research.md`.

## 4. Tailor

Run `@resume-builder` with Annie's context files, the full JD, the research and `data/templates/resume-base.tex`. It writes `evidence-map.yml` and `resume.tex`, with a signature project no other company owns.

## 5. Validate

- `backend/.venv/bin/python backend/scripts/validate_workspace.py`
- `backend/.venv/bin/python backend/scripts/validate_resume.py <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir <folder>/resume-preview --qa-json <folder>/qa.json`
- Inspect `resume-preview/page-01.png`, then record the visual review through the validator.
- Release only when all nine paths exist: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`.

## 6. Study plan

Run `backend/workflows/modes/upskill.md` (Resume Studio → Write study plan). Say the wall: nothing in it goes on the resume until learned and recorded.

## 7. Optional outreach

Draft with `backend/workflows/linkedin-outreach.md`; never send without explicit authorization.

## 8. Track

After Annie applies, record the real date in the dashboard or with `career.py update JOB_ID --status applied --application-date YYYY-MM-DD`. Twenty-one quiet days later it becomes ghosted automatically; a reply takes it back out. The Markdown trackers are generated; never edit them.
