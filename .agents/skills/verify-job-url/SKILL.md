---
name: verify-job-url
description: >-
  Check whether job listing URLs are still open, expired, broken, or behind a login wall. Use before
  saving or tailoring for a role, when refreshing the job list, when a link looks stale, or when asked to
  "verify these jobs", "check if this posting is still live", or "clean up the job list". Supports one
  URL or every URL in Annie's generated pipeline.
---

# Verify Job URL

Applying to a closed listing wastes the best hour of a job search. Verify before you tailor. The bundled
script makes the deterministic HTTP and expiry checks; then confirm any role by hand before treating it
as active. `career` means `.\career.cmd` on Windows or `./career` on macOS, Linux and Git Bash (it runs
`scripts/verify_job_url.py` in this folder with the app's Python).

## Single URL

```bash
career verify-url --url "https://company.example/jobs/123" --output career-dashboard/data/verification-results.json
```

## Markdown batch

The parser reads the first URL on each line, so both the generated table in
`career-dashboard/data/pipeline.md` and checklist lines work:

```text
- [ ] https://company.example/jobs/123 | Example Co | Data Engineer | A | Austin, TX
```

```bash
career verify-url --file career-dashboard/data/pipeline.md --delay 8 --output career-dashboard/data/verification-results.json
```

## Interpret results

- `LIKELY_ACTIVE`: HTTP and page-text checks passed. Still look at the page: title, company, US
  location, description, sponsorship wording and application route.
- `EXPIRED`: closure text, or a redirect from a specific job to a generic careers page.
- `BROKEN`: HTTP or network failure. Confirm once in a browser before changing anything.
- `NEEDS_MANUAL_CHECK`: generic portal, auth wall or too little page evidence; search the portal for the
  exact role.

Liveness does not establish fit. After verification, run the sponsorship gate
(`career ws sponsor-check`), the never-re-apply check (`career ws check-reapply`) and the role gate in
`career-dashboard/data/config/profile.yml`: entry level, ≤4 years, United States, one of the four tracks.
The dashboard also re-checks saved postings daily and moves any whose wording now refuses sponsorship to
Excluded roles.

Never delete application history; change status through the dashboard or `career update`.
