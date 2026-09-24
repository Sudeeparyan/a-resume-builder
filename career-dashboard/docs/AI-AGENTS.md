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

## The isolation boundary

`hiring_manager` must never see candidate information. `AgentTeam.run()`
refuses it, and `run_isolated()` builds a payload of exactly
`job_description` and `public_company_research`. `tests/test_ai_agents.py`
asserts both halves.

## Providers

OpenRouter reaches GPT, Claude, Gemini and Kimi with one key and is the
default. Each provider can also be used directly with its own key. Three local
runtimes need no key at all and run on a subscription's usage limits instead:
Codex (the ChatGPT app's `codex exec`), Claude Code (the `claude` CLI that
ships with the Claude app and the Claude Code extension) and Kimi Code (the
`kimi` CLI from the Kimi Code app, `backend/ai/kimi_cli.py`). Codex and Claude
Code take the prompt on stdin and return a schema-checked JSON object. Kimi
Code takes the prompt as an argument (`kimi -p … --output-format stream-json`),
reads no stdin, and answers in its default model; prompts over 20,000
characters are written to `prompt.md` in its fresh working directory and the
argument points at that file. Its stdout is captured to a file rather than a
pipe, because on Windows the CLI can lose buffered pipe output on long runs;
when a turn fails without output, the error is read back from the CLI's own
session log. All three CLIs run one-shot in restricted mode with no session,
settings, MCP servers or CLAUDE.md files, and allow only web search and fetch
when the action needs the web. Neither Claude Code nor Kimi Code has Gmail
access, so the email worker stays on Codex. Claude Code and Kimi Code serve
both the agent runs (discovery, research, advisor, match) and the nine
specialists above, chosen per tier in Settings.

One choice on the Settings page drives every agent: it becomes the gateway
default and, for providers the specialist team can run on, both tiers. Keys
pasted on that page are written to `career-dashboard/.env` (0600, git-ignored),
checked with a free model-list call, and never returned to the browser. With a
key, OpenRouter, Gemini and Kimi join the gateway through LangChain
(`HostedProvider` in `providers.py`). Work the chosen provider cannot do is not
failed but routed: `resolve()` sends web research to the first ready provider
with web search (Claude Code, Codex, Kimi Code, OpenAI) and Gmail to Codex, and Settings
lists where each kind of work will run. A provider named explicitly is still
refused when it lacks the capability.

## Auto: free plans first (the default)

`backend/ai/router.py` routes like OpenRouter across her own plans. The
default choice, `auto`, sends each step down an ordered route, **Kimi Code
(K3) → Codex (GPT-6-Astra to write, GPT-6-Luna to read) → Claude Code (Opus to
write, Sonnet to read) → Azure OpenAI**, to the first endpoint that is switched
on, set up here, able to do the step (Gmail: Codex only), not resting, and, for
Azure, inside the daily paid-call limit. Paid endpoints always sort last. A
failure moves the step to the next endpoint; a usage-limit failure also rests
that plan until the reset time the CLI printed (`limits.py` reads Claude's
"resets 5:40pm (zone)", Codex's "try again in 2 hours 13 minutes", Claude's
epoch form; an hour when it says nothing, two minutes for an Azure 429), and
three failures in a row rest it for 15 minutes. The rest state lives in
`.ai-plan-health.json` beside the shared `.env`, so every profile sees it. The
gateway (`RouterProvider`), the specialist team (`AgentTeam` tiers set to
`auto`) and Daily Search all use the same `router.route`; each call records the
endpoint that served it (`ai_calls`, the Agents trace "Auto → Codex · …") and
each switch as a `provider_fallback` activity event.

Every call on a free plan is also metered against that plan's 5-hour window:
real tokens when the CLI reports them (Claude Code), otherwise an estimate from
the text plus a per-call overhead. Each plan's limit per window is what she
typed in Settings, else the one learned when the plan last ran out (the tokens
metered in that window), else a starting guess. Settings shows each plan's
percentage used; Daily Search shows how a search's estimated tokens will fill
the plans in route order before it starts.

The daily limit (`ai_policy.daily_call_limit`) counts **paid** calls only; free
plan calls never count, since each plan has its own usage window. When it is
used up, Auto skips Azure until tomorrow and keeps working on the free plans;
a paid provider chosen by name is stopped. `workspace.py ai-status` and
`ai-wake --provider X` show and clear plan state from any AI app.

Every run records its stages and AI calls in `agent_run_events` (provider,
model, web or not, seconds, new or reused, error); `GET /api/v2/agents/activity`
serves them to the Agents tab. Nothing in the trace is sent to a model.

Model lists are fetched from each provider and cached for a day, so a new
release appears in the dropdown without a code change. Test connection makes
the smallest real call, so a bad key or an exhausted quota fails there rather
than in the middle of a run. Provider errors are reported by class — "the
account is out of credits" — because the raw text embeds key-management URLs.
