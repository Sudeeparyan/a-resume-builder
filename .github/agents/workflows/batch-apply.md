---
description: "Batch: find N verified the United States openings, then research, tailor, audit and plan one application per company in a single pass — N resumes with N different signature projects, plus a study plan each. Trigger with 'give me N companies this week + resumes' or 'find N <field> roles in the United States and tailor each'."
---

# Workflow: batch apply (N companies → N resumes)

This is the headline flow. One request → a shortlist of live, verified the United States jobs, **and** for
each one: company research, a tailored and audited resume carrying a **signature project unique to
that company**, and an upskilling plan for the weeks before they call. Follow `system/modes/batch.md`
exactly; this file is the Copilot entry point.

Ten companies means ten genuinely different resumes — not one resume with the name swapped.

## When to run
The user asks for **multiple jobs and their resumes together**, e.g.:
- "give me the latest 10 companies this week with working links"
- "find 10 data roles in the United States and tailor my resume for each"
- "10 companies + 10 resumes"

If they ask only for a *list* of companies (no resumes), run the plain `job-hunter` scan instead and
offer to tailor afterwards.

## Steps
1. **Read `context/` first** — every file plus `context/files/`. `07-preferences.md` *is* the search
   (titles, cities, seniority, salary floor, hard limits, companies to skip, companies to check
   directly); `01-basics.md` right-to-work is a hard eligibility filter; `04-projects.md` is the bank
   the ten distinct signature projects come from. Then the config: `system/config/profile.yml`,
   `system/config/regions.yml` (the United States), `system/config/portals.yml`, `system/modes/_shared.md`,
   `system/modes/_profile.md`, `system/profile/master-profile.md`,
   `system/data/applied-companies.md`. If `master-profile.md` has `{{TOKEN}}`s, stop and run
   `profile-intake`; if `context/` is empty too, offer to interview the user and fill it for them.
2. **Run `system/modes/batch.md`** — scan → verify every link → score → then, per company: research
   (`system/modes/deep.md`) → tailor → assign a **distinct signature project** (§4b) → recruiter audit
   (`references/recruiter-audit.md`) → upskilling plan (`system/modes/upskill.md`).
3. **Deliver** the single combined table (company · role · score · **verified apply link** · resume
   file · signature project · plan) + the "Check your memory" list + the top five things to study
   this week from `output/SUMMARY.md`, and append rows to `output/SUMMARY.md`.

## Guardrails
- Every apply link is verified live; unverifiable links are excluded, not guessed.
- No company from `applied_companies.md` appears.
- No fabricated resume facts — missing must-haves go under "Check your memory" so the candidate can
  add them and re-run.
- **One distinct signature project per company**, tracked in `system/data/signature-projects.md`. If
  the project bank runs out of strong matches before the companies do, say so plainly and propose
  build-now projects — never quietly reuse one, and never put an unbuilt project on a resume.
- **Nothing from an upskilling plan reaches a resume.** Those are the gaps to close during the
  three-to-six-week wait, not claims to make today.
- You prepare applications; the candidate reviews and submits each one.

## After the batch
Point the user at `.github/agents/workflows/apply-to-job.md` for the per-application submit + track +
follow-up steps, and remind them to move each company into `applied_companies.md` the day they apply.
