# API v2

All paths are under `/api/v2`, served on loopback only. Cross-origin requests
are refused. Nothing here returns a key value.

## AI settings

| Method | Path | Purpose |
|---|---|---|
| GET | `/ai/settings` | Providers, whether each has a key, its live model list, tier choices, and the agent roster. `?refresh=true` refetches model lists. |
| PUT | `/ai/settings` | Save the writing and reading tier choices: `{"tiers": {"strong": {provider, model}, "cheap": {...}}}`. |
| POST | `/ai/settings/test` | Make the smallest real call with `{provider, model}`; returns `ok` and a plain-language `detail`. |

The older `/ai/providers`, `/ai/preferences` and `/ai/test` remain for the Codex path.

## Postings and employers

| Method | Path | Purpose |
|---|---|---|
| POST | `/jobs` | Save a posting. Order: sponsorship gate → duplicate check → never-re-apply check → save. Returns `{"excluded": true, "reason", "reason_label", "sentence", "record"}` when the posting refuses sponsorship or requires citizenship/clearance (nothing is saved; it goes to the excluded log); `{"blocked": true, "rule", "note"}` for `same_role`, `rejected_180` or `ghosted_90`; `{"job", "duplicate": true}` for a repeat; otherwise the saved job (with `sponsor_tier` and `sponsor_evidence`) plus `relevance` (score, eligibility, blockers). |
| GET | `/excluded` | The excluded log, newest first, each with the triggering sentence and source (`manual`, `discovery`, `portals`, `sweep`, `recheck`, `cli`). `?include_restored=true` includes restored rows. |
| POST | `/excluded/{id}/restore` | A wrong exclusion is correctable: saves the posting as a tier C job (or brings back a swept job) and marks the row restored. Later sweeps and re-checks will not exclude it again for the same sentence. 400 if already restored. |
| POST | `/jobs/{job_id}/sponsorship` | Re-run the gate on the saved description; a refusal moves the job to the excluded log. |
| POST | `/jobs/age` | Mark applications quiet for 21 days as `ghosted` (the scheduler also runs this hourly). |
| POST | `/jobs/verify-due` | Re-check open postings unchecked for 24 hours (expired ones weekly); live wording is re-gated. |
| POST | `/jobs/{job_id}/verify` | Re-check one posting now. |
| GET | `/jobs/{job_id}/verification` | Evidence history for the posting. |
| POST | `/companies/{job_id}/check` | Assess the employer: legitimacy, size, sponsorship evidence, red flags. |
| GET/PUT | `/discovery/preferences` | `default`, `balanced_five` or `portals`, persisted and read by the Daily Search screen. |

Job rows include `sponsor_tier` (`S`, `A`, `B`, `C`), `sponsor_evidence` (label, reason, sentence, cap-exempt reason, H-1B approvals and years, E-Verify, restored flag), `posting_state`, `legitimacy_state`, `size_category` and `sponsorship_state`. `/summary` adds `excluded_jobs`, `counts.excluded` and `counts.ghosted`.

## Resume Studio

| Method | Path | Purpose |
|---|---|---|
| GET | `/studio/{job_id}/assessment` | ATS readiness, resume coverage, opportunity fit, and keywords split into `missing_supported` and `missing_unsupported`. |
| GET | `/studio/{job_id}/download?format=pdf\|tex` | Attachment download. PDF requires the current compiled revision. |
| POST | `/studio/{job_id}/chat/preview` | Preview a change set. Exact commands apply directly; plain English goes to the resume tailor agent. `applies_resume_change` and `ai_note` say what will happen and why. |
| POST | `/studio/{job_id}/chat/apply` | Apply a preview at its expected revision, compile, and rescore. |
| POST | `/studio/{job_id}/chat/undo` | Restore the source revision as a new version. |
| POST | `/profile/chat/preview` | Preview profile changes; plain English goes to the profile curator agent. Always requires confirmation. |
| POST | `/profile/chat/apply` | Confirm and apply a profile preview. |

Chat mutations require `request_id` and `expected_revision`, plus
`change_set_id` for apply and undo. Reusing a request ID returns the existing
change set; a stale revision fails rather than silently rebasing.

## Assistant chat

