---
description: Find lower-competition US opportunities that truthfully match Annie's data, ML/AI, software and embedded profile and pass the sponsorship gate.
---

# Find Lower-Competition Opportunities

## 1. Load the rules and history

Read `AGENTS.md`, `data/config/profile.yml` (`competition_strategy`), `data/config/sponsorship.yml` and `data/context/07-preferences.md`. The never-re-apply memory and the excluded log live in `data/career.db`; check a lead with `backend/scripts/workspace.py check-reapply`.

## 2. Where competition is thinner for her

- **Cap-exempt employers (tier S)**: universities, academic medical centers, national labs, nonprofit research institutes. No H-1B lottery; many research-engineer and data roles.
- Postings that explicitly offer sponsorship (tier A).
- Companies under 200 employees; postings under 7 days old.
- Medical-device and health-tech employers (the Soliton/Dräger test automation and the ventilator-telemetry streaming project).
- Embedded / test-automation roles (the least contested track).
- Roles needing a combination she has: Flink event-time semantics, LabVIEW + Python V&V, FPGA plus data.

Reject senior titles, >4 years, non-US locations, web/full-stack and DevOps/platform roles.

## 3. Validate and score

For every lead: open the specific page; confirm title, company, US location, description and application route; run the sponsorship gate (quote any restrictive sentence); run the re-apply check; score with `backend/workflows/modes/_shared.md`; record applicant counts only when visible. Excluded, expired, inaccessible and duplicate leads do not consume a requested count.

## 4. Report

```markdown
# Lower-Competition Opportunities — YYYY-MM-DD

| Company | Role | Track | Tier | Posting age | Applicant evidence | Fit | Priority |
|---------|------|-------|------|-------------|--------------------|-----|----------|
```

Explain each fit using only registered evidence. Save verified roles through the dashboard or `backend/scripts/career.py add --file <job.json>`, both of which run the gate.
