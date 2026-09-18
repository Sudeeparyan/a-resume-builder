# Resume Builder — USA Edition

An AI-driven job-search workspace for one person. You put your background into `context/`, ask in
plain English, and get a resume tailored to each job — plus company research, a study plan, and a
tracker.

### 👉 **New here? Read [START_HERE.md](START_HERE.md).** That's the whole system in three steps.

---

## The folders

```
├── context/     📥 YOURS — everything about you. The only folder you touch.
├── output/      📤 SUMMARY.md (what the system did) + one folder per application.
├── system/      ⚙️  The machinery. Ignore it.
└── dashboard/   🖥️  Optional local web app. Ignore it unless you want the live editor.
```

Full map of every file and folder: **[STRUCTURE.md](STRUCTURE.md)**.

| Folder | Contents |
|--------|----------|
| **[context/](context/)** | `01-basics` · `02-education` · `03-experience` · `04-projects` · `05-skills` · `06-achievements` · `07-preferences` · `08-voice` · `09-anything-else` · `files/` for CVs and transcripts · `QUESTIONS-FOR-YOU.md` where the AI asks you things |
| **[output/](output/)** | **`SUMMARY.md`** — one page: resumes made, companies found, what was skipped and why, what to study · plus `Annie_Manoharan_<Company>_<NN>/` per application — each holding `resume.tex`, `resume.pdf`, `job-description.txt` and `audit.md` |
| **system/** | `config/` · `modes/` · `profile/` (the tidied knowledge base built from your context) · `templates/` · `scripts/` · `SETUP.md` |

Skills and agents live in `.claude/skills/` and `.github/agents/` — hidden, and read automatically.

## What makes it different from pasting a CV into a chatbot

1. **It can't invent anything.** Every claim traces to a line you wrote in `context/`. Missing facts
   are reported as gaps, never filled with plausible text.
2. **Ten companies get ten different resumes** — each leading with a different project of yours,
   chosen for that employer after researching them.
3. **A hard wall between the resume and the study plan.** What you have goes on the page; what you
   don't goes into `study-plan.md` for the interview weeks later. Never hedged onto the resume.
4. **It compounds.** Add a fact to `context/` once and every future resume can use it.

## Two things you'll actually type

```
/hunt              →  10 sponsorship-safe US jobs + 10 tailored one-page resumes (LaTeX + PDF)
<paste a job ad>   →  one tailored, screening-software-ready resume + an honest match assessment
```

Every prompt worth knowing is in **[PROMPTS.md](PROMPTS.md)**.

## Requirements

Any AI coding assistant — Claude Code, GitHub Copilot, or Codex — opened in this folder. Any model.
No API key. The scripts in `system/scripts/` are Python standard library only.
LaTeX builds locally via Tectonic at `system/bin/tectonic.exe`; the `.tex` files also compile on
Overleaf unchanged.

## The market is the United States, and only the United States

Job boards, hubs, salary bands and resume conventions (one page, no photo, no date of birth) are
in `system/config/regions.yml`. A role outside the US is not searched for, ranked, or listed.

## The sponsorship rule

| The posting says | What happens |
|---|---|
| Explicitly **won't sponsor** | **Excluded.** Never shown. |
| **Says nothing** | **Shown** — most postings, and where most offers come from. |
| Explicitly **will sponsor** | Shown, ranked top. |
| Needs citizenship / clearance / ITAR | **Excluded** — cannot hire you regardless. |

Ranking: **S** cap-exempt (no H-1B lottery) → **A** says yes → **B** proven sponsor → **C** silent.

A company having no H-1B record is **not** a reason to skip it. Rules and patterns live in
`system/config/sponsorship.yml`; the local sponsor index is 83,624 employers from USCIS FY2021–2023.

## It never lets you apply twice

`system/data/applications.tsv` tracks every application. Same company + same role is never
surfaced again; a company that rejected you disappears for 180 days. Just say
*"I got rejected by X"* and it updates.

## Setup and reference

- **[START_HERE.md](START_HERE.md)** — the user guide
- **[system/SETUP.md](system/SETUP.md)** — first-run walkthrough
- **[system/DATA_CONTRACT.md](system/DATA_CONTRACT.md)** — which files are yours vs. safe to update
- **[system/PLACEHOLDERS.md](system/PLACEHOLDERS.md)** — every `{{TOKEN}}` the template uses
- **[CLAUDE.md](CLAUDE.md)** — the operating instructions the AI reads first
