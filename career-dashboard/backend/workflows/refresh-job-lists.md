---
description: "Refresh Annie's US job pipeline: re-verify saved postings, re-run the sponsorship gate on their live wording, and add new eligible roles."
---

# Refresh US Job Data

`data/career.db` is authoritative; `data/pipeline.md`, `data/application-tracker.md`, `data/applied-companies.md` and `data/output/SUMMARY.md` are generated projections.

1. Read `AGENTS.md`, `data/config/profile.yml` and `backend/workflows/modes/_shared.md`.
2. Run the posting sweep (`POST /p/<profile>/api/v2/jobs/verify-due`, e.g. `/p/annie/api/v2/jobs/verify-due`, or leave it to the daily scheduler): expired and redirected postings are marked, and any posting whose live wording now refuses sponsorship moves to Excluded roles with the sentence.
3. Confirm doubtful results with the `verify-job-url` skill and a browser check.
4. Re-run the role gate; remove mismatched leads from the saved list (recoverable removal, never deletion of application history).
5. Scan tracked career pages (`workspace.py run --kind discovery --preset portals`) and the configured searches for new eligible US roles; every lead passes the gate and the re-apply check.
6. Report checked, active, expired, newly excluded (with sentences), mismatched, duplicate and newly saved counts.
