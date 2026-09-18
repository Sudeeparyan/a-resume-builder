---
description: "End-to-end single-job workflow: gate, verify, evaluate, research, choose a unique signature project, fit exactly one Letter page, study plan, release only after QA."
---

# Generate Tailored Resume

1. Read `AGENTS.md`, all of `data/context/` and the registry. Visible claims must map to `data/context/evidence.yml`.
2. Run the sponsorship gate and the never-re-apply check (`backend/scripts/workspace.py sponsor-check` / `check-reapply`, or save through the dashboard). Stop on EXCLUDED or blocked, and report the sentence or the rule.
3. Save and hash the full JD as `job-description.md` in `data/output/applications/Annie_Manoharan_<Company>_<NN>/`.
4. Run `backend/workflows/modes/evaluate.md`; save `evaluation.md`; stop out-of-scope roles.
5. Run `backend/workflows/modes/deep.md`; save `company-research.md`.
6. Run `backend/workflows/modes/resume.md`; write the evidence map before any LaTeX.
7. Choose the signature project (unused by other companies, not supporting-only) and one supporting project from `data/context/evidence.yml`.
8. Fit and validate with `backend/scripts/validate_resume.py`: exactly one US Letter page, 10–11pt.
9. Repair evidence-safe content at most three times, cutting in the documented order.
10. Run `backend/workflows/modes/quality.md`, including the visual review of `page-01.png`.
11. Run `backend/workflows/modes/upskill.md`; save `study-plan.md`.
12. Return all nine paths (`job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`) plus the tier, job fit, supported coverage and QA results as separate numbers.

Never submit an application or send outreach without explicit authorization.
