# Mode: Scan — US Job Discovery

Discover current US roles that pass Annie's sponsorship gate, never-re-apply rules and role guardrails.

## Inputs — read `data/context/` first; it is the search query

| From | What it decides |
|------|-----------------|
| `data/context/07-preferences.md` | Titles, alternative titles, locations, seniority, hard limits, companies to skip or to check first |
| `data/context/01-basics.md` | Work authorization (F-1 OPT, authorized now); sponsorship needed later |
| `data/context/04-projects.md`, `05-skills.md` | What a good match means: score against what she actually has |
| `data/config/profile.yml` | Tracks A–D and their signals, `max_years_required: 4`, US hubs |
| `data/config/portals.yml` | Tracked companies with their ATS (Greenhouse/Lever/Ashby) and search queries |
| `data/config/regions.yml` | US hubs and remote wording |

If a preference is still open (see `QUESTIONS-FOR-YOU.md`), ask Annie in plain language and offer to record her answer; do not guess.

## Process

For a requested count, keep scanning past exclusions, duplicates, expired postings and inaccessible pages until that many verified eligible jobs are found or the search is honestly exhausted.

### 1. Tracked career pages first (no AI needed)

Daily Search → mix *Tracked career pages*, or `backend/scripts/workspace.py run --kind discovery --preset portals`. This reads the public Greenhouse/Lever/Ashby feeds for every enabled company in `portals.yml`, runs the relevance screen, the sponsorship gate and the re-apply check, and saves up to today's remaining target. Employer postings beat aggregator copies.

### 2. Configured queries

Default discovery (`--preset default`) or *Balanced five* runs the AI search worker with `backend/workflows/agents/job-discovery.md`: US only, the four tracks, entry level, and the posting's own sponsorship/citizenship/clearance wording quoted verbatim as `restriction_quote`. Search results are leads; open the specific employer or ATS page before inclusion.

### 3. The gates, in order

1. **Sponsorship**: explicit refusal or citizenship/clearance/ITAR/EAR/permanent-residency requirement → EXCLUDED, logged with the sentence. Silence is not a negative.
2. **Never re-apply**: same company + role ever, company rejected within 180 days, ghosted company within 90 days.
3. **Role fit**: four tracks, entry level, ≤4 years, United States (or Remote US). Reject Senior/Staff/Lead/Principal/Manager titles, web/full-stack and DevOps/platform roles, and "data" titles whose duties are not data engineering.

### 4. Liveness

The specific page must show the role, company, US location, description and an active application route. Generic portals stay `NEEDS_MANUAL_CHECK`. Undated postings count as 30+ days old.

### 5. Deduplicate

Posting identity (URL and requisition ID) and the re-apply memory in `data/career.db` are the dedupe; `data/pipeline.md` and the trackers are projections of the same data.

## Output

Save eligible jobs through the dashboard, `workspace.py`, or `backend/scripts/career.py add --file <job.json>` (all three run the gate and the re-apply check). Never write the Markdown projections.

Report counts: scanned, excluded by the sponsorship gate (with their sentences), blocked by re-apply rules, out of scope, expired/broken, duplicate, needs manual check, newly saved. Rank saved jobs by tier (S → A → B → C), then score. `data/output/SUMMARY.md` refreshes itself.

## Rules

- Never invent a listing, a URL or an applicant count. Unknown means unknown.
- Never surface a company or role the re-apply memory blocks, or anything on her skip list.
- H-1B history, E-Verify and cap-exempt status rank; they never exclude.
- "Must be authorized to work in the US" never excludes: she is authorized.
