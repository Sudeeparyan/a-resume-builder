# The agent layer

Built on LangChain and LangGraph. One general-purpose prompt was replaced by
nine specialists, each with a narrow brief, its own output schema, and a
service tier.

## Specialists

| Agent | Job | Tier |
|---|---|---|
| `requirement_extractor` | Job description to grounded requirements, each with a verbatim excerpt | reading |
| `relevance_judge` | Whether a posting is worth the candidate's time | reading |
| `company_investigator` | Whether the employer is real, its size, sponsorship evidence, fraud signals | reading |
| `posting_verifier` | Whether a posting is still open, from the fetched page | reading |
| `mail_classifier` | What one job-related email is | reading |
| `resume_tailor` | Evidence-bound resume edits for one role | writing |
| `profile_curator` | Proposed profile additions and corrections | writing |
| `cover_letter_writer` | A covering letter from registered evidence | writing |
| `hiring_manager` | What a strong application must show — **isolated** | writing |
| `fit_analyst` | The posting's requirements, each judged met, partial or missing against registered evidence (excerpts and ids checked in code) | reading |
| `letter_auditor` | A second AI that did not write the cover letter lists every sentence about Annie the evidence does not state | reading |
| `job_tailor` | Projects and Skills for one role: verified items word for word plus predicted items for her keep/remove review | writing |
| `workspace_agent` | The Assistant's agent loop: one decision per turn, up to five extra read-only lookups (`more_calls`) | writing |

A specialist whose answer has the wrong shape gets one more try on the same AI with the
reasons (`schema_repair` in the trace) before the route or the backup moves on.

## Two tiers, not nine model choices

The reading tier does extraction and classification; the writing tier produces
text that reaches an employer. Choosing a model per tier in Settings is the
cost control: a discovery pass over one posting runs three reading agents for
roughly four thousand tokens.

## Routing is deterministic

The workflow decides which specialist runs, not a model. A run's cost is
therefore predictable, and a routing mistake is a code bug rather than a prompt
bug. `evaluate_posting` fans out verification, relevance, company research and
requirement extraction in parallel; each writes its own state key, so the
branches never contend, and one failing agent leaves the others intact.

## Auto: one route across her plans

Choosing **Auto** in Settings (`backend/ai/router.py`, ported from the Template in October 2026)
sends every step to the first plan on the route that is switched on, set up on this PC, able to
do the step (web search, Gmail) and not resting: Kimi Code → Codex → Claude Code → Antigravity,
then Azure OpenAI (paid) last. A usage-limit error rests that plan until the reset time the CLI
printed (`backend/ai/limits.py`, `.ai-plan-health.json` next to `.env`); three failures in a row
rest it for 15 minutes. Each free plan's 5-hour window is metered (real tokens when reported,
else an estimate) and shown in Settings, with a limit she can type or that Auto learns the first
time a plan runs out. The daily AI limit now counts **paid** calls only (Azure, API keys); her
plans never count against it. One AI call at a time per plan (`services/task_execution.py`
`invocation_slot`), so two runs never fight over the same CLI.

Every agent run is traced locally (`backend/telemetry/`, OpenTelemetry into
`data/traces.db`, 14 days): the run, each AI call (provider, model, tokens, which plan Auto
picked) and each route switch. Spans never carry prompt or resume text. LangSmith's hosted
tracing is switched off on import unless `CAREER_ALLOW_LANGSMITH=1`. The Agents tab's **See what
it did** opens a run's side panel: steps, sources read, posting outcomes and the span timeline.

## The isolation boundary

`hiring_manager` must never see candidate information. `AgentTeam.run()`
refuses it, and `run_isolated()` builds a payload of exactly
`job_description` and `public_company_research`. `tests/test_ai_agents.py`
asserts both halves.

## Providers

OpenRouter reaches GPT, Claude, Gemini and Kimi with one key and is the
default. Each provider can also be used directly with its own key. Four local
runtimes need no key at all and run on a subscription's usage limits instead:
Codex (the ChatGPT app's `codex exec`), Claude Code (the `claude` CLI that
ships with the Claude app and the Claude Code extension) and Kimi Code (the
`kimi` CLI from the Kimi Code app, `backend/ai/kimi_cli.py`) and Google
Antigravity (the `agy` CLI, `backend/ai/antigravity_cli.py`). Codex and Claude
Code take the prompt on stdin and return a schema-checked JSON object. Kimi
Code takes the prompt as an argument (`kimi -p … --output-format stream-json`),
reads no stdin, and answers in its default model; prompts over 20,000
characters are written to `prompt.md` in its fresh working directory and the
argument points at that file. Its stdout is captured to a file rather than a
pipe, because on Windows the CLI can lose buffered pipe output on long runs;
when a turn fails without output, the error is read back from the CLI's own
session log. Antigravity runs headless (`agy -p … --output-format json
--json-schema schema.json --sandbox`), returns the schema-checked object as
`structured_output`, takes long prompts through `prompt.md` and captures stdout
to a file the same way, and is never given `--dangerously-skip-permissions`: a
tool that needs approval is refused and the run carries on. Its model is the
CLI's own (`antigravity-runtime`) unless Settings pins a Gemini slug from
`agy models`. Sign in once by running `agy` in a terminal. All four CLIs run one-shot in restricted mode with no session,
settings, MCP servers or CLAUDE.md files, and allow only web search and fetch
when the action needs the web. None of Claude Code, Antigravity or Kimi Code has Gmail
access, so the email worker stays on Codex. Claude Code, Antigravity and Kimi Code serve
both the agent runs (discovery, research, advisor, match) and the nine
specialists above, chosen per tier in Settings.

One choice on the Settings page drives every agent: it becomes the gateway
default and, for providers the specialist team can run on, both tiers. Keys
pasted on that page are written to `career-dashboard/.env` (0600, git-ignored),
checked with a free model-list call, and never returned to the browser. With a
key, OpenRouter, Gemini and Kimi join the gateway through LangChain
(`HostedProvider` in `providers.py`). Work the chosen provider cannot do is not
failed but routed: `resolve()` sends web research to the first ready provider
with web search (Claude Code, Codex, Antigravity, Kimi Code, OpenAI) and Gmail to Codex, and Settings
lists where each kind of work will run. A provider named explicitly is still
refused when it lacks the capability.

Every run records its stages and AI calls in `agent_run_events` (provider,
model, web or not, seconds, new or reused, error); `GET /api/v2/agents/activity`
serves them to the Agents tab. Nothing in the trace is sent to a model.

Model lists are fetched from each provider and cached for a day, so a new
release appears in the dropdown without a code change. Test connection makes
the smallest real call, so a bad key or an exhausted quota fails there rather
than in the middle of a run. Provider errors are reported by class — "the
account is out of credits" — because the raw text embeds key-management URLs.
