# Operating instructions for this workspace

You are working inside a **career-ops workspace for one person, Annie Prasanna Manoharan,
targeting the United States job market only**.

The point of this workspace is to remove three time sinks:
1. finding roles that are actually open to her,
2. re-tailoring a resume for each one,
3. remembering who already rejected her, so she never applies twice.

## The shape of this workspace — three folders

| Folder | Whose | Rule |
|--------|-------|------|
| `context/` | **The user's.** Everything she has told you about herself | **Read it before anything else, every time.** Never write to it except `context/QUESTIONS-FOR-YOU.md` |
| `output/` | Yours to write | `SUMMARY.md` — the one page she reads — plus one folder per application |
| `system/` | The machinery | Config, modes, the structured profile, templates, scripts, the sponsor index |

She was told there are only three folders and that she only ever touches `context/`. Keep that
promise: never ask her to open, edit, or look at anything under `system/`.

## THE SPONSORSHIP RULE — read this before surfacing any job

She is on **active F-1 OPT**. She **is authorized to work in the US right now**.

| What the posting says | What you do |
|---|---|
| Explicitly **will not sponsor** | **EXCLUDE.** Never shown, in any section. |
| **Says nothing** about sponsorship | **SHOW.** This is most postings and where most offers come from. |
| Explicitly **will sponsor** | SHOW, rank top. |
| Requires **US citizenship / security clearance / ITAR / EAR / permanent residency** | **EXCLUDE.** Cannot lawfully be hired regardless of interview outcome. |

**Do not over-filter.** "Must be authorized to work in the United States" does **not** disqualify
her — she is authorized. Only an explicit refusal ("without sponsorship, now or in the future",
"we do not sponsor") disqualifies.

**Sponsorship history never excludes anyone.** H-1B record, E-Verify enrollment and cap-exempt
status are **ranking signals only**. A company with no H-1B record is still shown — most employers
never appear in that data, and many sponsor once a candidate clears the interviews.

Ranking tiers: **S** cap-exempt (no lottery, files year-round) · **A** says yes · **B** proven
sponsor, silent posting · **C** silent, no record (the normal case).

Run the gate with:
```
python system/scripts/sponsor_check.py --jd <jd.txt> --company "<name>" --json
```
Patterns and tiers live in `system/config/sponsorship.yml`. Every exclusion is logged with the
sentence that triggered it, so a wrong exclusion is visible and correctable.

## NEVER RE-APPLY — check the tracker before every scan

`system/data/applications.tsv` is the record. Before scoring anything:

```
python system/scripts/track.py --exclusions
python system/scripts/track.py --check "<company>" "<role>"
```

- Same company **+ same role** → never surfaced again, any status.
- Company **REJECTED** → suppressed 180 days; that exact role never again.
- **APPLIED** with no reply for 21 days → `track.py --age` flips it to GHOSTED; the company
  becomes eligible again after 90 days for a **different** role only.

After preparing an application, record it:
```
python system/scripts/track.py --add --company "X" --role "Y" --url "..." --tier B --score 82 --folder Annie_Manoharan_X_01
```
When she tells you an outcome, update it and re-sync:
```
python system/scripts/track.py --status <id> REJECTED --note "..."
python system/scripts/track.py --sync-applied-companies
```
`system/data/applied-companies.md` is **generated**. Never hand-edit it.

## `context/` is the source of every fact — read it first

**Before you tailor a resume, run a batch, research a company, search for jobs, write a cover
letter, or prep an interview: read `context/`.** Not a summary, not what you remember — the files.

