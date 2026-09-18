# Mode: deep — research one company before applying

**Run this for every job description the user brings, not only for high scorers.** Company research
is what turns a generic resume into a targeted one: it decides which real skills get promoted, which
projects get reframed, and what goes into the upskilling plan. Also run it before any interview.

Output goes to `output/NN_Company_Role/research.md`. A shorter version is fine for a low-scoring
role — but it is never skipped. If the web is unreachable, produce the JD-only version and label it
as such; never fill gaps with plausible invention.

## 0. Read `context/` before you browse

Research is a **comparison**, not a company summary. You are working out what this company needs
*versus what this person actually has* — so read `context/` first, or §6 (the part that drives both
the resume and the study plan) is guesswork.

| From `context/` | What it changes about the research |
|-----------------|-----------------------------------|
| `04-projects.md`, `05-skills.md` | The demand map in §6 — every skill this company needs is scored against what they really hold |
| `02-education.md` | Which of their named requirements a module already covers |
| `01-basics.md` → right to work | Whether this employer can actually hire them — check for sponsorship signals, and say plainly if they cannot |
| `07-preferences.md` → salary, location, hard limits | Whether this role is worth the effort at all. Say so early if it is not |
| `08-voice.md` | The vocabulary the fit narrative and cover-letter angle are written in |

Anything the research shows this company wants that is **not anywhere in `context/`** is not
automatically a gap — the person may simply not have written it down. Raise it as a
"⚠️ did you forget to add it?" and log it in `context/QUESTIONS-FOR-YOU.md`.

## 1. What they do
Product, customers, business model, stage, funding or ownership, headcount and trend.

## 2. Engineering and tooling reality
Public stack signals: engineering blog, GitHub org, job ads for *adjacent* roles, conference talks,
their docs. **What they actually run beats what the JD lists** — a JD is written by a recruiter, the
engineering blog is written by the team. Note where the two disagree; that gap is often the most
useful thing on this page.

## 3. The team behind this role
Who the role reports to if discoverable, team size, whether it is a new or backfilled headcount,
what the team shipped recently.

## 4. Current pressures
Recent launches, funding, layoffs, regulation, competitors, expansion into this market. This is the
"Pain" in the cover letter.

## 4b. Where they are going next (the forward look)
The half of the research that most people skip, and the half that makes the resume land. Look for:

- **Stated roadmap** — product announcements, "coming in 2026", public betas, beta waitlists.
- **Hiring pattern** — every other role they have open right now. Ten backend openings plus a
  platform lead means a rebuild; a first data hire means they are starting from nothing.
- **Investment signals** — a funding round names what the money is for. Acquisitions, new market
  entries, a new office in this region.
- **Technology direction** — migrations in progress (on-prem → cloud, monolith → services, a new
  ML platform), regulatory work they are obliged to do, deprecations they have announced.
- **Public commitments** — leadership talks, earnings calls if listed, press interviews.

State clearly which of these are confirmed and which are inferred.

## 5. What they will actually expect from this hire
Convert everything above into the day job: three to five sentences on what this person will be doing
in months 1–3, and where the role goes by month 12. Not the JD's bullet list — the real work implied
by their stage, their stack, their pressures, and their roadmap.

## 6. Skills demand map (drives both the resume and the upskilling plan)

The bridge between research and output. Every skill the JD or the research names goes in one row:

| Skill / tool | Named by | How central | Candidate's real level | Where it goes |
|--------------|----------|-------------|----------------------|---------------|
| e.g. Kubernetes | JD must-have + eng blog | Core to the day job | working | Resume — promote to Summary + Skills |
| e.g. Terraform | Adjacent job ads only | Likely within 6 months | none | Upskilling Tier 2 |

Levels come from `context/05-skills.md` (Strong / Used it / Touched it), as recorded in
`system/profile/skills-matrix.md` — `core`, `working`, `exposure`, or none. The last column
is one of exactly three destinations:

- **Resume** — the candidate genuinely has it. Promote it, in the company's own vocabulary.
- **Upskilling plan** — they do not have it and could realistically learn it in the shortlisting
  window. It goes to `output/NN_Company_Role/study-plan.md`, **never onto the resume.**
- **Honest gap** — not held, not learnable in weeks (years of production experience, a clearance, a
  specific degree). Named in the Match Assessment with the honest answer for the interview.

**This table never moves a skill from the second or third column onto the resume.** Research changes
which *true* facts are emphasised, in whose vocabulary, and in what order. It never adds a skill the
person does not have.

## 7. Fit narrative
Two or three sentences: the problem they have, the evidence this person has solved something of that
shape, and the honest limit of the analogy.

## 8. Application angle
- Which two projects to reframe, and into what
- Which proof points lead
- Which gap will come up, and the honest answer
- Whether a referral route exists

## 9. Questions to ask them
Four questions that could only come from having done this research. At least one should come from
§4b — asking about a direction they have announced is the clearest signal that the research was real.

## Sourcing rules
Cite a URL for every non-obvious claim. Mark anything inferred as inferred. Distinguish "their blog
says" from "their JD says" from "I concluded". If the web is unavailable, produce the JD-only
version and label it — never fill the gaps with plausible invention.
