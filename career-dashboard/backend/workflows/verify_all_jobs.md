---
description: Verify saved US postings in Annie's pipeline, re-run the sponsorship gate on their live wording, and never treat a generic careers portal as an active posting.
---

# Verify Active Job URLs

## Scope

Saved and prepared jobs in `data/career.db` (projected to `data/pipeline.md`). Applied, interviewing, rejected and ghosted records are history and are not re-verified.

## 1. The built-in sweep

The dashboard re-checks saved postings daily (`JobQualityService.verify_due`, also `POST /p/<profile>/api/v2/jobs/verify-due`, e.g. `/p/annie/api/v2/jobs/verify-due`). For each posting it records the HTTP result, marks closed or redirected postings expired, and **re-runs the sponsorship gate on the live page text**: a posting whose wording now refuses sponsorship or requires citizenship/clearance moves to Excluded roles with the sentence. A posting Annie already restored after reviewing that same sentence stays.

## 2. The URL skill for anything else

From the repo root (`career` is `.\career.cmd` on Windows, `./career` elsewhere; the skill lives in
`.agents/skills/verify-job-url/`):

```bash
career verify-url \
  --file career-dashboard/data/pipeline.md \
  --delay 8 \
  --output career-dashboard/data/verification-results.json
```

## 3. Manual verification

- `LIKELY_ACTIVE`: still open the page and confirm the title, company, US location, description, sponsorship wording and application route.
- `NEEDS_MANUAL_CHECK`: search the portal for the exact role.
- `EXPIRED` or `BROKEN`: confirm once in a browser before changing anything.

## 4. Re-check eligibility

A live URL is not necessarily suitable: entry level, ≤4 years, one of the four tracks, United States.

## 5. Update

Change records through the dashboard or `backend/scripts/career.py update`; never edit the projections. Keep application history; mark status instead of deleting. Never submit an application.
