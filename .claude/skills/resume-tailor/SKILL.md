---
name: resume-tailor
description: >-
  Research a company, then tailor this workspace's candidate resume to its job description for a high
  ATS match — producing company research, a complete audited resume, an honest match assessment, and
  an upskilling plan of what to learn for that company before they call. Use WHENEVER a job
  description, job posting, JD, role spec, or job link is provided and a resume or CV is the goal —
  even if the user only pastes the JD text with no instruction. Also use for "update my resume for
  this role", "optimise my CV", "write a cover letter for this job", "what should I learn for this
  company", or "run an ATS keyword check". Reads the candidate's facts from system/profile/ — never
  fabricates experience, metrics, or skills.
---

# Resume Tailor

Turn a job description into a tailored, compile-ready resume for the person described in
`context/`, with a high ATS match and zero invented claims.

## Inputs you might get

- **A pasted JD** — most common. Treat the paste itself as the trigger; no instruction needed.
- **A job URL** — fetch it first, then proceed. If fetching is blocked, ask for the pasted text.
- **A title only** ("Data Analyst, Fayetteville") — proceed, but say you are working from the title alone
  and that a full JD would sharpen the match by a lot.
- **A company name only** — research the company's open roles first, or ask which one.

## Read before writing

| File | Why | When |
|------|-----|------|
| **`context/`** — every file | **The user's own words. Every fact on the page traces here. Wins on any conflict with `system/profile/`.** | **Always, first** |
| `system/config/profile.yml` | Identity, tracks, archetypes, signal words | Always |
| `system/modes/_shared.md` | Scoring, ATS rules, banned phrases, honesty rules | Always |
| `system/modes/_profile.md` | Personal overrides — these win | Always |
| `system/profile/master-profile.md` | The structured copy of `context/` — fast to select from | Always |
| `system/profile/positioning.md` | Framing per archetype, project reframing map, honest gaps | Always |
| `system/profile/skills-matrix.md` | Skill ordering and the ATS keyword bank | Always |
| `references/tailoring-playbook.md` | Track selection, section rules, page fit | Always |
| `references/ats-rules.md` | Keyword placement, parser-safe formatting | Always |
| `references/recruiter-audit.md` | **The three-pass audit every resume must survive** | Always, at Step 6 |
| `system/modes/deep.md` | Company research — including where they are going next | Always, at Step 3 |
| `system/modes/upskill.md` | Turning the research into a study plan for this company | Always, at Step 8 |
| `references/output-formats.md` | LaTeX vs Markdown vs PDF, file naming | At output time |
| `system/profile/interview-stories.md` | Cover letters and interview prep | When asked |

**If `system/profile/master-profile.md` still contains `{{TOKEN}}` placeholders, stop.** Run
`profile-intake` first and say so — a resume from an unfilled profile is a fabricated resume. If
`context/` is empty too, offer to interview the user and fill it for them; never tell them to go and
edit files.

**If `context/` has changed since `system/profile/` was last built, re-run `profile-intake` before
tailoring.** `context/` is what the person actually said; `system/profile/` is only your tidied copy
of it, and a stale copy silently drops their newest work.

## What one job description produces

A resume alone is half the job. Every JD run delivers all four, in this order:

All four land in **one folder**, `output/NN_Company_RoleTitle/` (NN continuing from what is already
in `output/`):

| # | Deliverable | File |
|---|-------------|------|
| 1 | Company research — what they build, run, and are building next | `research.md` |
| 2 | The tailored resume, **after** the recruiter audit | `resume.tex` |
| 3 | The audit itself — score, red flags fixed, ATS verdict, pile verdict | shown inline |
| 4 | The upskilling plan for this company | `study-plan.md` |
| + | The job ad, kept as the audit trail | `job-description.txt` |

The split that governs everything: **the resume gets them shortlisted using only facts they already
have; the upskilling plan wins the interview weeks later.** Shortlisting takes 3–6 weeks, and that
waiting time is the candidate's biggest asset — but nothing from the plan touches the resume until
it is genuinely learned and added to `context/`.

## Workflow

### Step 0 — Read `context/`
Every file, plus anything in `context/files/`. This is where every fact on the page comes from —
`04-projects.md` supplies the signature project, `02-education.md` the modules to promote,
`05-skills.md` the honesty level of every skill, `08-voice.md` the tone and the words to avoid.
Do not work from memory of an earlier turn; read the files.

### Step 1 — Analyse the JD
Print a short table before writing anything:
- Company · role title · team · location · work mode · seniority
- 5–7 **must-have** technical requirements (the ones repeated, or listed under "required")
- 3–5 **nice-to-haves**
- 3–5 domain/soft keywords ("stakeholder", "SOP", "on-call", "agile", "policy enforcement")
- The **hiring problem** in one sentence: what is broken or growing that made them open this role

