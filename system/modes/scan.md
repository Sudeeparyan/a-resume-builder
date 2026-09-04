# Mode: scan — discover new openings

## 0. Read `context/` first — it *is* the search query

A job scan is not a generic search. Before you type a single query, read `context/` and build the
search out of it. Then read `system/config/regions.yml`, `system/config/portals.yml`,
`system/config/profile.yml`, and `system/data/applied-companies.md`.

| From `context/` | What it decides |
|-----------------|-----------------|
| `07-preferences.md` → titles, alternative titles | The exact search terms |
| `07-preferences.md` → cities, remote/hybrid, relocation | The location filter |
| `07-preferences.md` → industries wanted / avoided | Which results survive |
| `07-preferences.md` → seniority | The level filter — never surface roles above or below it |
| `07-preferences.md` → target salary, minimum | Drop or flag anything below the stated minimum |
| `07-preferences.md` → **hard limits** | Absolute exclusions. Nothing matching them appears, at any score |
| `07-preferences.md` → **companies to skip** | Absolute exclusions |
| `07-preferences.md` → **companies they'd love to work for** | Check these careers pages **first and directly** — roles appear there days before the job boards |
| `01-basics.md` → right to work, sponsorship needed | A hard eligibility filter, applied before scoring |
| `04-projects.md`, `05-skills.md` | What "a good match" means — score against what they actually have |

If `context/07-preferences.md` is still empty, **ask the user what they're looking for in plain
language** and offer to write their answers into it. Do not guess a search from the profile alone,
and do not tell them to go and edit the file.

## Procedure
1. **Exclusions first.** Load `system/data/applied-companies.md` plus the hard limits and companies-to-skip from
   `context/07-preferences.md`. Nothing on those lists may appear in the output, in any section.
2. **Direct career pages.** Walk the companies named in `context/07-preferences.md`, then
   `tracked_companies` where `enabled: true`. These beat aggregators.
3. **Saved searches.** Run `search_queries` for both tracks, substituting the titles and locations
   from `context/07-preferences.md` and the tokens from the configs.
4. **Filter** with `filters` in `system/config/portals.yml`: age, title words, years demanded,
   location, agency reposts — then again against the user's hard limits.
5. **Verify** every surviving link with the `verify-job-url` skill before it reaches the tracker.
   A listing that cannot be verified is marked `NEEDS_CHECK`, never `ACTIVE`.
6. **Score** each with the `system/modes/_shared.md` weights, scoring skill match against
   `context/`, not against the role's ideal candidate.
7. **Write** results into `output/SUMMARY.md` — ranked rows under **"Companies found, no resume
   yet"**, everything ruled out under **"Considered and skipped"** with its reason, and update the
   `Last run:` line. That one page is what the user actually reads.
8. **Log** the scan in `system/data/scan-history.tsv`.

## Output format
Ranked table: `# | Company | Role | Track | Location | Posted | Applicants | Score | Link`.
Group into Tier 1 (score 80+), Tier 2 (70–79), Tier 3 (55–69). Anything under 55 is listed in a
short "considered and skipped" block with a one-line reason each — that record stops the same role
being re-surfaced next week.

## Rules
- Never invent a listing, a URL, or an applicant count. Unknown means unknown.
- Never include a company from `system/data/applied-companies.md` or from the user's skip list.
- Never surface a role that breaks a hard limit in `context/07-preferences.md`, however well it scores.
- A role the user is not eligible for (work authorisation, location) scores 0 and is listed
  **separately with the reason** — never silently dropped, and never presented as viable.
- Prefer the employer's own posting over an aggregator copy of it.
- Note the posting date for every row; undated listings are treated as 30+ days old.
