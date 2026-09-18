Current system: [Agent architecture and end-to-end workflow](docs/AGENT-ARCHITECTURE.md).

# Annie's Career Workspace

Annie Prasanna Manoharan's US job-search and resume workspace. It finds entry-level data, ML/AI, software and embedded roles, drops every posting that refuses visa sponsorship or requires citizenship or a clearance, never lets her apply to the same role twice, and builds one-page resumes from her real evidence only.

Policy lives in [AGENTS.md](AGENTS.md). Her own facts live in [data/context/](data/context/); open questions are in [QUESTIONS-FOR-YOU.md](data/context/QUESTIONS-FOR-YOU.md).

## Start the dashboard

On this Mac, double-click **Start Dashboard.command** (in this folder or the repo root). It creates the Python environment in `backend/.venv` on first use, builds the React client, then opens http://127.0.0.1:8010. Port 8000 on this Mac belongs to a different dashboard; the launcher checks who answers on its port and never opens someone else's app. Stop the server with Ctrl+C in its Terminal window.

Manual setup:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python run.py            # http://127.0.0.1:8010; --port 8011 if taken, --no-browser to skip opening a tab
```

Needs Python 3.12, Node.js + npm (for the React client) and Tectonic (PDF builds; the launcher wires the bundle through `../daily-job-search/with_resume_runtime.py`). Research and discovery run on a signed-in Claude Code or Codex runtime, chosen in Settings; API keys for OpenAI, the Claude API, OpenRouter, Gemini or Kimi can be pasted in Settings → API keys instead. Gmail sync is optional and needs Codex signed in. The Agents tab shows every agent step by step.

## Six tabs

- **Dashboard**: saved jobs ranked by sponsorship tier (S cap-exempt → A says yes → B proven sponsor → C silent), status/notes/date editing, a tier filter, linked Gmail evidence and activity. **Excluded roles** lists every posting the gate cut, with the exact sentence that triggered it and a Restore button for a wrong call.
- **Daily Search**: weekly targets over chosen workdays (default 30 a week, Monday–Saturday, US Central time), carryover, and **Find suitable jobs** with three mixes: *Default*, *Balanced five* (2 startup, 1 mid, 2 large; mid/large need tier S/A/B) and *Tracked career pages* (Greenhouse/Lever/Ashby feeds from `data/config/portals.yml`, no AI call). Every lead passes the sponsorship gate and the never-re-apply check before it is saved.
- **Resume Studio**: the per-job one-page draft. **Fit to one page** ranks content for the role's track, tries 11 → 10.5 → 10pt and then cuts content in the documented order; it never goes below 10pt or touches margins. Signature and supporting project slots, chat edits (`skills:`, `skills data:`, `coursework:`, `font:`), build and score, and **Write study plan**.
- **Profile**: editable facts, skills, experience, education and projects; original sources; agent inputs. Edits pause new drafts until reconciled with the evidence registry.
- **Agents**: every run and its steps, spending limits, provider choice.
- **Settings**: providers, API keys, Gmail connector, schedules.

Open a saved job to see its tier and the reason ("Cap-exempt: .edu domain", "H-1B history: 459 approvals"), re-check sponsorship, run company research, an independent hiring-manager benchmark (it never sees Annie's profile) and a separate profile comparison.

## Daily workflow

1. **Daily Search** → *Find suitable jobs*. Excluded postings go to Excluded roles with their sentence; roles she already saw or that rejected her in the last 180 days are skipped.
2. Open a posting, read the JD, run *Company & hiring review*.
3. **Resume Studio** → *Fit to one page*, review, *Build & score*, *Write study plan*.
4. Annie applies herself, then records the date (or Gmail confirms it). Applications quiet for 21 days become *ghosted* automatically.
5. Read `data/output/SUMMARY.md`, the one-page front page: resumes, pipeline, shortlist, excluded (with sentences) and what to study this week.

## Folder map

```text
frontend/         React + TypeScript screens and component tests (npm run dev)
backend/          all Python, self-contained: .venv, run.py, requirements
  dashboard/        HTTP routes (legacy /api and /api/v2)
  services/         sponsorship gate, never-re-apply rules, portals, goals, profile, Gmail evidence, Resume Studio
  scripts/          career.py and workspace.py CLIs, resume/batch/workspace validators, fresh_start
  workflows/        discovery, tailoring, study-plan, review and interview playbooks
  ai/               providers, model catalogues, LangChain specialists
  resume_contract.py  the one-page US Letter contract every validator reads
data/             everything that is Annie's or generated
  career.db         the single mutable authority (gitignored)
  config/           profile.yml, sponsorship.yml, portals.yml, regions.yml
  context/          Annie's files 01–09, her 14 resume PDFs, evidence.yml, PROFILE.md, questions
  sponsors/         USCIS H-1B employer history (83,624 employers) and its SQLite index
  templates/        resume-base.tex and batch/evidence-map examples
  output/           SUMMARY.md, base resume, application folders
  interview-prep/   story bank
  signature-projects.md  generated: which company owns which signature project
tests/            Python and API regression tests
docs/             architecture, agents, API, scoring, operations, sources
.agents/          URL-verification skill adapter
.github/agents/   agent adapters (US job hunter, resume builder, reviewers, interview coach)
```

## Build and release commands

Base resume:

```bash
backend/.venv/bin/python backend/scripts/validate_resume.py data/templates/resume-base.tex --compile --output data/output/base/Annie_Manoharan_Resume.pdf --render-dir data/output/base/resume-preview --qa-json data/output/base/qa.json
```

For a tailored application use the same command with its folder's `resume.tex`, PDF, preview and QA paths. After inspecting the rendered page, add `--visual-review pass --visual-reviewer "Your name"`.

Other commands:

```bash
backend/.venv/bin/python backend/scripts/workspace.py summary
backend/.venv/bin/python backend/scripts/workspace.py run --kind discovery --preset portals
backend/.venv/bin/python backend/scripts/workspace.py sponsor-check --company "Acme" --file JD.txt
backend/.venv/bin/python backend/scripts/workspace.py check-reapply --company "Acme" --title "Data Engineer"
backend/.venv/bin/python backend/scripts/workspace.py excluded
backend/.venv/bin/python backend/scripts/workspace.py run --kind study_plan --job-id JOB_ID
backend/.venv/bin/python backend/scripts/career.py jobs
backend/.venv/bin/python backend/scripts/career.py prepare JOB_ID
backend/.venv/bin/python backend/scripts/career.py preview JOB_ID
backend/.venv/bin/python backend/scripts/validate_workspace.py
backend/.venv/bin/python -m pytest tests -q
backend/.venv/bin/python .agents/skills/verify-job-url/scripts/verify_job_url.py --url 'https://careers.company.com/specific-posting'
```

`backend/scripts/fresh_start.py --yes` empties the job list for a new search after snapshotting everything into `../backup/<date>-fresh-start/`. It keeps the never-re-apply memory, the excluded log and the signature assignments.

## Backups

The workspace before this port (old `system/`, `dashboard/`, `output/`, root docs and agent files) is in `../backup/2026-09-18-pre-port/`. Nothing there is read by the app. Its two prepared applications (USC, Databricks) were re-saved through the sponsorship gate and rebuilt as fresh one-page drafts; the old PDFs stay in the backup because they predate the Q1 and Q4 answers.

From the repo root, `Check Workspace.command` runs the backend tests, workspace and layout checks, the React build and component tests.
