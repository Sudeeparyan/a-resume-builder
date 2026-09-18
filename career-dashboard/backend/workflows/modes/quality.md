# Mode: Quality — Resume Release Gate

Artifact QA is binary. It is never averaged with job fit or supported requirement coverage.

The release folder must contain exactly these artifact paths: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`.

## Automated hard gates

Run `backend/scripts/validate_resume.py` and require:

- LaTeX compiles without an overfull box or unresolved reference warning.
- The PDF is **exactly one US Letter page** (612 × 792 pt).
- The fixed `letterpaper,10pt` class, geometry and line spacing are unchanged; no `\newpage` or `\clearpage`; Studio layouts stay within 10–11pt.
- One signature project and one distinct supporting project, both registered and resume-ready, rendered with their registry wording.
- Every content line has a `% EVIDENCE:` tag naming known, non-held IDs.
- Every percentage on a line appears in the approved wording of that line's evidence tags (the ~94% figure only in the Dräger bullet).
- No unresolved placeholders, visible evidence IDs, banned filler, never-claim skills, years-of-experience totals, publication words, GPA, certification or LinkedIn claims, or the superseded InsOps data-science framing.
- Header shows name, phone, email, portfolio and GitHub exactly as registered; every printed employer or degree carries a registered title/date line.
- Every visible number comes from registered wording.
- PDF metadata author is Annie Prasanna Manoharan; the PDF is at least as new as its source.

## Evidence review

The evidence map must show the candidate revision and JD snapshot hash, one mapping per normalized requirement, all resume claim IDs, no held claims, the signature project and its reason, ownership wording preserved, and the company-problem source, date, confidence and explicit/inferred label.

Reject when a JD keyword became an unsupported skill, a study-plan item reached the page, a team result became individual ownership, lab research became a side project, or an intern title was upgraded.

## Manual visual gate

Inspect `resume-preview/page-01.png` for clipping, overlap, tiny text, crowded contact details, orphan headings, split entries, unbalanced blank space (Studio fits aim for at least 80% fill) and readable hierarchy.

Then rerun validation with `--visual-review pass --visual-reviewer "{identity}"`. Never edit `qa.json` by hand; the manifest binds the reviewer and timestamp to the PDF and the preview hash.

## Release result

Return either:

- `PASS — release-ready`, with artifact paths; or
- `FAIL — do not use`, with the exact failures and the next evidence-safe repair.
