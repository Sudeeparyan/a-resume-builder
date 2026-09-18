---
name: verify-job-url
description: >-
  Check whether job listing URLs are still open, expired, broken, or behind a login wall. Use before
  adding roles to a tracker, when refreshing a company list, when a link looks stale, or when asked
  to "verify these jobs", "check if this posting is still live", or "clean up the job list".
  Supports a single URL or batch mode over a Markdown table of listings.
---

# Verify Job URL

Applying to a closed listing wastes the best hour of a job search. Verify before you tailor.

## Usage

```bash
# single URL
python3 system/scripts/verify_job_url.py --url "https://example.com/jobs/1234"

# batch: every [Apply](url) link in a Markdown table
python3 system/scripts/verify_job_url.py --file output/SUMMARY.md --delay 6

# write JSON somewhere specific
python3 system/scripts/verify_job_url.py --file output/SUMMARY.md --output system/data/verify.json
```

The script is stdlib-only by default; it uses `requests` + `beautifulsoup4` when they are installed
(slightly better redirect and text handling) and falls back to `urllib` + a regex tag-stripper when
they are not. No install step is required.

## Statuses

| Status | Meaning | What to do |
|--------|---------|-----------|
| `ACTIVE` | Page loads, no expiry language found | Keep |
| `EXPIRED` | Explicit closure language, or a job URL that redirects to a careers homepage | Remove from the list |
| `BROKEN` | 4xx/5xx, DNS failure, SSL error, timeout | Remove, or find the reposted listing |
| `NEEDS_CHECK` | Login wall (LinkedIn), JS-only page, or a careers homepage rather than a listing | Open it yourself, or use a browser tool |

`NEEDS_CHECK` is not a failure — LinkedIn and Workday deliberately hide content from unauthenticated
requests. Never record such a listing as `ACTIVE` without eyes on it.

## After running

1. Remove `EXPIRED` and `BROKEN` rows from `output/SUMMARY.md`.
2. Update the listing count in the file header and renumber.
3. Move anything already applied to into `system/data/applied-companies.md`.
4. Note the verification date in the file header so the next scan knows how stale the list is.

## Etiquette
Keep `--delay` at 5 seconds or more. This is a personal job search, not a crawler: hammering a
careers site gets your IP blocked and helps nobody.
