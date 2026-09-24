# Annie's career workspace

This is Annie Prasanna Manoharan's US job-search workspace, and this file is the **one set of rules for every AI app** that opens it: Claude Code and Claude Cowork, Codex, Kimi Code, Copilot, or anything else that reads `AGENTS.md`. There is no `CLAUDE.md` and no tool-specific copy; if an app does not load this file by itself, tell it "read AGENTS.md first".

The folder has two active workflows, `career-dashboard/` (the app) and `daily-job-search/` (daily runs), plus `backup/` (preserved history, never an active template or current profile).

Always read `career-dashboard/AGENTS.md` before candidate or resume work. It is Annie's full policy (the sponsorship rule, never re-apply, the one-page contract, the wall between resume and study plan, and how to work with her), and the app reads it too. Her own files in `career-dashboard/data/context/` and the evidence registry `career-dashboard/data/context/evidence.yml` are the only current candidate authorities. Never write to `data/context/` except `QUESTIONS-FOR-YOU.md`, or when she asks you to record something; then say exactly which file changed.

## Profiles

The dashboard holds several profiles, each a completely separate workspace (its own documents, database, jobs, resumes, chats, AI settings, gates and daily search). Nothing is shared between them except the code and this PC's AI keys and plans.

- **Annie (`annie`) is the default, the backup profile, and locked**: she can never be reset or deleted. Her data stays in `career-dashboard/data/`; everything else in this file and `career-dashboard/AGENTS.md` is her policy, and the skills below are hers. Her page: http://127.0.0.1:8010/p/annie/.
- **Every other profile** lives in `career-dashboard/profiles/<id>/` (kept out of git; the registry is `profiles/registry.json`). It is built from the person's own uploaded documents on its page (http://127.0.0.1:8010/p/<id>/), in the setup chat by default (attach or paste, then questions one at a time, then *Build my workspace*; `backend/services/intake/interview.py`) or the review form, has its own policy in `career-dashboard/profiles/<id>/AGENTS.md`, its own country pack (`career-dashboard/backend/countries/<code>/`: United States or Ireland today) and its own daily task ("Career Daily Job Search - <name> (<id>)").
- The commands take `--profile <id>` (default `annie`); `validate_resume.py` takes `--workspace <profile folder>`.
- When a request is about someone other than Annie, work only in that profile's folder and follow its `AGENTS.md`. Never copy a fact, job or file from one profile to another.

## The three rules that shape everything

1. **Sponsorship.** A posting that says it will not sponsor, or that requires US citizenship, permanent residency, a security clearance, ITAR/EAR or US-person status, is never listed; it is logged with the sentence that excluded it. A posting that says nothing is shown. She is on F-1 OPT and authorized to work now.
2. **Never re-apply.** Same company and role never again; a rejection hides the company for 180 days; 21 quiet days after applying means ghosted, and the company is open again after 90 days for a different role only.
3. **One page, real facts.** Every resume is exactly one US Letter page with a signature project unique to that company. Never a years total, never a publication until Q3 is detailed, never a study-plan skill or an unbuilt project — with one review-gated exception: per-company tailoring may propose predicted Projects/Skills items (stored with origin `predicted`, kept or removed in the Assurance tab before applying); experience, education and personal details are never fabricated.

## One shared state, whichever AI app you are

Every AI app works on the same database, `career-dashboard/data/career.db`, through the commands below (the dashboard uses the same one). Never keep her jobs, statuses or facts in an AI app's own memory or notes, and never keep a second status list.

`WORKSPACE-STATE.md` is the handoff between sessions **and between AI apps**. Read it first. When your app's usage limit is near or reached in the middle of a task, write an "In progress" line there before you stop (what is done, the exact job IDs and folders, the next step), so the next app (Claude, Codex, Kimi) opened in this folder carries on without redoing work. After meaningful work, update it with what changed, what is unresolved and the next action.

## Commands (the same in every AI app, on Windows and Mac)

`career` below means `.\career.cmd` on Windows (PowerShell or cmd) and `./career` (or `sh career`) on macOS, Linux and Git Bash, run from this folder. Both use the app's own Python. `career help` lists everything.