### Step 2 — Classify the track
Count `signals` hits per archetype from `system/config/profile.yml`. Pick Track A, Track B, or hybrid, and
load the matching base from `system/templates/latex/`. State the classification and why in one line.
Preserve the base's preamble, margins, and custom commands (`\job`, `\project`, `\resumeSubheading`
…) exactly — only content changes.

### Step 3 — Research the company (mandatory, every JD)
Run `system/modes/deep.md` and save `output/NN_Company_Role/research.md`. Not optional, and not only for high scorers —
this is what makes the resume targeted rather than generic. Cover:

- **Now:** what they build, who buys it, their real stack (engineering blog and GitHub beat the JD),
  their current pressures.
- **Next:** their roadmap, what their *other* open roles reveal, migrations in progress, what a
  funding round or acquisition was for.
- **The day job:** three to five sentences on what this hire will actually do in months 1–3, and
  where it goes by month 12.
- **The skills demand map** (`system/modes/deep.md` §6) — every skill the JD or the research names, sorted
  into exactly three destinations: **Resume** (they have it → promote it in the company's own
  words), **Upskilling plan** (they do not have it, learnable in the window → Step 8, never the
  resume), **Honest gap** (not held, not learnable in weeks → Match Assessment).

Research changes which *true* facts are emphasised, whose vocabulary is used, and what order things
appear in. **It never adds a skill the person does not have.** Without web access, infer from the JD,
label every inference as inferred, and say so to the user.

### Step 4 — Tailor (select from the superset, don't dump it)
`context/` — and its structured copy `system/profile/master-profile.md` — is a **complete knowledge
base** that is intentionally bigger than any resume. Tailoring = **scoring every item against this JD and keeping the top-ranked ones that fit
the page budget** (full algorithm in `references/tailoring-playbook.md` §5). Full rules there; in
short:

- **Summary** — rewrite in the JD's own vocabulary. Name the role's core technologies. State years
  of experience only if `system/config/profile.yml` has them; for a graduate profile, lead with the degree,
  the strongest project, and the domain.
- **Skills** — reorder per `system/profile/skills-matrix.md` so the JD's top tools come first. Add only skills the
  person actually has. Drop categories the JD does not care about.
- **Experience bullets** — action verb → what → tool/method → outcome. Keep real numbers. Mirror the
  JD's phrasing where it is truthful. Keep role types honest (internship stays "Intern").
- **Projects — the highest-leverage edit.** Score the whole Projects & Build Bank by `Tags:` overlap
  with the JD *and* the demand map, take the best two (three on a one-pager), and reframe them using
  `system/profile/positioning.md`. Reframing changes the title and the framing, never the underlying facts.
- **The signature project (one per company, never repeated).** The top-scoring project becomes this
  company's **signature project**: first in the Projects section, one extra bullet, written in their
  vocabulary, aimed at the work the research says this hire will do. Check
  `system/data/signature-projects.md` first so no project is used twice, and add this application's
  row after. Ten companies must get ten different signature projects. If nothing in the bank fits
  what this company expects, say so plainly, ship the best real project as signature, and put a
  **build-now spec** in the upskilling plan — never a project that does not exist yet, in any tense,
  anywhere on the page. Full rules: `references/tailoring-playbook.md` §5c.
- **Education** — promote the specific modules and coursework projects the JD names, pulled from the
  full module list. For graduates, this section moves above Experience.
- **Publications / certifications** — promote what is relevant, drop what is not.

