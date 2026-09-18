---
description: "Weekly scan for verified entry-level US data, ML/AI, software and embedded/test roles for Annie that pass the sponsorship gate and the never-re-apply rules."
---

# Weekly US Job Scan

## 1. Load profile and history

Read `AGENTS.md`, `data/context/07-preferences.md`, `data/config/profile.yml`, `data/config/portals.yml` and `data/config/sponsorship.yml`. The re-apply memory and excluded log live in `data/career.db`.

## 2. Discover

1. Tracked career pages first: `backend/scripts/workspace.py run --kind discovery --preset portals`.
2. Then the configured searches across all US hubs and Remote (US), four tracks, entry level.

## 3. Gate and exclude

- Sponsorship: explicit refusal or citizenship/clearance/ITAR/EAR/permanent-residency requirement → EXCLUDED, logged with the sentence.
- Never re-apply: same company and role; rejected within 180 days; ghosted within 90 days (different role only after).
- Role: senior titles, >4 years, non-US, web/full-stack and DevOps/platform roles are out.

## 4. Validate

Open the specific page; confirm title, company, US location, description, date when shown and an active application route. Flag generic portals for manual review.

## 5. Rank

Tier first (S → A → B → C), then the score in `backend/workflows/modes/_shared.md`. Show evidence type and gaps.

## 6. Save and report

Save verified leads through the dashboard or `backend/scripts/career.py add --file <job.json>` (both run the gate). Never apply, contact anyone or change application status without authorization.

Report: pages scanned, eligible roles, excluded by the gate (with sentences), blocked by re-apply rules, role mismatches, expired/broken pages, duplicates, manual checks, newly saved. `data/output/SUMMARY.md` refreshes itself.
