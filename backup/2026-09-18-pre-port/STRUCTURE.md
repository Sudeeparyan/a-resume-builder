# Where everything lives

One page. If you are looking for a file, it is on this page.

**You only ever edit `context/`.** Everything else is either produced for you, or machinery.

---

## The four folders

| Folder | Whose | Open it? |
|--------|-------|----------|
| **`context/`** | **Yours.** Every fact about you. | **Yes — this is the only one.** |
| `output/` | Produced for you: resumes, PDFs, the summary page. | To read and to send. Never to edit. |
| `system/` | The machinery: rules, templates, scripts, data. | No. |
| `dashboard/` | Optional local web app. | No, unless you want the live editor. |

---

## `context/` — yours

```
context/
  01-basics.md            identity, contact, work authorisation
  02-education.md         degrees and modules
  03-experience.md        jobs, internships, research roles
  04-projects.md          the project bank (P1–P10)
  05-skills.md            skills at three honesty levels
  06-achievements.md      certs, awards, publications
  07-preferences.md       target titles, locations, hard limits
  08-voice.md             tone, and the banned-words list
  09-anything-else.md     what each of the 14 old resumes proves
  QUESTIONS-FOR-YOU.md    open questions — you answer, the AI asks
  files/                  your 14 original resume PDFs (the raw source)
```

Nothing outside this folder may become a claim on a resume. If a fact is not in here, it does
not exist.

---

## `output/` — what you get back

```
output/
  SUMMARY.md                          <- THE ONE PAGE. Start here.
  Annie_Manoharan_<Company>_<NN>/     one folder per application
  project-pack/                       generated export for ChatGPT/Claude projects
  project-pack.zip                    the same thing, zipped
```

### Inside every application folder

The **folder name** carries the company and the number. The **files inside are always named the
same** — every tool opens them by these exact names, so they are never renamed per company.

| File | What it is |
|------|-----------|
| `resume.pdf` | **Send this one.** |
| `resume.tex` | Edit this in Overleaf if you want to change something. |
| `job-description.txt` | What you were matched against. |
| `audit.md` | Which experience and project were chosen, and why. |
| `research.md` | What the company actually does. *Needs an AI key.* |
| `study-plan.md` | What to learn before they call. *Needs an AI key.* |
| `cover-letter.md` | Only if you ask for one. |

`<NN>` counts **per company** — a second Databricks application is `..._Databricks_02`.

### Right now

| # | Folder | Company | Role | Tier |
|---|--------|---------|------|------|
| 1 | `Annie_Manoharan_USC_01` | University of Southern California | Research Engineer (CIC, neuroimaging ML) | **S** cap-exempt |
| 2 | `Annie_Manoharan_Databricks_01` | Databricks | AI Engineer — FDE | **B** proven sponsor |

---

## `system/` — the machinery

```
system/
  config/
    sponsorship.yml     the sponsorship gate: patterns, tiers, exclusions
    profile.yml         the structured profile
    regions.yml         US job boards and hubs
    portals.yml         ATS portals
  data/
    applications.tsv        THE RECORD — every application, and who said no
    applied-companies.md    generated from the above — never hand-edit
    signature-projects.md   which project led which resume
    company-notes.md        free-form notes per company
    scan-history.tsv        a log of every scan
    sponsors-uscis.csv      83,624 USCIS sponsor records
  modes/            how to score, research, batch, upskill
  profile/          the tidied knowledge base built from context/
  templates/        LaTeX and markdown templates
  scripts/          the command-line tools (see below)
  bin/tectonic.exe  the LaTeX engine (gitignored, 50 MB)
```

### The scripts

| Script | What it does |
|--------|-------------|
| `track.py` | Add an application, record a rejection, check before re-applying. |
| `sponsor_check.py` | Run the sponsorship gate on one job ad. |
| `build_pdf.py` | Compile a `.tex` and assert it is one page. |
| `ats_check.py` | Keyword coverage against a job ad. |
| `verify_job_url.py` | Is this posting still live? |
| `doctor.py` | Health check. Exit 0 means healthy. |
| `export_project_pack.py` | Rebuild `output/project-pack/`. |
| `sponsor_data_refresh.py` | Refresh the USCIS sponsor data. |
| `init_profile.py`, `pack_skill.py` | Setup helpers. |

---

## `dashboard/` — the optional web app

Start it with `python dashboard/run.py`, then open `http://127.0.0.1:8000`.

```
dashboard/
  run.py            start here
  cli.py            the same thing without a browser (brief / pack / schedule / status)
  backend/
    paths.py            the ONLY file that knows where the workspace is
    settings.py         configuration and the API key
    db.py               SQLite: a cache and a run log, never the authority
    models.py           the shared data shapes
    legacy.py           bridge to system/scripts/*.py
    main.py             the FastAPI app
    scheduler.py        the daily brief timer
    api/routes.py       every HTTP endpoint
    agents/             composer, builder, deterministic gates, prompts
    services/           fact bank, honesty guards, LaTeX, Tectonic, job sources
    orchestrator/       the pipeline, live events, ETA
    llm/                Anthropic / OpenAI-compatible / Claude CLI / none
  frontend/         React + CodeMirror + pdf.js
  tests/            pytest suite (102 tests) and four runnable probes
  data/             the database and backups — gitignored, safe to delete
  .env              your API key — gitignored, never committed
```

**The database is disposable.** Delete `dashboard/data/` and the app rebuilds it. Nothing that
matters lives there — `context/`, `output/` and `system/data/applications.tsv` are the truth.

---

## The files at the top

| File | For |
|------|-----|
| **`START_HERE.md`** | **You. Read this first.** |
| `PROMPTS.md` | Every prompt worth typing. |
| `README.md` | What this project is. |
| `STRUCTURE.md` | This page. |
| `CLAUDE.md` | The operating rules the AI reads first. |
| `AGENTS.md` | The same contract for any other AI coding tool. |
| `CODEX.md`, `GEMINI.md` | Four-line pointers to `AGENTS.md`. |

`CLAUDE.md`, `AGENTS.md`, `CODEX.md` and `GEMINI.md` must stay at the top level — each tool
looks for its own file there by name.

Hidden but active: `.claude/skills/` (the skills), `.github/agents/` (the same for Copilot).

---

## The two rules that decide everything

1. **The honesty wall.** If it is not in `context/`, it never reaches a resume — not hedged, not
   as "familiar with". A skill in a study plan is a skill you do not have yet.
2. **The sponsorship gate.** Silence about sponsorship is a *keep*. Only an explicit refusal, or
   a citizenship / clearance / ITAR requirement, rules a job out.
