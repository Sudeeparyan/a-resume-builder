# Mode: batch — N companies → N tailored resumes, one pass

Use this when the user asks for **several jobs *and* the resumes to go with them** in a single
request. Typical triggers:

- "give me the latest 10 companies this week with working links"
- "find 10 AI roles in Ireland and tailor a resume for each"
- "10 companies + 10 resumes"

It chains three existing pieces — `scan` → `verify-job-url` → `resume-tailor` — over a list, and
returns one combined table plus **one folder per company in `output/`**, each holding that company's
resume, research, study plan and the job ad. Ask for 10 companies and you get 10 folders with 10
genuinely different resumes. Nothing here invents a listing, a link, or a resume fact; the honesty
rules in `system/modes/_shared.md` apply to every row.

## Inputs
- **N** — how many companies (default 10 if unspecified).
- **Field / track focus** — e.g. "AI/software", "data", "medtech software". If absent, use both
  tracks from `system/config/profile.yml`.
- **Recency** — "this week" → posting age ≤ 7 days; otherwise use the `filters` in
  `system/config/portals.yml`.

## Preconditions
1. **Read `context/` — all of it, plus `context/files/`.** It sets the search (`07-preferences.md`),
   the eligibility filter (`01-basics.md`), and the project bank every signature project is drawn
   from (`04-projects.md`). A batch run against unread context produces ten near-identical resumes.
2. If `context/` has changed since `system/profile/` was last built, re-run `profile-intake` first —
   `context/` wins on any disagreement.
3. If `system/profile/master-profile.md` still has `{{TOKEN}}` placeholders, **stop**, and offer to
   interview the user and fill `context/` for them — a resume from an unfilled profile is a
   fabricated resume.
4. Load `system/data/applied-companies.md` plus the hard limits and companies-to-skip in
   `context/07-preferences.md`. Nothing on those lists may appear anywhere in the output.

## Pipeline

### 1. Discover (scan)
Run `system/modes/scan.md`: career pages first, then the Ireland `search_queries`. Gather at least ~1.5×N
candidates so there are enough survivors after verification.

### 2. Verify every link (mandatory)
Run the `verify-job-url` skill on every candidate. **Drop `EXPIRED` / `BROKEN`. A link you could
not verify is `NEEDS_CHECK` and does not count toward N.** Only live, verified listings proceed.
This is what makes the "working links" promise real.

### 3. Score and rank
Score each with the `system/modes/_shared.md` weights (skill 35 / competition 25 / eligibility 20 /
company 10 / recency 10). Eligibility failures (no right to work, wrong location) score 0 and are
listed separately — never silently dropped. Keep the top **N**.

### 4. Tailor one resume per company (the batch loop)
For each of the N companies, run the full `resume-tailor` pipeline — research, tailor, audit,
upskilling plan — not just the tailoring step:

- **Research** the company (`system/modes/deep.md`, short form is fine at batch scale) → `output/NN_Company_Role/research.md`.
  The demand map (§6) is the part that matters most here.
- Classify the track, select the JD-relevant slice from the knowledge base, reframe the best
  projects, write the complete `.tex`.
- **Assign a distinct signature project** (see §4b below).
- **Audit** it (`references/recruiter-audit.md`). At batch scale, run Pass 1 and Pass 3 in full and
  apply Pass 2's rewrite rules as you write, rather than as a separate rewrite round.
- **Write the upskilling plan** → `output/NN_Company_Role/study-plan.md`, including the signature
  project's defence brief.
- Save everything into one folder, `output/NN_Company_RoleTitle/` (sequential NN, continuing from
  what is already in `output/`): `resume.tex`, `research.md`, `study-plan.md`, `job-description.txt`.
- Collect, but do not print in full, each resume's Match Assessment — summarise it to one line
  (confidence + top gap) in the table below.

Keep numbering continuous with the folders already in `output/`.

### 4b. One distinct signature project per company (the batch's hardest constraint)
N companies must receive N **different** signature projects — the one project on each resume
positioned for that employer alone. Do this as an assignment problem across the whole batch, not
greedily one company at a time:

1. Score every project in `context/04-projects.md` against every company's demand map, using the
   `Keywords:` line of each project.
2. Assign so the **total** match is highest — the best project overall may be worth "spending" on the
   company where it is uniquely strong rather than the first one processed.
3. Record every assignment in `system/data/signature-projects.md`, excluding anything already used by
   a live application from an earlier batch.
4. **If the bank has fewer strong projects than companies, say so plainly** — do not quietly reuse
   one. Report it as: *"Your bank covers 6 of these 10 well. Four resumes ship with a weaker
   signature slot; here are four build-now projects that would cover them."* Then put a build-now
   spec in each of those four upskilling plans.
5. Never put an unbuilt project on any resume in the batch, in any tense.

### 5. One combined report
Print a single table — this is the deliverable the user asked for:

```
| # | Company | Role | Track | Posted | Score | Conf. | Apply link (verified) | Resume file | Signature project | Plan |
```

`Signature project` names the one project unique to that company; `Plan` links its
`output/NN_Company_Role/study-plan.md`.

Then, below the table:
- **What to study first** — refresh the **"What to study this week"** table in `output/SUMMARY.md`
  and print its top five: the
  skills that appear across the most of these N applications, so one week of study lifts several
  interviews at once. This is the batch's most useful output after the resumes themselves.
- **Signature project coverage** — how many companies got a strong project match, how many shipped
  weak, and the build-now projects proposed to close the difference.
- **Check your memory** — a de-duplicated list of must-haves that were missing across these JDs but
  that the candidate might actually have. "These came up repeatedly and aren't in your profile — if
  you've done any, add them to `system/profile/` and re-run to lift several matches at once." **Append each
  to `context/QUESTIONS-FOR-YOU.md`** under **Open** (`- [ ] <requirement> — came up for <Company> (<role>),
  <YYYY-MM-DD>`), skipping anything already listed — one batch often surfaces the same gap several
  times, and the ledger keeps it to a single line.
- **Append** each row to **"Your resumes"** in `output/SUMMARY.md` at status 🔵 ready to send, with
  the folder name, match score and verified apply link. Update the `Last run:` line.
- **Log** the batch in `system/data/scan-history.tsv`.

## Resumability & scale
- If N is large (say > 12), tell the user you will do the first batch and can continue — quality per
  resume matters more than volume.
- If a single company's tailoring fails, mark that row `resume: FAILED — retry` and continue; one
  failure never aborts the batch.
- The user still reviews and submits each application themselves — this mode prepares, it does not
  auto-apply.

## Honesty gates (every row)
- Never invent or guess an apply link. Unverifiable = excluded.
- Never surface a company on the applied list.
- Never fabricate a resume fact to raise a match — raise it under "Check your memory" instead.
- Never put an unbuilt project on a resume to fill a signature slot. A weak slot plus a build-now
  spec is the honest answer; an invented project ends the process at the first technical question.
- Never move an upskilling-plan skill onto a resume. The plan is for the interview weeks away, not
  for the page going out today.
