---
description: "Weekly routine: discover new openings, verify links, score, and queue the week's applications."
---

# Workflow: weekly job scan

Run once a week — Monday morning works best, since most postings go live Monday–Tuesday and
applying in the first 48 hours materially changes the odds.

## 1. Scan
Run the `job-hunter` skill (or `@job-hunter`) for each configured region. It follows `system/modes/scan.md`:
career pages first, then saved searches, then filters, verification, and scoring.

## 2. Triage into three buckets
- **Apply now (80+)** — target 3–5 per week. More than that and the tailoring gets thin.
- **Apply if time (70–79)** — the backlog for a quiet evening.
- **Watch** — good company, wrong role or wrong timing. Note what would change the answer.

## 3. Run the application workflow
For each "apply now", run `.github/agents/workflows/apply-to-job.md`. Five well-tailored applications beat thirty generic
ones; the tracker will show it within a month.

## 4. Housekeeping
- Move anything applied to into `applied_companies.md`
- Update statuses on rows older than 14 days
- Append the scan to `system/data/scan-history.tsv`
- Roll up the numbers in `system/data/pipeline.md`

## 5. Review the numbers monthly
Applications sent, replies, interviews, offers — and the conversion rate between each pair. A reply
rate under 5% means the resume or the targeting is wrong, not that the market is bad. Check, in
order: is the track classification right, are the must-haves actually being matched, and is the
resume reaching a human at all (direct portal vs aggregator).