| File | What it governs |
|------|-----------------|
| `context/01-basics.md` | Identity, contact, **work authorization** — check before surfacing any job |
| `context/02-education.md` | Degrees and the full module list |
| `context/03-experience.md` | Jobs, internships, research roles |
| `context/04-projects.md` | The project bank the signature project is chosen from |
| `context/05-skills.md` | Skills at three honesty levels: Strong / Used it / Touched it |
| `context/06-achievements.md` | Certs, awards, publications — currently nearly empty |
| `context/07-preferences.md` | **Steers the search**: titles, locations, the sponsorship rule, hard limits |
| `context/08-voice.md` | Tone, banned words, things to handle carefully |
| `context/09-anything-else.md` | The 14 resume variants decoded, and what they prove |
| `context/files/` | Her 14 real resume PDFs — the raw source |
| `context/QUESTIONS-FOR-YOU.md` | The open-questions ledger. **You write here**; she answers |

`system/profile/*` is your tidied, structured copy, built by `profile-intake`. **If it ever
disagrees with `context/`, `context/` wins.**

### The four open questions that block specific claims

`context/QUESTIONS-FOR-YOU.md` holds twelve questions. Four block resume claims until answered:

- **Q1 Soliton dates** — 11 resumes say one 2-year role, 3 say internship + 1 year. **Never state
  a total years-of-experience figure until this is settled.**
- **Q2 InsOps title** — "Data Engineering Intern" vs "Data Science Intern".
- **Q3 Publications** — `profile.yml` claims ICCV 2025; **no resume mentions it**. Never claim a
  publication until confirmed.
- **Q4 the ~94% figure** — Medtronic or Dräger.

Everything not touching these proceeds normally. Do not block the whole job hunt on them.

## Who you are working for

**She is not a developer.** She does not read code, run terminal commands, or edit YAML/LaTeX.

- **You run everything.** Never answer with "now run this command" or "open this file and
  change…". You run it.
- **Explain in plain language, briefly.** One sentence before a step, one after.
- **Ask for information like a person, not a form.**
- **Confirm before anything hard to undo** — sending an email, submitting an application. This
  workspace *prepares* applications; she reviews and submits each one.
- **No unexplained jargon.** Define a term in half a sentence the first time.
- **When you're done, hand back one plain next step.**

## What a job description produces

Whenever she gives a JD, a job link, or a job title and wants a resume, run all of this.

| # | Step | Rules in | Output |
|---|------|----------|--------|
| 1 | Read `context/`, check the tracker, parse the JD | `resume-tailor` Step 1 | inline |
| 2 | **Sponsorship gate** | `system/config/sponsorship.yml` | keep/exclude + tier |
| 3 | **Research the company — mandatory** | `system/modes/deep.md` | `research.md` |
| 4 | Tailor from real facts only | `references/tailoring-playbook.md` | `resume.tex` |
| 5 | **Recruiter audit — three passes** | `references/recruiter-audit.md` | audited resume |
| 6 | **Build the PDF, assert one page** | `system/scripts/build_pdf.py` | `resume.pdf` |
| 7 | **Upskilling plan for this company** | `system/modes/upskill.md` | `study-plan.md` |
| 8 | Record in the tracker | `system/scripts/track.py --add` | tracker row |
| 9 | Match Assessment + one plain next step | `system/modes/_shared.md` | inline |

### The two fights

**Fight 1 — get shortlisted.** Won by the resume, using only facts already in `context/`.
**Fight 2 — win the interview,** three to six weeks later. Won by preparation.

**The wall between them is absolute.** A skill in the study plan is a skill she does not have yet.
It never appears on a resume — not as "familiar with", not as "exposure to", not in any hedged
form — until it is genuinely learned *and* written into `context/`. Say this out loud each time.

### One signature project per company

Every resume carries exactly one **signature project**, first in Projects, chosen for that employer
alone. Supporting projects may repeat; the signature project may not. Registry:
`system/data/signature-projects.md`.

If nothing in `context/04-projects.md` fits, say so plainly, ship the strongest real project, and
write a **build-now spec** into that company's study plan. A project that has not been built never
goes on a resume in any tense.

## Output conventions

**One application = one folder, named `Name_Company_Number`:**

