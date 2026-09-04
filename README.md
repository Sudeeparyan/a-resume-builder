# Resume Builder — USA Edition

An AI-driven job-search workspace for one person. You put your background into `context/`, ask in
plain English, and get a resume tailored to each job — plus company research, a study plan, and a
tracker.

### 👉 **New here? Read [START_HERE.md](START_HERE.md).** That's the whole system in three steps.

---

## Three folders

```
├── context/     📥 YOURS — everything about you. The only folder you touch.
├── output/      📤 SUMMARY.md (what the system did) + one folder per application.
└── system/      ⚙️  The machinery. Ignore it.
```

| Folder | Contents |
|--------|----------|
| **[context/](context/)** | `01-basics` · `02-education` · `03-experience` · `04-projects` · `05-skills` · `06-achievements` · `07-preferences` · `08-voice` · `09-anything-else` · `files/` for CVs and transcripts · `QUESTIONS-FOR-YOU.md` where the AI asks you things |
| **[output/](output/)** | **`SUMMARY.md`** — one page: resumes made, companies found, what was skipped and why, what to study · plus `NN_Company_Role/` per application (resume, research, study plan, cover letter, the job ad) |
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
"Give me 10 companies in Ireland this week with working links, and a resume for each"
<paste a job ad>   →  one tailored, screening-software-ready resume + an honest match assessment
```

## Requirements

Any AI coding assistant — Claude Code, GitHub Copilot, or Codex — opened in this folder. Any model.
No API key. The scripts in `system/scripts/` are Python standard library only.

## The market is pre-set to Ireland

Job boards, hubs, work-permit routes (Critical Skills / General Employment Permit, Stamp 1G) and CV
conventions (no photo, no date of birth) are filled in at `system/config/regions.yml`. To target a
different country, copy the `ireland:` block there and change `default_region`.

## Setup and reference

- **[START_HERE.md](START_HERE.md)** — the user guide
- **[system/SETUP.md](system/SETUP.md)** — first-run walkthrough
- **[system/DATA_CONTRACT.md](system/DATA_CONTRACT.md)** — which files are yours vs. safe to update
- **[system/PLACEHOLDERS.md](system/PLACEHOLDERS.md)** — every `{{TOKEN}}` the template uses
- **[CLAUDE.md](CLAUDE.md)** — the operating instructions the AI reads first
