---
name: job-hunter
description: >-
  Find, verify, sponsorship-screen, score and track US job openings for Annie. Use when asked to
  "find jobs", "search for roles", "what should I apply to this week", "scan companies", "refresh
  the job list", "give me 10 jobs", or to check a specific company's openings. Reads context/ for
  what she actually wants, applies the hard sponsorship gate, checks the tracker so an already-applied
  or already-rejected company is never surfaced again, and writes results to output/SUMMARY.md.
  United States only. Never invents a listing or a link.
---

# Job hunter

## Read first, in this order

1. `context/01-basics.md` — work authorization. She is on **active F-1 OPT** and **is authorized
   to work now**.
2. `context/07-preferences.md` — the search query itself: titles, seniority, the sponsorship rule.
3. `context/05-skills.md` — what "a good match" means. Score against what she has, not the ideal.
4. `system/config/portals.yml` — tracked companies and search queries.
5. `system/config/regions.yml` — the US pack: boards, hubs, cap-exempt categories.
6. `system/config/sponsorship.yml` — the gate.
7. `system/modes/_shared.md` then `_profile.md` — scoring. `_profile.md` wins.

## Step 0 — exclusions, before anything else

```
python system/scripts/track.py --age          # flip 21-day-silent applications to GHOSTED
python system/scripts/track.py --exclusions   # what must never be surfaced
```

Nothing on that list appears in the output. Not in the shortlist, not in "considered", nowhere.

## Step 1 — discover

Work down this list. Direct sources first: a company's own posting is fresher and less contested
than an aggregator copy.

### a. Tracked companies, direct
Walk `tracked_companies` in `portals.yml` where `enabled: true`. **Cap-exempt entries first.**
Where a company has an `ats` token, hit the public JSON API — no auth, no scraping:

- Greenhouse: `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
- Lever: `https://api.lever.co/v0/postings/{company}?mode=json`
- Ashby: `https://api.ashbyhq.com/posting-api/job-board/{company}`

### b. Indeed — the primary volume channel
```
mcp__claude_ai_Indeed__search_jobs(search="<title>", location="<hub or 'remote'>",
                                   country_code="US", job_type="fulltime")
```
Run it once per target title from `context/07-preferences.md`, across Remote plus the hubs.
Aim for ~1.5× the number of roles she asked for, because the gate will cut some.

### c. Cap-exempt sweep — do not skip this
Run the `cap_exempt` queries in `portals.yml`. Universities, national labs, nonprofit research
institutes and academic medical centers file H-1B **year-round with no lottery**. Aggregators index
these poorly, so they need their own pass.

### d. The sponsorship-positive queries
Run the `sponsorship_positive` queries. Postings that say "visa sponsorship available" are
uncommon and convert far better than anything else in the list.

## Step 2 — get the full job description

For every candidate role:
```
mcp__claude_ai_Indeed__get_job_details(job_id="<id>")
```
or fetch the ATS posting. **You need the full text**, not the search-result summary — it feeds both
the gate and the tailoring step. Save it to `job-description.txt` in the application folder.

## Step 3 — the sponsorship gate (hard)

```
python system/scripts/sponsor_check.py --jd <jd.txt> --company "<name>" --json
```

| Verdict | Meaning |
|---|---|
| `EXCLUDED` / `no_sponsorship` | Posting explicitly refuses to sponsor. **Drop it.** |
| `EXCLUDED` / `cannot_hire` | Citizenship, clearance, ITAR/EAR, or permanent residency required. **Drop it.** |
| `KEEP` tier `A` | Posting explicitly offers sponsorship. Rank top. |
| `KEEP` tier `S` | Cap-exempt employer. Rank top. |
| `KEEP` tier `B` | Proven H-1B sponsor, posting silent. |
| `KEEP` tier `C` | Silent, no record. **Keep it.** This is the normal case and the largest bucket. |

**Do not over-filter.** "Must be authorized to work in the United States" is not a refusal — she
is authorized. Only an explicit refusal counts.

**Absence of H-1B history never excludes.** Most employers never appear in USCIS data, and many
sponsor once a candidate has cleared the interviews.

Every exclusion gets logged in `SUMMARY.md` with **the sentence that triggered it**, so a wrong
exclusion is visible and can be overridden.

## Step 4 — verify the link is live

```
python system/scripts/verify_job_url.py --url "<url>"
```
`EXPIRED` or `BROKEN` → drop it. Never publish a link you have not checked.

## Step 5 — score

Weights from `_shared.md`, with `_profile.md` overrides. Eligibility is now a **gate in Step 3**,
not a weight — redistribute it across skill match and competition.

Then order by sponsorship tier first, score second: **S → A → B → C**.

Tiers: 80+ apply today · 70–79 this week · 55–69 only if competition is low · below 55 skipped
with a one-line reason.

## Step 6 — write it up

Update `output/SUMMARY.md`:

- `Last run:` — what you did, when, how many found/kept/excluded
- **Your resumes** — one row per prepared application
- **Pipeline** — what's out, how long it's been quiet, what needs a nudge
- **Companies found, no resume yet** — the ranked shortlist, links verified
- **Excluded** — company, role, and the triggering sentence
- **What to study this week**

Append one row per scan to `system/data/scan-history.tsv`.

## Step 7 — record what you prepared

```
python system/scripts/track.py --add --company "X" --role "Y" --url "..." \
    --tier B --score 82 --track track_a --folder Annie_Manoharan_X_01
python system/scripts/track.py --sync-applied-companies
```

## Output table

| # | Company | Role | Tier | Score | Location | Posted | Apply |
|---|---------|------|------|-------|----------|--------|-------|

Follow it with the honesty line from `sponsorship.yml → disclaimer`, every time.

## Rules

- **Never invent a listing, a company, or a URL.** If you could not verify it, it does not ship.
- **Never surface anything on the exclusion list**, in any section.
- **Never exclude for a reason other than the two in Step 3.** No silent drops.
- **US only.** A non-US role is not searched for, not ranked, not listed as skipped.
- **Log every exclusion with its triggering sentence.** She must be able to see and overrule it.
- **Cap-exempt employers rank first**, whatever track they belong to.
- If a scan returns fewer than asked, say so plainly and say why. Do not pad the list with roles
  that failed the gate or repeat companies already in the tracker.