| Method | Path | Purpose |
|---|---|---|
| GET | `/assistant` | The open conversation (`conversation_id`, its `messages` newest last, and `conversations`, the list above), the question it is waiting on (`pending`), whether a message is still `busy`, `ai_configured`, the `engine` the agent runs on (`provider`, `model`, `label`, `ready`, `moved_from`, `runs` — what the runs it starts go through — a `note` when Codex is installed but not signed in, and the `options` ready on this Mac), the agent registry with what the chat reaches (`agents`: `id`, `name`, `linked`, `tools`) and the tool groups (`capabilities`). |
| POST | `/assistant/messages` | Send `{message, request_id}` (up to 120,000 characters, so a whole posting fits). Returns 202 with the row in state `processing`; the reply, its `steps` and `data` fill in on the worker thread. The same `request_id` returns the same row. |
| GET | `/assistant/messages/{id}` | One message: `state` (`processing`, `done`, `needs_input`, `failed`), `response`, `steps` (`label`, `state`, `detail`, the `agent` it ran on, a `run_id` when it queued a run) and `data`. |
| POST | `/assistant/messages/{id}/stop` | Stop a reply in progress. The worker ends it at its next step boundary: a compile or one model call that is mid-flight finishes first, but a model decision that comes back after the stop is dropped (no tool runs, no reply shows). The running step reads *Stopping…* until then, and the message ends `failed` with `data.intent: stopped` and a reply saying that anything a finished step saved stays. The question the chat was waiting on is dropped. |
| GET | `/assistant/conversations` | Every conversation with messages, newest activity first: `id`, `title` (the first line of its first message), `count`, `started_at`, `updated_at`, `busy`, `current`. |
| POST | `/assistant/conversations` | New chat: opens a fresh conversation and returns the overview. An open conversation with nothing in it is reused. Refused (400) while a reply is being worked on. |
| PUT | `/assistant/conversations/{id}` | Open an earlier conversation (returns the overview). The question the current one was waiting on is dropped. Refused while a reply is being worked on. |
| DELETE | `/assistant/conversations` | Clear the chat history: every conversation and its messages, for good; a fresh conversation opens. Refused (400) while a reply is being worked on. Returns the overview. |
| DELETE | `/assistant/conversations/{id}` | Delete a conversation and its messages for good; the jobs, resumes and profile changes it produced stay. Deleting the open one opens the most recent other conversation, or a fresh one. Returns the overview. |

Two paths. A pasted posting (or a lone link, fetched first) is handled without a model: fields from labelled lines or the cheap `posting_parser` (values not in the text are dropped), then `save_posting` (sponsorship gate, duplicates, never-re-apply), `studio.open`, `studio.fit` and the score. A `resume_ready` reply carries `job_id`, `pdf` and `preview_png` (paths under `/api/files/`), `posting_url`, `tier`, `coverage`, `ats`, `gaps` and `suggestions`. The shortcuts `find jobs`, `status`, `excluded`, `study plan for X`, `research X`, `open X` and `applied to X` (recorded only after the next message is `yes`) are also deterministic.

Everything else runs the agent loop (`services/assistant.py`): the `workspace_agent` specialist receives the workspace snapshot, the tool catalogue, the last five exchanges of the open conversation and the task transcript and returns one decision per turn — `call` a tool, `ask` her something, or `reply` — up to 14 turns per message. Tools (`services/assistant_tools.py`) wrap every feature: jobs (`list_jobs`, `get_job`, `save_posting`, `fetch_posting`, `update_job`, `remove_job`, `restore_job`, `excluded_postings`, `restore_excluded`, `recheck_sponsorship`, `verify_posting`, `find_jobs`), resume (`build_resume`, `resume_status`, `edit_resume`, `undo_resume_change`, `sync_resume_projects`, `cover_letter`, `application_documents`), agents (`run_agent` for research, resume_advisor, resume_build, resume_match and study_plan; `wait_for_run`, `agent_runs`, `run_result`), profile (`profile_overview`, `search_profile`, `get_profile_item`, `propose_profile_change`, `apply_profile_change`, `reconcile_profile`, `open_questions`, `add_question`), search and mail (`status`, `get_goals`, `set_goals`, `list_mail`, `resolve_mail`) and settings (`ai_settings`, `set_discovery_preset`, `read_policy`, `recent_activity`). The Gmail sync is not a tool. Tools marked *needs her yes* (`update_job`, `remove_job`, `restore_excluded`, `apply_profile_change`, `reconcile_profile`, `set_goals`, `resolve_mail`) pause the loop with `state: needs_input` and `pending.kind: confirm_tool`; the next `yes` runs the tool and the task continues, `no` leaves it undone. A question from the agent sets `pending.kind: agent`; the answer continues the same task. A tool result that carries a document fills `data` the same way as `resume_ready`.

The engine is the strong tier from `ai_preferences.tiers`; a tier nobody chose follows the Settings main choice (`ai_preferences.default`, else the gateway's built-in: OpenAI with a key, otherwise Codex), so the chat and the background runs share one engine by default. When the chosen provider cannot run on this Mac, the loop moves to the first runtime that is ready (the main choice, then Claude Code, Codex, then any keyed provider) and `engine.moved_from` names what it moved away from. A run the chat starts (`find_jobs`, `run_agent`, the `find jobs` and research/study-plan shortcuts) is enqueued on the chat's engine when that runtime can do the work and Settings gave the action no provider of its own; otherwise the gateway routes it as usual. `PUT /ai/main` changes everything at once (the rail's *Runs on* control calls it).

The page polls `GET /assistant` every 1.2 s while a message is processing, every 8 s when idle and every 30 s in a hidden tab, with a 20 s request timeout; a poll that lands after a newer one is dropped, and a send is echoed at once and followed by an immediate poll.

## Agent runs

`POST /agents/run` takes `kind` (`research`, `resume_advisor`, `email`, `discovery`, `resume_build`, `resume_match`, `instruction_interpret`, `study_plan`), optional `job_id`, `provider`, `model` and a discovery `preset` (`default`, `balanced_five`, `portals`). A discovery result lists `added`, `duplicates` and `excluded` (company, title, URL, reason and sentence). A balanced-five run adds `balanced_shortages`. The `portals` preset reads tracked Greenhouse/Lever/Ashby feeds and makes no AI call. `study_plan` writes `study-plan.md` into the job's application folder.

`POST /studio/{job_id}/fill` fits the draft to exactly one US Letter page (11 → 10.5 → 10pt, then the documented cuts) and returns the new version with its measured layout.
