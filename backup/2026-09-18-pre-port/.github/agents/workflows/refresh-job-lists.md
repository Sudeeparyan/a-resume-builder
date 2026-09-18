---
description: "Every 2–4 weeks: verify every tracked link, prune dead listings, and add newly discovered companies."
---

# Workflow: refresh job lists

Job lists rot fast. A list older than a month is mostly closed listings.

## 1. Verify
```bash
python3 system/scripts/verify_job_url.py --file output/SUMMARY.md --delay 6 \
  --output data/verify-<region>-$(date +%F).json
```

## 2. Prune
- Remove `EXPIRED` and `BROKEN` rows
- Open every `NEEDS_CHECK` yourself (login walls and JS-rendered pages cannot be auto-verified)
- Renumber, update the count and the "verified on" date in the file header

## 3. Extend
- Add companies discovered since the last refresh to `system/config/portals.yml` with an honest `why`
- Check whether any tracked company has changed ATS (a dead careers URL usually means they moved to
  Greenhouse/Ashby/Workday — find the new one rather than dropping the company)
- Review tiering: a company that never replies drops a tier; one that replied fast rises

## 4. Prune the config too
Disable (`enabled: false`) rather than delete companies that have gone quiet — the record of having
tried them is worth keeping.
