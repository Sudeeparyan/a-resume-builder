# Annie's career workspace

This folder has two active workflows, `career-dashboard/` (the app) and `daily-job-search/` (daily runs), plus `backup/` (preserved history, never an active template or current profile).

Always read `career-dashboard/AGENTS.md` before candidate or resume work. It is the single policy source. Annie's own files in `career-dashboard/data/context/` and the evidence registry `career-dashboard/data/context/evidence.yml` are the only current candidate authorities.

## The three rules that shape everything

1. **Sponsorship.** A posting that says it will not sponsor, or that requires US citizenship, permanent residency, a security clearance, ITAR/EAR or US-person status, is never listed; it is logged with the sentence that excluded it. A posting that says nothing is shown. She is on F-1 OPT and authorized to work now.
2. **Never re-apply.** Same company and role never again; a rejection hides the company for 180 days; 21 quiet days after applying means ghosted, and the company is open again after 90 days for a different role only.
3. **One page, real facts.** Every resume is exactly one US Letter page with a signature project unique to that company. Never a years total, never a publication until Q3 is detailed, never a study-plan skill or an unbuilt project — with one review-gated exception: per-company tailoring may propose predicted Projects/Skills items (stored with origin `predicted`, kept or removed in the Assurance tab before applying); experience, education and personal details are never fabricated.

## Continue work from a chat

Read `WORKSPACE-STATE.md`, then:

```sh
career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/workspace.py summary
career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/career.py jobs
career-dashboard/backend/.venv/bin/python career-dashboard/backend/scripts/career.py activity
```

The dashboard and the chat update the same `career-dashboard/data/career.db` through `career.py` / `Workspace` or `workspace.py` / `CareerServices`; never keep a second status list. Use exact job IDs; if Annie names an ambiguous employer or role, ask which posting. Record a submission only from her explicit confirmation or a verified matching email, and keep the date she states.

For a daily search follow `daily-job-search/DAILY_BRIEF.md`; a scheduled task ("Annie Daily Job Search", daily 07:00) already runs discovery + tailoring automatically via `daily-job-search/morning_run.py` — check its `logs/` and `<date>/MORNING-REPORT.md` before starting a duplicate manual run. For "give me 10 companies" use `/hunt` (`.claude/commands/hunt.md`). Application folders live once, under `career-dashboard/data/output/applications/Annie_Manoharan_<Company>_<NN>/`.

After meaningful work, update `WORKSPACE-STATE.md` with what changed, what is unresolved and the next action. Run `./Check Workspace.command` after code changes. Use disposable workspaces for tests. Never submit applications or contact anyone without Annie's explicit go-ahead.

## Who you are working for

Annie is not a developer. You run everything, explain in one plain sentence before and after each step, ask like a person rather than a form, confirm before anything hard to undo, and finish with one plain next step.
