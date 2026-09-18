---
name: verify-job-url
description: Verify one job URL, or the URLs in Annie's generated pipeline, and classify each as likely active, expired, broken, or needing manual review. Use before adding, refreshing, or acting on a US job lead.
---

# Verify Job URL

Use the bundled script for deterministic HTTP and expiry checks, then manually confirm any role before treating it as active.

## Single URL

```bash
backend/.venv/bin/python .agents/skills/verify-job-url/scripts/verify_job_url.py \
  --url "https://company.example/jobs/123" \
  --output data/verification-results.json
```

## Markdown batch

The parser reads the first URL on each line, so both the generated table in `data/pipeline.md` and checklist lines work:

```text
- [ ] https://company.example/jobs/123 | Example Co | Data Engineer | A | Austin, TX
```

```bash
backend/.venv/bin/python .agents/skills/verify-job-url/scripts/verify_job_url.py \
  --file data/pipeline.md \
  --delay 8 \
  --output data/verification-results.json
```

## Interpret results

- `LIKELY_ACTIVE`: HTTP and page-text checks passed. Manually confirm title, company, US location, description, sponsorship wording and application route.
- `EXPIRED`: closure text, or a redirect from a specific job to a generic careers page.
- `BROKEN`: HTTP or network failure.
- `NEEDS_MANUAL_CHECK`: generic portal, auth wall or too little page evidence.

Liveness does not establish fit. After verification, run the sponsorship gate (`backend/scripts/workspace.py sponsor-check`), the never-re-apply check (`workspace.py check-reapply`) and the role gate in `data/config/profile.yml`: entry level, ≤4 years, United States, one of the four tracks.

Never delete application history; change status through the dashboard or `backend/scripts/career.py update`.