```sh
career ws summary                 # what is saved, applied, excluded; today's plan
career jobs                       # saved postings with their exact IDs
career activity                   # what happened recently
career ws goals                   # today's application target
career ws run --kind discovery [--preset portals|balanced_five]   # find jobs (portals: no AI)
career ws sponsor-check --company "<name>" --file <jd.txt>        # the sponsorship gate on one JD
career ws check-reapply --company "<name>" --title "<role>"       # the never-re-apply check
career add --file <job.json>      # save a posting (runs both gates)
career prepare JOB_ID             # create the application folder
career ws run --kind research|study_plan --job-id JOB_ID
career check-resume <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir <folder>/resume-preview --qa-json <folder>/qa.json
career verify-url --url "<url>"   # is a posting still open
career update JOB_ID --status applied|interview|rejected|...      # only on her word or a verified email
career ws ai-status               # the AI route, which plans are resting, paid calls left
career check                      # the whole-workspace check after code changes
```

While the dashboard is running (double-click **Start Dashboard.cmd**, then http://127.0.0.1:8010/p/annie/), the same features are on its local API under `/p/annie/api/v2/`: `POST pipeline/run` and `GET pipeline/status` (Daily Search: count, source, AI and helpers), `POST agents/run` (one agent run), `GET ai/route` (the AI route). The 07:00 scheduled task ("Annie Daily Job Search") runs `daily-job-search/morning_run.py`; check its `logs/` and `<date>/MORNING-REPORT.md` before starting a duplicate manual run.

## Skills: what to read for each request

The skills live in `.agents/skills/<name>/SKILL.md` (Codex and Kimi Code load them from there by themselves; any other app: read the file named here and follow it).

| She asks for | Read and follow |
|---|---|
| "give me 10 companies", "hunt 10", N jobs **and** resumes, a batch of JDs | `.agents/skills/hunt/SKILL.md` |
| "find jobs", "what should I apply to", "check this company's openings" | `.agents/skills/job-hunter/SKILL.md` |
| a job description or link and a resume, cover letter or "what should I learn" | `.agents/skills/resume-tailor/SKILL.md` |
| "I built X", "I finished a course", an answer to a question in `QUESTIONS-FOR-YOU.md`, an updated CV | `.agents/skills/profile-intake/SKILL.md` |
| "I have an interview at X", practice questions | `.agents/skills/interview-prep/SKILL.md` |
| "is this posting still live", "clean up the job list" | `.agents/skills/verify-job-url/SKILL.md` |

For a daily search follow `daily-job-search/DAILY_BRIEF.md`. Application folders live once, under `career-dashboard/data/output/applications/Annie_Manoharan_<Company>_<NN>/`. Use exact job IDs; if Annie names an ambiguous employer or role, ask which posting. Record a submission only from her explicit confirmation or a verified matching email, and keep the date she states.

## AI use: free plans first, paid last

Her Kimi Code, Codex (ChatGPT) and Claude plans are already paid for and reset about every 5 hours; Azure OpenAI and API keys bill per call. The app's default AI is **Auto**, a route like OpenRouter's: **Kimi K3 → Codex (GPT-6-Astra to write, Luna to read) → Claude (Opus to write, Sonnet to read) → Azure OpenAI last**. When a plan reaches its usage limit, Auto rests it until the reset time it printed and moves to the next; Azure runs only when all three are resting or failing, and never past the daily limit on **paid** calls (free plan calls never count). Settings shows the route, how much of each plan's 5-hour window is used, and lets her reorder or switch plans off; Daily Search shows how much of each plan a search will use before it starts.

For you, the AI app reading this: never switch the app to a paid provider, add a key or raise the paid limit without her go-ahead, and never spend paid calls while a free plan has room. If your own plan runs out mid-task, hand over through `WORKSPACE-STATE.md` (above).

## Who you are working for

Annie is not a developer. You run everything, explain in one plain sentence before and after each step, ask like a person rather than a form, confirm before anything hard to undo, and finish with one plain next step. Never submit applications or contact anyone without her explicit go-ahead. Run `career check` after code changes, and use disposable workspaces for tests.
