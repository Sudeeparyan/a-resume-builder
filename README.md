# Career workspace (Annie's resume builder, now for more than one person)

A local job-search and resume workspace. It started as **Annie Prasanna Manoharan**'s (United States only) and now holds any number of **profiles**, each a completely separate workspace built from that person's own documents.

For each profile it finds entry-level roles in that person's target country; drops any posting that refuses the work permit they need or requires a citizenship or clearance they don't have (and shows the exact sentence, so a wrong call can be undone); never lets them apply to the same role twice; and builds one-page resumes (US Letter or A4) that use only facts from their own files, each with a study plan for the interview weeks.

## Start

Double-click **Start Dashboard.cmd** on Windows (**Start Dashboard.command** on a Mac). It sets itself up on first run, lists which AI apps it found (Claude Code, Codex, Kimi Code, any API keys) and whether the PDF compiler is installed, and opens the dashboard at http://127.0.0.1:8010 (port 8000 on the Mac is a different person's dashboard; this app never uses it). If the dashboard is already running from older code it restarts it, so you always get the newest version, but never while a search is in progress. Keep the window open; closing it stops the app. `Start Dashboard.cmd --restart` forces a restart.

On **Daily Search**, pick how many jobs, where to look, which AI does the work and which helpers run for each job (company research, tailored resume, study plan, one-page PDF). The default AI is **Auto**: your Kimi Code, Codex and Claude plans first (they cost nothing extra), moving to the next when one reaches its 5-hour limit, and Azure (paid) only when all three are out. The page shows the time, tokens, AI calls and how much of each plan's 5-hour limit the search will use before you press **Start search**.

Or open this folder in any AI app (Claude Code or Cowork, Codex, Kimi Code) and ask: "find me jobs", paste a job description, or "give me 10 companies" (Annie's profile). Every app follows the same rules, [AGENTS.md](AGENTS.md), uses the same skills in `.agents/skills/`, and works on the same database, so when one app's limit runs out another can carry on.

## Profiles

- **Annie** is the default and the **locked backup** profile: http://127.0.0.1:8010/p/annie/. Her data stays in `career-dashboard/data/` and can never be reset or deleted.
- **Add someone**: click the profile name at the top left → **New profile**, name it, then upload their Word or PDF documents (resume, "about me", project write-ups, interview answers). The AI reads every line, shows what it found (and that every part of the documents is accounted for), you correct the essentials (contacts, country, work permission, target roles) and press **Build my workspace**. Their Profile page, evidence registry, base resume, job-search rules and agents are then built from those documents only, and a daily search task is set up for them.
- **Countries**: United States and Ireland today (`career-dashboard/backend/countries/`). Ireland means A4 CVs, Irish/UK spelling, Irish locations only (not Northern Ireland) and a work-permit gate (EU/EEA-only, Stamp 4 or "no permit sponsorship" postings are set aside with their sentence).
- **Reset / Delete**: Settings → *This profile*. Both warn that the process cannot be reverted and need the profile's name typed in full. Reset erases everything and starts again from documents; Delete removes the profile and its daily task.
- Other people's profiles live in `career-dashboard/profiles/<id>/` and are **kept out of git**.

## Folders

```text
career-dashboard/   the app: React dashboard, FastAPI backend, agents, validators, tests
  data/context/       Annie's own files (01–09, her 14 resume PDFs), the evidence registry, open questions
  data/output/        SUMMARY.md (the front page) and one folder per application
  profiles/<id>/      every other profile: the same data/ layout, its own AGENTS.md and daily-job-search/
  backend/countries/  country packs (us, ie): locations, work-permit gate, paper, spelling
daily-job-search/   daily-run helpers (morning_run.py --profile <id>), the PDF runtime wrapper, Annie's history
backup/             the workspace before the 18 Sep 2026 port (reference only)
AGENTS.md           the one set of rules every AI app reads
.agents/skills/     hunt, job-hunter, resume-tailor, profile-intake, interview-prep, verify-job-url (Annie's)
career.cmd, career  one command for every AI app: `.\career.cmd help` (Windows) or `./career help`
```

Details: [career-dashboard/README.md](career-dashboard/README.md). Health check: double-click **Check Workspace.command**.