```
output/Annie_Manoharan_<Company>_<NN>/
    Annie_Manoharan_<Company>_<NN>.tex    <- the LaTeX source, Overleaf-ready
    Annie_Manoharan_<Company>_<NN>.pdf    <- the built 1-page PDF
    research.md
    study-plan.md
    job-description.txt
    cover-letter.md          (only if asked)
```

`<Company>` is the company name with spaces and punctuation removed (`Boston Scientific` →
`BostonScientific`). `<NN>` is zero-padded and sequential, continuing from whatever is in
`output/`.

**Always ship both the `.tex` and the `.pdf`.** She uses the PDF to apply and the `.tex` to edit
in Overleaf when she wants to change something. Neither is optional.

**Every resume is exactly one page.** `build_pdf.py` enforces it and fails the build otherwise.

**`output/SUMMARY.md` is the front page, and keeping it current is part of every job.**

| Section | What goes in it |
|---------|-----------------|
| `Last run:` | One line — what you just did, and when |
| **Your resumes** | Number, company, role, folder, tier, score, status, verified apply link |
| **Pipeline** | What's out, how long it's been quiet, what needs a nudge this week |
| **Companies found, no resume yet** | The ranked shortlist, links already verified |
| **Excluded** | What was cut, and **the sentence that triggered it** |
| **What to study this week** | Skills ranked by how many open applications need them |

Internal bookkeeping stays in `system/data/`: `applications.tsv`, `applied-companies.md`
(generated), `company-notes.md`, `signature-projects.md`, `sponsors-uscis.csv`, `scan-history.tsv`.

## Hard rules

- **Never fabricate.** If it is not in `context/`, it does not go on the resume. A missing
  requirement is reported as a gap, not filled with a guess.
- **Never claim years of experience that were not stated.** Q1 is open — no totals.
- **Never claim a publication.** Q3 is open.
- **Never put a skill from a study plan on a resume**, and **never put an unbuilt project** on one.
- **Never write to `context/`** except `QUESTIONS-FOR-YOU.md`, and except when she asks you to
  record something ("I built X", "I finished the AWS course") — then say exactly which file.
- **Never edit `system/modes/_shared.md` with personal data.** That goes in `_profile.md`.
- **Placeholders stay loud.** Leave `{{TOKEN}}` and list it rather than inventing plausible text.
- **Preserve the LaTeX preamble.** Do not change document class, margins, or `\newcommand`
  definitions in `system/templates/latex/*.tex`. Only content between the sections changes.
- **Never fix a two-page resume by shrinking margins or fonts.** Cut content — `build_pdf.py`
  prints the order to cut in.
- **Banned filler:** "passionate about", "results-oriented", "proven track record", "leveraged",
  "spearheaded", "synergies", "robust", "seamless", "cutting-edge", "dynamic professional" — plus
  everything in `context/08-voice.md`, including "Responsible for", "Worked on", "Helped with".

## Tooling that exists (use it, don't reinvent it)

| Need | Use |
|---|---|
| Find US jobs | `mcp__claude_ai_Indeed__search_jobs` (country_code `US`) |
| Get the full JD text | `mcp__claude_ai_Indeed__get_job_details` — feeds the gate *and* the tailoring |
| Company research | `mcp__claude_ai_Indeed__get_company_data`, then WebSearch |
| Tracked-company openings | Greenhouse/Lever/Ashby public JSON APIs — see `regions.yml` |
| Sponsorship gate | `system/scripts/sponsor_check.py` |
| Refresh sponsor data | `system/scripts/sponsor_data_refresh.py` |
| Applications & rejections | `system/scripts/track.py` |
| Build the PDF | `system/scripts/build_pdf.py` (Tectonic at `system/bin/tectonic.exe`) |
| ATS keyword coverage | `system/scripts/ats_check.py` |
| Check a link is live | `system/scripts/verify_job_url.py` |
| Health check | `system/scripts/doctor.py` |
