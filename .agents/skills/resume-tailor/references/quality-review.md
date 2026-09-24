# Quality review: fail-closed, one tailored resume

Read `career-dashboard/AGENTS.md`, `data/context/evidence.yml`, `backend/workflows/modes/quality.md`,
and the folder's JD, `evaluation.md`, research, study plan, evidence map and LaTeX. Confirm that:

- MiGa and DualFit read as AICV Lab research;
- InsOps stays a Data Engineering Intern role;
- the ~94% figure appears only in the Dräger bullet;
- nothing from `study-plan.md` reached the page;
- no years total, publication, GPA, certification or LinkedIn appears;
- there is a unique signature project plus one supporting project, on exactly one US Letter page.

Run automated QA first (`career` is `.\career.cmd` on Windows, `./career` elsewhere):

`career check-resume {folder}/resume.tex --compile --output {folder}/resume.pdf --render-dir {folder}/resume-preview --qa-json {folder}/qa.json`

Then confirm `{folder}/resume-preview/` holds exactly `page-01.png`, look at it, and rerun with the review
recorded:

`career check-resume {folder}/resume.tex --compile --output {folder}/resume.pdf --render-dir {folder}/resume-preview --qa-json {folder}/qa.json --visual-review pass --visual-reviewer "{reviewer identity}"`

Never edit computed QA fields by hand; the final run binds the reviewer, timestamp, PDF hash and preview
hash.

Return `PASS — release-ready` only when every automated and manual gate passes. Otherwise
`FAIL — do not use` with the exact failures. Do not waive a gate or rewrite candidate claims; send
content problems back to the tailoring step.
