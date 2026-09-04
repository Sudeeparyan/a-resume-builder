---
description: Find sponsorship-safe US jobs and build a tailored one-page resume (LaTeX + PDF) for each
argument-hint: "[count] [track|remote|cap-exempt|role title]"
---

# /hunt — the whole loop, one command

Arguments: `$ARGUMENTS` (may be empty)

Parse them loosely:
- a bare number → how many applications to prepare (default **10**)
- `remote` → Remote (US) only
- `cap-exempt` → universities, national labs, nonprofit research, academic medical centers only
- anything else → treat as a role/track filter (e.g. `data engineer`, `embedded`)

Run every step. Do not ask permission between steps — she asked for the whole thing.

---

## 1. Load the facts

Read `context/` — all nine files plus `QUESTIONS-FOR-YOU.md`. Then `system/profile/`,
`system/config/profile.yml`, `portals.yml`, `regions.yml`, `sponsorship.yml`, and
`system/modes/_shared.md` → `_profile.md`.

She is on **active F-1 OPT**: authorized to work now, needs H-1B later.

## 2. Clear the exclusions

```
python system/scripts/track.py --age
python system/scripts/track.py --exclusions
```
Nothing on that list may appear anywhere in the output.

## 3. Find roles

Follow `.claude/skills/job-hunter/SKILL.md` Step 1. Gather **~1.5×** the target count, because
the gate will cut some.

Unless the arguments narrow it, use the batch mix from `profile.yml`:
**4 Data · 2 ML/AI · 2 Software · 2 Embedded**.

Always include a cap-exempt pass and the sponsorship-positive queries.

## 4. Pull the full JD for each

`mcp__claude_ai_Indeed__get_job_details`, or fetch the ATS posting. Save each to
`job-description.txt` in that application's folder.

## 5. Gate on sponsorship

```
python system/scripts/sponsor_check.py --jd <jd.txt> --company "<name>" --json
```

Drop `EXCLUDED`. Keep everything else, including tier `C`. Record the triggering sentence for
every exclusion.

## 6. Verify the link

```
python system/scripts/verify_job_url.py --url "<url>"
```
Drop dead links.

## 7. Rank and pick

Order by tier (**S → A → B → C**), then score. Take the top N **distinct companies**.

## 8. For each company, build the application

Folder: `output/Annie_Manoharan_<Company>_<NN>/`
`<Company>` = name with spaces and punctuation stripped. `<NN>` = zero-padded, continuing from
what's already in `output/`.

1. **Research** the company → `research.md` (`system/modes/deep.md`). Mandatory, every time.
2. **Pick the signature project** — one per company, never reused. Check and update
   `system/data/signature-projects.md`.
3. **Tailor** from `system/templates/latex/resume-track-*.tex` using only facts in `context/`.
   Obey the do-not-claim list in `system/profile/master-profile.md`.
4. **Recruiter audit**, three passes (`references/recruiter-audit.md`).
5. Write it to `Annie_Manoharan_<Company>_<NN>.tex`.
6. **Build and verify one page:**
   ```
   python system/scripts/build_pdf.py output/Annie_Manoharan_<Company>_<NN>/Annie_Manoharan_<Company>_<NN>.tex
   ```
   If it fails on page count, cut content in the order the script prints. **Never** shrink
   margins or fonts.
7. **ATS check:**
   ```
   python system/scripts/ats_check.py --resume <tex> --jd <jd.txt>
   ```
8. **Study plan** → `study-plan.md` (`system/modes/upskill.md`).
9. **Record it:**
   ```
   python system/scripts/track.py --add --company "X" --role "Y" --url "..." \
       --tier <T> --score <N> --track <track> --folder Annie_Manoharan_X_NN
   ```

## 9. Write the summary

Update `output/SUMMARY.md` — every section in `CLAUDE.md → Output conventions`, including
**Excluded** with the triggering sentence for each.

```
python system/scripts/track.py --sync-applied-companies
```
Append a row to `system/data/scan-history.tsv`.

## 10. Report back

Print the table:

| # | Company | Role | Tier | Score | Location | Folder | Apply |

Then, briefly:
- how many were found, kept, and excluded — **and why they were excluded**
- the honesty line from `sponsorship.yml → disclaimer`
- the single skill most of these roles wanted that she doesn't have yet
- **one plain next step**

---

## Non-negotiable

- Both a **`.tex`** and a **`.pdf`** in every folder. The PDF to send, the LaTeX to edit in
  Overleaf. Neither is optional.
- **Every resume exactly one page.** Verified, not assumed.
- **Ten companies means ten different signature projects**, not one resume with the name changed.
- Never surface an excluded, applied-to, or rejected company.
- Never invent a listing, a link, or a fact.
- If you can only find fewer than asked, say so and say why. Do not pad.
