# The recruiter audit — three passes over every resume

Run this on **every** tailored resume, before it is handed over. A first draft is not a deliverable;
the audited version is. Do all three passes yourself and show the user the results — never hand the
user these as prompts to run.

Why it exists: the resume's only job is to **get shortlisted**. It is read twice before any human
decides — once by a parser, once by a person skimming for six seconds — and it has to survive both.
Pass 1 finds what would fail. Pass 2 fixes it. Pass 3 re-checks as both readers.

---

## Pass 1 — Senior recruiter for this exact company

Act as a senior recruiter *at this company*, holding this JD, having just read fifty resumes for this
role. Be blunt. The candidate has said explicitly they would rather fix problems now than be ghosted
later, so soften nothing.

Produce, in this order:

**1. Match score — NN/100.** Composition:

| Component | Weight | Measures |
|-----------|--------|----------|
| Must-have coverage | 40% | Share of the JD's must-haves backed by real, evidenced experience |
| Keyword / ATS coverage | 20% | Must-have phrases present, in the JD's own wording, at least twice |
| Evidence strength | 20% | Numbers, scope, outcomes — not duties |
| Seniority and domain fit | 10% | Right band, right industry vocabulary |
| Readability in a 6-second skim | 10% | Front-loading, bullet length, scannability |

Report the component breakdown, not just the total. A total with no breakdown cannot be acted on.

**2. Top 5 missing keywords the ATS is scanning for.** Ranked by how often each appears in the JD and
whether it sits under "required". For each one, say which of two things it is:

- **In the profile but not on this page** — a writing problem. Fix it in Pass 2.
- **Not held at all** — a truth problem. It becomes a gap in the Match Assessment and a line in
  `career-dashboard/data/output/applications/Annie_Manoharan_<Company>_<NN>/study-plan.md`. It never gets written onto the resume.

That distinction is the whole game.

**3. The 3 red flags a hiring manager spots in under 10 seconds.** Check at least these:

| Red flag | What it looks like |
|----------|--------------------|
| Unexplained gap | Months missing between roles with no line covering them |
| Title / level mismatch | Applying two bands above anything ever held, with nothing bridging |
| Duty-listing | Bullets describing responsibilities instead of results |
| No numbers anywhere | Zero quantification in the whole document |
| Generic summary | A summary that would fit any job at any company |
| Job-hopping pattern | Several short stints with no contract or internship labelling |
| Buried relevance | The one thing this JD wants is sitting on page 2 |
| Density | Bullets running three or more lines, walls of grey text |
| Stale tooling | The stack the JD names is absent; older tools dominate |
| Eligibility doubt | Nothing on the page resolves the obvious work-authorisation or location question |

Name the three most damaging ones *for this specific application*, and where they appear.

**4. Which sections are strong, and why.** Section by section, one line each.

**5. Which sections are weak, and why.** Same, with the specific failure named.

**6. How this compares to a strong candidate for this role.** Describe what the top-of-pile resume
for this exact JD looks like, then state plainly where this one sits against it and what closes the
distance. If a difference only closes with time, say so — it becomes a Tier 1 line in the upskilling
plan.

---

## Pass 2 — Rewrite the experience section

Rework every Experience bullet under these rules. Wording stays inside what the registry's approved facts for that role say; you may select, reorder and tighten, never add a fact. Project blocks use the registry wording exactly (the validator checks it).

1. **Weave in the missing keywords from Pass 1 — but only the true ones.** They must read as a
   natural part of the sentence. A keyword that cannot be inserted truthfully is *not* inserted: it
   goes to the gap list and the upskilling plan. Never force one in.
2. **Fix every red flag Pass 1 raised**, or state explicitly why one cannot be fixed on paper. An
   unexplained gap may need a real answer rather than a rewrite.
3. **Google XYZ formula on every bullet:** *"Accomplished [X] as measured by [Y] by doing [Z]."* In
   this workspace's wording that is `action verb → what changed → measured by what → using which
   method`. Same shape as the house rule in `career-dashboard/backend/workflows/modes/_shared.md`; XYZ just insists the measurement is
   actually present.
4. **Strong action verb first.** Never "Responsible for", "Helped with", "Worked on", "Assisted in",
   "Tasked with", and never the banned filler listed in `career-dashboard/backend/workflows/modes/_shared.md`.
5. **Numbers wherever they exist.** If `career-dashboard/data/context/` (and its registry, `evidence.yml`) records a number, use it. If it
   does not, leave a loud marker — `[FILL IN: approx. records processed per day]` — suggesting the
   realistic *unit* with the value left empty. **Never write a plausible number, and never fill one
   in as a guess.** The marker is the honest way to ask the candidate for something only they know.
6. **One to two lines per bullet, maximum.** Hiring managers skim; dense paragraphs get skipped. Cut
   qualifiers before cutting content.
7. **Order bullets by impact, not chronology.** The most impressive relevant result leads every role.
   Chronology governs the order of *roles*, never the bullets inside them.

After rewriting, collect every `[FILL IN: …]` into one block and ask the candidate for those numbers
directly, in plain language. There are usually about five, and answering them is the single biggest
score lift available. Write whatever they answer straight back into `career-dashboard/data/context/` (and its registry, `evidence.yml`), so
the question is never asked twice and every future resume inherits the number.

---

## Pass 3 — Dual-perspective final scan

### 3a. As an ATS filter

- **Would this pass the ATS for this job? Yes or No.**
- **Keywords now present** — list them, with the section each appears in and its count.
- **Keywords still missing** — with the reason: not held (gap) versus not yet placed (place it now).
- **Formatting risks** — tables, columns, headers or footers carrying content, images, text boxes,
  unusual glyphs, non-standard section names, inconsistent dates. Check against `ats-rules.md`.
- Back this with the real tool rather than eyeballing it, and run it yourself:
  `career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/workspace.py score --job-id JOB_ID`

### 3b. As a hiring manager on resume 147 of 200

- **Which sections would you skip, and why?**
- **What makes you stop scrolling** — good or bad. Name the exact line.
- **Yes pile, maybe pile, or no pile** for this role — and the one change that moves it up a pile.
- **Rewrite anything that would get skipped** so it earns its six seconds.

### Then deliver the final version

Apply every Pass 3 fix and save the result. The `resume.tex` in the application folder is always the post-audit version;
the pre-audit draft is never the deliverable.

---

## Reporting to the candidate

Compress all three passes into a short, readable block. The user is not a developer and does not want
a wall of analysis:

```
## Recruiter audit — <Company> / <Role>
Before: NN/100   After fixes: NN/100   Verdict: <yes | maybe | no> pile

Fixed          — red flags and keyword gaps closed, one line each
Still open     — what could not be fixed truthfully, and why
Need from you  — every [FILL IN] number, asked as a plain question
ATS check      — the Build & score readiness and coverage results, plus anything flagged
```

## Honesty gates

- The after-fixes score is an honest re-score, not a number chosen to look like progress. If the
  fixes moved it four points, report four.
- A keyword counts as "now present" only if it is truthfully present in real experience.
- `[FILL IN: …]` markers must never survive into a sent resume. Flag any that remain, loudly, every
  time the file is touched. `validate_resume.py` fails any resume with a leftover
  placeholder — that is the backstop, not the plan.
- If Pass 1 scores below 55/100 and the gaps are structural, say plainly that this application is a
  long shot and what would make it viable. A resume cannot fix a role mismatch, and pretending
  otherwise wastes the candidate's week.
