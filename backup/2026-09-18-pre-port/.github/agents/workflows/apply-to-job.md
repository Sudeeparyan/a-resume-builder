---
description: "End-to-end workflow for one application: evaluate → research → tailor → build → submit → track → follow up."
---

# Workflow: apply to a job

Run this when you have a specific JD and intend to apply.

## 1. Evaluate before spending effort
Run `system/modes/evaluate.md` on the JD. It produces blocks A–F and a priority score.

| Score | Do |
|-------|-----|
| 80+ | Continue, and run deep research at step 2 |
| 70–79 | Continue |
| 55–69 | Continue only if competition is low or the company is a genuine personal fit |
| < 55 | Stop. Record the reason in the tracker so it is not re-surfaced |

An eligibility failure (work authorisation, location, language, licence) stops here regardless of
skill match.

## 2. Deep research (every JD, not only 80+)
Run `system/modes/deep.md`. Save to `output/NN_Company_Role/research.md`. Cover what they build, what they actually run,
**where they are going next**, and what this hire will really do in months 1–3. Finish with the
skills demand map (§6), which sorts every named skill into resume / upskilling plan / honest gap.
The findings drive the signature project, the Projects reframe, and the cover letter's opening.
A shorter version is fine for a low scorer; skipping it is not.

## 3. Tailor, audit, and plan
Run the `resume-tailor` skill (or `@resume-builder`) with the JD. It produces all four:
- `output/NN_Company_Role/resume.tex` — the **post-audit** resume, carrying one signature project
  chosen for this company alone (registered in `system/data/signature-projects.md`)
- the **recruiter audit** shown inline — score before and after, red flags fixed, ATS verdict,
  yes/maybe/no pile, and any `[FILL IN]` numbers it needs from you
- `output/NN_Company_Role/study-plan.md` — what to learn before they call, in three tiers, plus the
  signature project's defence brief
- `output/NN_Company_Role/job-description.txt` — the JD exactly as it was when you applied
- `output/NN_Company_Role/cover-letter.md` if the application takes one

## 4. Check
```bash
python3 system/scripts/ats_check.py --resume output/NN_Company_Role/resume.tex --jd output/NN_Company_Role/job-description.txt
```
Fix anything under-covered, then build:
```bash
bash system/scripts/build_pdf.sh output/NN_Company_Role/resume.tex
```
Read the PDF once, end to end. Check: dates consistent, no `{{TOKEN}}` survived, no orphaned line
on the last page, links clickable, filename `Firstname_Lastname_RoleTitle.pdf`.

## 5. Submit
Apply on the company's own portal where one exists — it routes to the hiring team rather than a
recruiter's queue. If the portal has a free-text "why this role" box, paste the cover letter's
middle two paragraphs rather than leaving it empty.

## 6. Track
Add the row to `output/SUMMARY.md`: date, company, role, track, resume version, source,
score, status 🟡 Applied, follow-up date (+7 days).
Add the company to `system/data/applied-companies.md` so the hunter stops surfacing it.

## 7. Use the wait
The 3–6 weeks between applying and a first call is the most usable time in the whole process. Work
`output/NN_Company_Role/study-plan.md`: Tier 1 in the first fortnight, Tier 2 next, and re-read the
signature project's defence brief before any scheduled call.

When a proof artefact or a build-now project gets finished, tell the assistant — it appends the
project to `system/profile/master-profile.md`, ticks the item off `context/QUESTIONS-FOR-YOU.md`, updates
`system/data/signature-projects.md`, and can regenerate this company's resume with the new project in
the signature slot. Applications stay open for weeks; a rebuilt resume is often still worth sending.

Across several live applications, `output/SUMMARY.md` answers "what do I study first" —
the skill wanted by the most of them.

## 8. Follow up
- **Day 7:** if a hiring manager or recruiter is findable, one short message: role, one line on the
  strongest match, a link to work if any.
- **Day 14:** no reply → status 🔴 No response. Do not chase a third time.
- **Any reply:** update the status the same day; move to `interview-prep` if it is an interview.
