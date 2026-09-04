---
name: job-hunter
description: >-
  Find, verify, score, and track job openings for the candidate in this workspace, in the markets
  configured in system/config/regions.yml. Use when asked to "find jobs", "search for roles", "what should
  I apply to this week", "scan companies", "refresh the job list", or to check a specific company's
  openings. Reads context/07-preferences.md for what the person actually wants, plus the region pack,
  the tracked-company list, and the already-applied exclusion list;
  scores every result for skill match, competition, eligibility and recency; writes results to
  output/SUMMARY.md, the one page the user reads. Never invents a listing or a link.
---

# Job Hunter

Region-agnostic job discovery. Everything market-specific comes from `system/config/regions.yml`; nothing
about a country or a company is hardcoded in this skill.

## Read first (in order)

1. **`context/07-preferences.md`** — **the search itself**: titles to look for, cities, seniority,
   industries wanted and avoided, salary floor, contract types, **hard limits**, **companies to
   skip**, and the companies whose careers pages to check directly first.
   Plus **`context/01-basics.md`** — right to work is a hard eligibility filter, applied before
   scoring, and **`context/04-projects.md` / `05-skills.md`** — what a real skill match means.
   If `07-preferences.md` is empty, ask the user what they're looking for in plain language and
   write their answers into it yourself. Never guess the search, never tell them to go edit a file.
2. `system/data/applied-companies.md` — **exclusion list. Nothing on it may appear in output.**
3. `system/config/profile.yml` — target titles per track, competition strategy, eligibility
4. `system/config/regions.yml` — job boards, hubs, work-authorisation rules, salary bands for the region
5. `system/config/portals.yml` — tracked career pages, saved searches, filters
6. `system/modes/_shared.md` then `system/modes/_profile.md` — scoring weights (personal overrides win)
7. `output/SUMMARY.md` — what is already there, so you add rather than duplicate

If no region is specified, use `system/config/regions.yml → default_region` and say which one you used.

## Workflow

### 1. Direct career pages first
Walk `tracked_companies` where `enabled: true` and `region` matches. A company's own posting is
fresher and less contested than an aggregator copy, and it avoids agency middlemen.

### 2. Saved searches
Run the `search_queries` for both tracks, substituting tokens from the configs. Add the
graduate/entry queries when `years_professional_experience` is 0–1.

### 3. Filter
Apply `filters` from `system/config/portals.yml`: posting age, excluded title words, years demanded, location
match, applied-list exclusion, agency reposts. Then apply `hard_filters` from `system/modes/_profile.md`.

### 4. Verify every link
Run the `verify-job-url` skill on the survivors. A link you could not verify is `NEEDS_CHECK`,
never `ACTIVE`. Drop anything `EXPIRED` or `BROKEN` before it reaches the tracker.

### 5. Score
Use the weights in `system/modes/_shared.md`: skill match 35, competition 25, eligibility 20, company 10,
recency 10. Eligibility is a gate — a work-authorisation or location fail scores 0 and is listed
separately as "not eligible", not silently dropped, so the same role is not re-surfaced next week.

### 6. Write results
- `output/SUMMARY.md` → **"Companies found, no resume yet"** — the ranked table, newest scan on top
- `output/SUMMARY.md` → **"Considered and skipped"** — anything ruled out, with the one-line reason
- Update the `Last run:` line at the top of `output/SUMMARY.md` every time
- `system/data/scan-history.tsv` — one row per scan: date, region, queries run, found, kept, applied

### 7. Report
Lead with the three highest-scoring roles and one sentence each on why. Then the full table. Then
"considered and skipped" with a one-line reason each.

## Output table

```
| # | Company | Role | Track | Location | Posted | Applicants | Score | Link |
```

Tier 1 = 80+ · Tier 2 = 70–79 · Tier 3 = 55–69 · below 55 goes in the skipped block.

## Quality rules

- **Never invent a listing, URL, company, or applicant count.** Unknown is written as unknown.
- **Never surface a company from the applied list** — in any section, including "considered".
- Prefer the employer's own posting over an aggregator's copy.
- Flag ghost-job signals (see `system/modes/_shared.md`) instead of ranking those roles highly.
- Note the posting date on every row; undated listings are treated as 30+ days old.
- Say plainly when a search returned little. A short honest list beats a padded one.
