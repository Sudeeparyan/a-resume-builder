---
name: verify-job-url
description: >-
  Check whether job listing URLs are still open, expired, broken, or behind a login wall. Use before
  saving or tailoring for a role, when refreshing the job list, when a link looks stale, or when
  asked to "verify these jobs", "check if this posting is still live", or "clean up the job list".
  Supports one URL or every URL in Annie's generated pipeline.
---

# Verify Job URL

Applying to a closed listing wastes the best hour of a job search. Verify before you tailor. The script and full guide live in the app: `career-dashboard/.agents/skills/verify-job-url/`.

```bash
career-dashboard/backend/.venv/bin/python career-dashboard/.agents/skills/verify-job-url/scripts/verify_job_url.py --url "https://company.example/jobs/123"
career-dashboard/backend/.venv/bin/python career-dashboard/.agents/skills/verify-job-url/scripts/verify_job_url.py --file career-dashboard/data/pipeline.md --delay 8 --output career-dashboard/data/verification-results.json
```

`LIKELY_ACTIVE` still needs a look at the page (title, company, US location, sponsorship wording, apply route). `NEEDS_MANUAL_CHECK` means search the portal for the exact role. `EXPIRED`/`BROKEN`: confirm once in a browser before changing anything. The dashboard also re-checks saved postings daily and moves any whose wording now refuses sponsorship to Excluded roles.
