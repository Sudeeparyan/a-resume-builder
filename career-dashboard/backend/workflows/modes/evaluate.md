# Mode: Evaluate — Job Fit

Evaluate one job description or URL against Annie's real professional, research and project evidence. Read `_shared.md` and `_profile.md` first.

## Step 0 — The gates (in this order)

1. **Sponsorship gate.** `backend/scripts/workspace.py sponsor-check --company "<name>" --file <jd.txt>`. `EXCLUDED` stops here: record it (the sentence is logged, the posting goes to Excluded roles) and report `EXCLUDED — the posting says: "<sentence>"`. Otherwise note the tier (S/A/B/C) and why.
2. **Never re-apply.** `workspace.py check-reapply --company "<name>" --title "<role>"`. Blocked stops here with the rule (`same_role`, `rejected_180`, `ghosted_90`).
3. **Role fit.** Classify the job as track A (Data / Analytics Engineering), B (ML / AI), C (Software) or D (Embedded / Test Automation), or `SKIP — outside Annie's profile` for senior titles, >4 years required, non-US location, web/full-stack or DevOps/platform roles.

## A. Role summary

| Field | Value |
|------|-------|
| Company | |
| Role | |
| Track | A / B / C / D |
| Sponsorship tier | S / A / B / C, with the reason (cap-exempt signal, "says it sponsors" sentence, H-1B approvals, or silent) |
| Seniority / years asked | |
| Location / arrangement | US city, or Remote (US) |
| Posting status | Active / Needs manual check / Expired |
| Eligibility | Pass / Conditional / Excluded |

## B. Evidence match

Read `data/context/evidence.yml` and the numbered context files. Normalize each distinct JD requirement:

| Requirement ID | Required/preferred | Job requirement | Evidence ID(s) | Annie's evidence | Evidence type/status | Strength |
|---|---|---|---|---|---|---|
| R01 | Required | Streaming pipelines (Kafka/Flink) | `PROJ-P01-IOT`, `SKILL-STREAMING-001` | Sub-second Kafka/Flink SQL/ClickHouse platform | Candidate project | Strong |
| R02 | Required | AWS data pipelines | `EXP-INSOPS-001`, `SKILL-CLOUD-001` | Glue, Lambda, EMR, Airflow, S3 | Professional (internship) | Strong |
| R03 | Preferred | Kubernetes | None | Not in the bank | — | Gap → study plan |

For each gap say whether it is a blocker, manageable, or nice-to-have, and first ask whether she has done it ("check your memory"). Never turn coursework into professional experience or lab research into a side project.

**Supported requirement coverage** is separate from job priority: required weight 3, preferred weight 1; strong credit 1.0, partial 0.5, gap or held 0. Report the weighted percentage with blockers. It is an evidence diagnostic, not an ATS score or a shortlist prediction.

## C. Seniority and competition

- Years asked versus her dated roles (never compute or state a total).
- New-grad / entry-level / Engineer I wording.
- Applicant count, posting age, reposts, agency in between.
- Uncommon combinations she has (Flink event-time, LabVIEW + Python V&V, FPGA plus data) that thin the field.

## D. Location and work requirements

Report only what the posting says: US location and arrangement, the exact sponsorship/authorization wording (quote it), E-Verify mentions (matter for STEM OPT). Do not give immigration conclusions.

## E. Tailoring plan

- the track and section order (A/C Experience first; B/D Projects first);
- skill ordering and which conditional skills are allowed with the chosen projects;
- which registered bullets to lead with;
- the signature project (unused by other companies) and the supporting project, with reasons;
- JD keywords to avoid because they are not in the bank.

## F. Interview exposure

Three to five likely questions and the stories from `data/interview-prep/story-bank.md` that answer them. Name any question with no story behind it; that goes into the study plan.

## Decision

Apply the weights in `_shared.md`, rank by tier first, then return:

- 80–100: APPLY TODAY
- 70–79: APPLY THIS WEEK
- 55–69: CONDITIONAL
- Below 55: SKIP (record why)

Also return the supported-requirement coverage and hard gaps. Never average it with artifact QA.

Save the evaluation as `evaluation.md` in the application folder: gates and tier, eligibility decision, job-fit score, requirement IDs, evidence mappings, coverage, blockers and tailoring plan. Record real application status through the dashboard or `backend/scripts/career.py update`. Evaluation alone never authorizes an application.
