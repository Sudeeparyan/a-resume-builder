# Porting the Template's newer features (October 2026)

Source: `C:\Users\sudee\Desktop\Template` (commit f933373, 8 Oct 2026, plus its uncommitted
Kimi/task-execution edits). Annie's app stays the base: her US-only rules, sponsorship gate,
never-re-apply memory, one-page US Letter contract, signature projects, study plans, Kimi and
Antigravity runtimes, sponsor boards and Sponsorship Tracker are kept. Not ported: multi-person
profiles and onboarding (`profiles.py`, `dashboard/shell.py`, `services/intake/`,
`source_library.py`), Ireland permit data (`countries/ie`, `permits/`, EURES), the demo profile
and evals.

Baseline before the port: 528 backend tests passed, 6 skipped.
Code snapshot before the port: session scratchpad `annie-code-before-port.tgz`.

## Phases

1. **AI agents**: Auto router across her plans with usage-limit rests (`ai/router.py`,
   `ai/limits.py`), tracing of agent runs (`telemetry/`), one AI call at a time per plan
   (`services/task_execution.py`), paid-call gate (`services/agent_cache.py`), persona,
   updated specialists, the route panel in Settings and run timelines in Agents.
2. **Job pipeline**: each job end to end (`services/pipeline.py`), fit check (`services/fit.py`),
   ready-to-submit verdict (`services/readiness.py`), Needs you (`services/needs_you.py`).
3. **Documents**: evidence-checked cover letters, Word copies, the rewrite guard, AI-mark cleanup.
4. **UI**: styles, phone navigation, question cards, week plan, self-recovering pages.

## Status

- [x] Phase 1 (9 Oct). Ported: `ai/router.py`, `ai/limits.py`, `ai/persona.py` (returns None:
  her specialists keep her own wording), `context_local.py`, `telemetry/`,
  `services/task_execution.py`, and the Template's `ai/catalog|codex|claude_code|keys|models.py`,
  `services/agent_cache.py`, `services/observability.py` (her Assurance count kept). Merged by
  hand: `ai/__init__|providers|settings.py`, `ai/agents/graph|schemas|specialists.py` (Antigravity
  kept as a fourth free plan; her job tailor keeps the 60/40 verified/predicted plan; her four
  older posting specialists kept; Kimi keeps her two sign-in fixes), `services/agents.py`
  (tracing, buffered live trace, the plan that answered, metering; the Template's durable task
  retries were not taken), `services/assistant.py` (`more_calls`, backup notice). New API:
  `/ai/route`, `/agents/runs/{id}/trace|spans`, `/traces/runs`. UI: Auto and its route in
  Settings, paid-only limit wording, the run side panel in Agents, `api.ts` retries reads while
  the app restarts. Not taken: demo mode (it relaxes the sponsorship gate). New tests:
  `test_auto_route_limits.py`, `test_task_execution.py`, `test_context_propagation.py`,
  `tests/conftest.py`, a `more_calls` test, `AgentTrace.test.tsx`, `TraceTimeline.test.tsx`.
  Note: `daily-job-search/morning_run.py` (outside the app) still looks for "daily AI call
  budget reached"; that wording no longer appears because her plans no longer count.
- [x] Phase 2 (9-10 Oct). New: `services/pipeline.py` (Annie's sources and helpers; one job per
  company like the morning run), `services/fit.py` (role = her four tracks and entry level, place =
  US; the job card keeps discovery's own fit score), `services/readiness.py` (no demo mode or salary;
  only predicted items wait for her decision), `services/needs_you.py` (adds a signed-out AI app,
  Assurance items and open questions), migration 9 `job_fit`, `assessment.py` v6, the independent
  review's verdict (`RESUME_REVIEW_SCHEMA`, `checked_resume_review`), a discovery `count`, health
  recorded for direct calls to her plans (`router.note_direct`), research trace notes. UI: the
  pipeline builder and live progress on Daily Search, Needs you on the Dashboard, the readiness
  card and fit check in Resume Studio, `UI.tsx` (Switch, Ask the assistant, review verdict badge).
  Chat tools: `run_search_pipeline`, `search_pipeline_status`, `stop_search_pipeline`,
  `check_readiness`. Tests: `test_daily_pipeline.py` (25), `SearchPipeline/FitCheck/NeedsYou.test.tsx`.
  Not taken: follow-up search passes, the overnight hunt, durable stage records.
- [x] Phase 3 (10 Oct). New: `services/cover_letters.py` (AI draft from registered evidence, checked
  for numbers, names, never-claim skills, missing requirements, filler and immigration words incl.
  H-1B/OPT/green card/citizenship, then audited by `letter_auditor`; two failures, a failed audit or no
  AI give the template from her registered sentences; US date, "Sincerely,"; no company facts because
  her research is not quote-verified), `services/docx_export.py` (Word resume and letter, US Letter;
  an empty skills label is skipped), `ai_marks.py` (hidden characters and look-alike letters cleaned in
  `tex_escape` and Studio saves; compiled PDFs keep only title and author; the validator fails on
  either). Routes: `GET /jobs/{id}/cover-letter/download?format=md|docx`, `/studio/{id}/download?format=docx`.
  UI: Download Word in Resume Studio, the shared cover letter view. Tests: `test_cover_letters.py` (13),
  `test_ai_marks.py` (3), `CoverLetterView.test.tsx`. Not taken: reworded project bullets
  (`rewrite_guard.py`): her tailor copies verified items word for word and her validator checks them
  verbatim; loosening that is her decision.
- [x] Phase 4 (10 Oct). App shell from the Template: the phone bar shows Chat, Dashboard, Search and
  Resumes with a More sheet for the rest (`components/PhoneNav.tsx`), a failed page recovers once by
  itself and is keyed by tab, a slower summary read never replaces a newer one (`latestRequest.ts`),
  "Ask the assistant" menus hand a question to the chat (`AskContext`, the Assistant's `asked`).
  Styles: a rule-level three-way merge against the Template's first commit took the Template's
  updates only where Annie had not changed a rule, plus 54 new rules for elements her pages render
  (page-title wrapping, phone sheet, list toolbars, chat chips) and the component styles of Phases
  1-3. Needs you counts open questions per question, not per checkbox. The readiness route rescores
  the current PDF first, so an older scoring version's coverage is never shown as current (one real
  job: 16 under v3, 80 under v6). Checked on a disposable copy of her data at 1440 and 500 px
  (Daily Search, Dashboard, Settings, Agents, Resume Studio). Tests: `PhoneNav.test.tsx`,
  `latestRequest.test.ts`, `selfHealing.test.ts`, `AutoRoute.test.tsx`. Not taken: the Template's
  chat project rail, file attachments, question cards and week-plan refactor (they rely on its
  multi-person intake).

## After the port

- Restart the dashboard (it was running the old code during the port); migration 9 (`job_fit`)
  applies on start, and the fit backfill gives every open job its requirement check (rules only).
- In Settings, consider choosing **Auto**: Kimi, then Codex, Claude Code and Antigravity, so a
  signed-out or exhausted plan no longer stops tailoring and study plans.
