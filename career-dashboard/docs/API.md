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

## Agent runs

`POST /agents/run` takes `kind` (`research`, `resume_advisor`, `email`, `discovery`, `resume_build`, `resume_match`, `instruction_interpret`, `study_plan`), optional `job_id`, `provider`, `model` and a discovery `preset` (`default`, `balanced_five`, `portals`). A discovery result lists `added`, `duplicates` and `excluded` (company, title, URL, reason and sentence). A balanced-five run adds `balanced_shortages`. The `portals` preset reads tracked Greenhouse/Lever/Ashby feeds and makes no AI call. `study_plan` writes `study-plan.md` into the job's application folder.

`POST /studio/{job_id}/fill` fits the draft to exactly one US Letter page (11 → 10.5 → 10pt, then the documented cuts) and returns the new version with its measured layout.
