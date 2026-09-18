# System rules — shared

<!-- ============================================================
     THIS FILE IS GENERIC AND AUTO-UPDATABLE. No personal data here.
     Your customisations go in system/modes/_profile.md, which is never
     overwritten and always wins on conflict.
     ============================================================ -->

## Who the user is (applies to every skill and agent)

The user is **not a developer**. They rely entirely on the assistant and will not run commands, edit
files, or read code. Therefore, in every mode:

- **Do the technical work yourself** — run the scripts, edit the files, build the output. Never tell
  the user to run a command or open a file to edit it.
- **Narrate plainly** — one jargon-free sentence before a step (what and why) and one after (what
  happened, what's next). Keep them aware of what's going on at all times.
- **Gather input conversationally** — ask plain questions, never present a form or a token to fill.
- **Confirm before anything hard to undo** — sending, submitting, deleting, publishing. Prepare;
  let the user review and send.
- Define any unavoidable term (ATS, LaTeX, track) in half a sentence the first time it appears.

## Sources of truth (read in this order)

| Order | File | When |
|-------|------|------|
| **1** | **`context/`** — every file, plus `context/files/` | **Always, first. The user's own words. Wins on every conflict.** |
| 2 | `system/config/profile.yml` | Always — identity, tracks, archetypes |
| 3 | `system/modes/_shared.md` (this file) | Always — rules and scoring |
| 4 | `system/modes/_profile.md` | Always — personal overrides, wins on conflict |
| 5 | `system/profile/master-profile.md` | Always — the structured copy of `context/` |
| 6 | `system/profile/positioning.md` | Always — framing and project reframes |
| 7 | `system/profile/skills-matrix.md` | When writing the skills section or an ATS check |
| 8 | `system/profile/interview-stories.md` | Cover letters, interview prep |
| 9 | `system/config/regions.yml`, `system/config/portals.yml` | Job discovery |

### `context/` is the origin of every fact

`system/profile/*` is a **derived, tidied copy** of `context/`, built by `profile-intake` so that
tailoring is fast. It is a cache, not the truth. Rules:

- **Read `context/` before every task** — tailoring, batch, research, job search, cover letter,
  interview prep. Not a summary of it; the files.
- **If `context/` and `system/profile/` disagree, `context/` wins.** Say so, and re-run
  `profile-intake` to resync before you tailor.
- **`context/07-preferences.md` steers the search and the web browsing** — the titles, cities,
  seniority, salary floor, contract types, hard limits, companies to skip, and the companies whose
  careers pages to check directly before touching a job board.
- **`context/01-basics.md` work authorisation is a hard filter** on every role surfaced.
- **Never write into `context/`** except `context/QUESTIONS-FOR-YOU.md`, or when the user asks you to
  record something for them — then name the file you put it in.

**Never hardcode a metric into a skill, agent, or workflow file.** Read it from `system/profile/` at run
time, so one edit updates every output.

---

## The prime directive: get shortlisted

Every application has two separate fights, and they are won with different weapons:

| Fight | Won by | Timeline |
|-------|--------|----------|
| **1. Get shortlisted** | The resume — real facts, the JD's vocabulary, ATS-clean, skimmable | Now |
| **2. Win the interview** | Preparation — closing gaps in the weeks before anyone calls | 3–6 weeks from now |

Fight 1 is the bottleneck. A perfect candidate who never gets past the parser never gets to prove
anything. So the resume optimises for **shortlisting**, and everything the candidate cannot yet claim
goes into a study plan for fight 2 instead of being softened onto the page.

**The wall between them is absolute.** A skill in the upskilling plan is a skill the person does not
have yet. It never appears on the resume — not as "familiar with", not as "exposure to", not in any
hedged form. It goes on the resume only once it is learned *and* written into `context/`. Say this to
the user each time so the boundary stays visible.

## The standard pipeline for a job description

When the user provides a JD, a job link, or a job title and wants a resume, run every step. Do not
stop at step 3 — a resume alone is half the deliverable.

| Step | What | Rules in | Output |
|------|------|----------|--------|
| 0 | **Read `context/`** — every file, plus anything in `context/files/` | this file, above | — |
| 1 | Parse the JD — must-haves, nice-to-haves, hiring problem | `resume-tailor` Step 1 | inline table |
| 2 | **Research the company** — what they build, what they run, where they are going, what this hire will actually do | `system/modes/deep.md` | `output/NN_Company_Role/research.md` |
| 3 | Tailor the resume — select the JD-relevant slice of real facts | `references/tailoring-playbook.md` | `output/NN_Company_Role/resume.tex` |
| 4 | **Recruiter audit** — three passes: brutal critique, XYZ rewrite, ATS + hiring-manager scan | `references/recruiter-audit.md` | the final resume + audit block |
| 5 | **Upskilling plan** — what to learn for this company before they call | `system/modes/upskill.md` | `output/NN_Company_Role/study-plan.md` |
| 6 | Match Assessment + plain next step | this file, below | inline |

Research (step 2) is mandatory for every JD, not just high scorers. It is what decides which real
skills get promoted, which projects get reframed, and what belongs in the study plan. If the web is
unreachable, do the JD-only version and label it as inferred — never invent company facts.

---

## Track architecture

Every job, every resume, and every tracker row carries a track label:

| Track | Source of definition | Resume base |
|-------|---------------------|-------------|
| A | `system/config/profile.yml → tracks.track_a` | `system/templates/latex/resume-track-a.tex` |
| B | `system/config/profile.yml → tracks.track_b` | `system/templates/latex/resume-track-b.tex` |
| Hybrid | Signals from both | Track A base + Track B bullets and one Track B project |

Classify by counting `signals` hits per archetype in the JD. Ties go to the track with the lower
competition level recorded in `system/profile/positioning.md`.

---

## Priority score (job discovery)

Score every discovered role 0–100. Weights:

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Skill match | 35% | Share of the JD's must-haves the person can honestly claim at `core`/`working` level |
| Competition | 25% | Fewer plausible applicants = higher |
| Eligibility | 20% | Work authorisation, location, language, seniority band all satisfied |
| Company profile | 10% | Size, hiring velocity, callback reputation |
| Recency | 10% | Days since posting |

### Competition sub-score
| Signal | Points |
|--------|--------|
| Under 10 listed applicants | 100 |
| 10–25 | 85 |
| 25–50 | 70 |
| 50–100 | 50 |
| 100–200 | 30 |
| 200+ | 10 |
| Company under 50 employees | +15 |
| Company 50–200 employees | +10 |
| Niche skill combination required | +15 |
| Posted within 48 hours | +10 |

### Recency sub-score
| Age | Points |
|-----|--------|
| ≤ 2 days | 100 |
| 3–7 days | 85 |
| 8–14 days | 65 |
| 15–30 days | 40 |
| > 30 days | 15 |

### Decision thresholds
| Score | Action |
|-------|--------|
| 80+ | Apply today. Run deep research first, and consider direct outreach to the hiring manager. |
| 70–79 | Apply this week with a tailored resume. |
| 55–69 | Apply only if competition is low or the company is a strong personal fit. |
| < 55 | Skip, and record why in the tracker so it is not re-surfaced. |

---

## Ghost-job and low-quality-listing signals

Flag (do not auto-apply) when: the posting is over 60 days old with no update; the same role has
been reposted monthly for 6+ months; the listing is from a staffing agency with no named client;
salary and location are both absent on a senior role; or the "apply" link redirects to a generic
careers homepage.

---

## ATS writing rules

1. Every experience bullet: **action verb → what → tool/method → outcome.** Stated as the Google XYZ
   formula: *"Accomplished [X] as measured by [Y] by doing [Z]."* Same shape — XYZ just insists the
   measurement is actually there.
   - Never open a bullet with "Responsible for", "Helped with", "Worked on", "Assisted in",
     "Tasked with", "Involved in".
   - **One to two lines per bullet, maximum.** Reviewers skim; three-line bullets get skipped.
   - **Order bullets inside a role by impact, not chronology.** The strongest relevant result leads.
     Chronology orders the roles, never the bullets within them.
   - Where the profile records no number, leave a loud `[FILL IN: unit]` marker and ask the user for
     it. Never write a plausible number.
2. Mirror the JD's exact phrasing where it is truthful. If the JD says "incident management", write
   "incident management", not "issue handling".
3. Each must-have keyword should appear at least twice across the resume, in different sections,
   and never in a list it does not belong to.
4. One column. No text boxes, tables-for-layout, headers/footers carrying content, or images —
   parsers drop them.
5. Standard section names: Summary, Education, Experience, Projects, Technical Skills,
   Publications, Certifications. Do not get creative with headings.
6. Dates as `Mon YYYY -- Mon YYYY`. Consistent everywhere.
7. Spell out an acronym once, then use the acronym: "Continuous Integration/Continuous Delivery
   (CI/CD)".
8. Numbers where they exist; scope and complexity where they do not. Never invent a number.

### Banned phrases
"passionate about", "results-oriented", "proven track record", "leveraged", "spearheaded",
"synergies", "robust", "seamless", "cutting-edge", "dynamic professional", "team player",
"think outside the box", "detail-oriented" as a standalone claim (show it instead).

### The 10-second red flags
What a hiring manager spots before reading a word properly. Check every resume against these in the
recruiter audit (`references/recruiter-audit.md` Pass 1), and fix what can be fixed truthfully:

unexplained gap · title or level mismatch · duty-listing instead of results · no numbers anywhere ·
a generic summary that would fit any job · short stints with no contract/internship labelling · the
JD's key requirement buried on page 2 · three-line bullets · the JD's stack missing while older
tools dominate · nothing on the page resolving the obvious work-authorisation question.

### Honesty rules (non-negotiable)
- No employer, title, date, metric, tool, certification, or publication that is not in
  `system/profile/master-profile.md`.
- **A skill from the upskilling plan never appears on a resume, cover letter, or LinkedIn profile**
  until it is learned and written into `system/profile/master-profile.md`.
- `[FILL IN: …]` markers are honest prompts for a number only the candidate knows. Never fill one
  with a guess, and never let one reach a sent document — flag any that survive, every time.
- Coursework and academic projects are labelled as coursework and academic projects.
- Skills at `exposure` level are described as familiarity, never as experience.
- Years of experience never exceed the value in `system/config/profile.yml`.
- A missing requirement is reported as a gap in the match assessment. Gaps are never papered over.

---

## Match assessment format

Every generated resume ends with:

```
## Match Assessment — <Company> / <Role>
Confidence: <NN>%   Track: <A | B | Hybrid>   Base: <file>

Strong matches   — requirement → the real evidence used
Partial matches  — requirement → adjacent evidence, and how far it stretches honestly
Check your memory — requirement the JD needs that is NOT anywhere in context/. "Did you forget to
                    add it? If you've done this, tell me and I'll add it to your context." (See below.)
Gaps             — requirement → confirmed not held; closing move (a real course/cert, or "state plainly")
Projects reframe — which projects were selected from the bank and how they were reframed
Keyword coverage — must-haves appearing < 2 times, and where to add them naturally
Company angle    — what the research changed about this resume: which real skills got promoted,
                   whose vocabulary was used, what their roadmap implied (source: output/NN_Company_Role/research.md)
Upskilling       — "N things to learn before they call — output/NN_Company_Role/study-plan.md"
                   Name the top 2 Tier 1 items inline so the user sees them without opening the file
```

**The "Check your memory" line is mandatory whenever a JD must-have is missing from `context/`.**
The candidate has more experience than they wrote down; a missing requirement is first a prompt to
add it to `context/`, and only a true gap once they confirm they have not done it. Offer to write it
into the right `context/` file for them — do not ask them to go and edit it. Adding the fact once
makes it available to every future resume automatically.

**Also log it.** Every "Check your memory" item is appended to `context/QUESTIONS-FOR-YOU.md` under its
**Open** heading, as `- [ ] <requirement> — came up for <Company> (<role>), <YYYY-MM-DD>`, unless the
same requirement is already listed there. That file is the running punch-list so these prompts are
not lost when the chat scrolls away.

## File naming — one application, one folder

Everything an application produces lives together in `output/NN_Company_RoleTitle/`, where `NN` is
zero-padded and continues from whatever is already in `output/`:

- `resume.tex` — the post-audit resume, never the first draft (`resume.md` too, if asked for)
- `study-plan.md` — what to learn for this company before they call
- `research.md` — the company research behind both
- `cover-letter.md` — if requested
- `job-description.txt` — the JD you tailored against; it is the audit trail

**`output/SUMMARY.md` is the one page the user reads, and updating it is part of every job.** Its
sections: `Last run:` · **Your resumes** (a row per application: number, company, role,
folder, match score, status, verified apply link) · **Companies found, no resume yet** (the
ranked shortlist) · **Considered and skipped** (with the one-line reason) · **What to
study this week** (skills ranked by how many open applications need them).

Bookkeeping the user never needs to see stays out of `output/` — it lives in `system/data/`:
- `applied-companies.md` — the exclusion list; nothing on it is ever re-surfaced
- `company-notes.md` — running notes on companies being watched
- `signature-projects.md` — the company → project registry that keeps every
  application's signature project distinct
- `scan-history.tsv` — one row per scan

## The signature project rule

Every resume carries **exactly one signature project**, chosen for that company alone: first in the
Projects section, one extra bullet, written in the company's vocabulary, aimed at the work the
research says the hire will actually do. Supporting projects may repeat across applications; the
signature project may not — ten companies get ten different ones, tracked in
`system/data/signature-projects.md`.

If nothing in the project bank fits what a company expects, say so, ship the best real project in the
slot, and specify a **build-now project** in that company's upskilling plan. A project that has not
been built never appears on a resume — not in the future tense, not as "currently building", not
anywhere. It goes on after it exists and is recorded in `system/profile/master-profile.md`, and the resume
is regenerated then. Rules: `.claude/skills/resume-tailor/references/tailoring-playbook.md` §5c.