Whenever a JD must-have is **not found anywhere in `context/`**, do not invent it — raise it under
"Check your memory" in the Match Assessment, offer to write it into the right `context/` file the
moment they confirm they've done it, **and append it to `context/QUESTIONS-FOR-YOU.md`** under **Open** (`- [ ] <requirement> — came up for <Company> (<role>),
<YYYY-MM-DD>`, skipping duplicates) so the prompt survives after the chat scrolls away.

### Step 5 — Page fit
Two pages for an experienced profile, one page for a graduate or career-changer unless the market
expects two (check `system/config/regions.yml → cv_conventions`). Target ~95% fill of the last page. Trim
the lowest-priority bullets first; never shrink the font below the base's setting.

**A short page is a failure, not a clean look.** `build_pdf.py` only catches overflow — nothing
stops a thin, mostly-white one-pager from compiling successfully. Before it ships, run the
full-page checklist in `references/tailoring-playbook.md` §7: every unblocked real job on the page,
three projects, every real skill category, every relevant module. If real content runs out, say so
plainly — never invent a bullet or a project to fill the gap.

### Step 6 — Recruiter audit (mandatory — the draft is not the deliverable)
Run all three passes from `references/recruiter-audit.md` **yourself**. Never hand these to the user
as prompts to run.

1. **Pass 1 — senior recruiter at this company.** Brutally honest: match score out of 100 with its
   component breakdown, the top 5 missing ATS keywords (each labelled *in the profile but not on the
   page* vs *not held at all*), the 3 red flags visible in under 10 seconds, which sections are
   strong and why, which are weak and why, and how this compares to a strong candidate for the role.
2. **Pass 2 — rewrite Experience (and Projects).** XYZ formula on every bullet, strong verb first,
   the *truthful* missing keywords woven in naturally, red flags fixed, 1–2 lines per bullet,
   bullets ordered by impact. Where the profile has no number, leave `[FILL IN: unit]` — never a
   plausible guess — and collect them all into one short list of plain questions for the user.
3. **Pass 3 — dual scan.** As an ATS: pass or fail, keywords present vs still missing, formatting
   risks; back it with `python3 system/scripts/ats_check.py`, run by you. As a hiring manager on resume 147
   of 200: what gets skipped, what stops the scroll, yes/maybe/no pile, and a rewrite of anything
   that would be skipped.

Apply every fix, then re-score honestly. The file saved in `output/` is always the post-audit
version.

### Step 7 — Output
1. Produce the **complete** document — `\documentclass` to `\end{document}`, never a fragment.
2. Save as `output/NN_Company_Role/resume.tex` (and `.md` if Markdown was requested). Save the JD to
   `output/NN_Company_Role/job-description.txt` as the audit trail.
3. Tell the user how to build it: `bash system/scripts/build_pdf.sh output/NN_Company_Role/resume.tex`, or
   paste into Overleaf.
4. Print the **Match Assessment** in the format defined in `system/modes/_shared.md`: confidence, strong
   matches, partial matches, gaps with closing moves, the projects reframe, keyword coverage, the
   company angle, and the upskilling pointer.

### Step 8 — Upskilling plan (mandatory)
Run `system/modes/upskill.md` and write `output/NN_Company_Role/study-plan.md` from
`system/templates/docs/upskilling-plan.template.md`. It takes the "Upskilling plan" column of the demand map
(Step 3) plus the gaps the audit exposed, and turns them into three tiers:

- **Tier 1** — before the screening call (weeks 1–2): the JD's must-haves, max 5.
- **Tier 2** — before the technical round (weeks 2–5): what they actually run, max 5, each ending in
  a small **proof artefact**.
- **Tier 3** — first 90 days, from their roadmap, max 4.

Every row names one specific resource — never "search online" — and Tier 1/2 rows name the weekend-
sized artefact that turns the learning into a claimable resume line.

The plan also carries **the signature project's defence brief** — how to explain that project in the
interview: architecture, why each tool, the three real trade-offs, what broke, the honest scale
limits, and 8–10 likely questions with answers. That project is what the interview digs into hardest,
and this section is what the candidate revises before the call. If the signature slot had to ship
weak, this section is instead the **build-now spec** for the project that would have fit.

Update `system/data/signature-projects.md`, add this application's row to `output/SUMMARY.md` →
**"Your resumes"**, and refresh its **"What to study this week"** table on batch runs. Close with the loop: *"When you finish any of these, tell me and I'll add it to your profile so
it starts appearing on your resumes."*

Then hand back one plain next step: PDF, cover letter, interview prep, or the first thing to study.

## Optional add-ons (only when asked)
- **Cover letter** — ≤400 words, Pain → Agitate → Solution, framework in
  `system/profile/interview-stories.md`. Reference one real company specific. Save to `output/`.
- **ATS keyword check** — `python3 system/scripts/ats_check.py --resume <file> --jd <file>` and interpret
  the output; suggest natural placements for anything under-covered.
- **LinkedIn** — ≤120-char headline plus three about-section bullets mirroring the JD.
- **Interview prep** — hand off to the `interview-prep` skill.

## Hard rules
- Never fabricate an employer, date, metric, tool, certification, or publication.
- **Never move a skill from the upskilling plan onto the resume.** Not as "familiar with", not as
  "exposure to". It qualifies only once it is learned and written into `context/`.
- Never ship the pre-audit draft. Steps 6 and 8 are part of the deliverable, not extras.
- Never leave a `[FILL IN: …]` marker unflagged, and never fill one with a guessed number.
- Never inflate years of experience, and never present coursework or a personal project as a job.
- Skills the user put under "Touched it" in `context/05-skills.md` (`exposure` in the master profile)
  are described as familiarity, never experience.
- Words the user banned in `context/08-voice.md` never appear, on top of the standard banned list.
- Always output a complete document, never a fragment.
- Always end with the Match Assessment, including the gaps. An honest gap list is the deliverable's
  most useful section.
- Banned filler: see `system/modes/_shared.md`.
