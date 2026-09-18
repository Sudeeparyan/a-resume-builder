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
default. Each provider can also be used directly with its own key. Two local
runtimes need no key at all and run on a subscription's usage limits instead:
Codex (the ChatGPT app's `codex exec`) and Claude Code (the `claude` CLI that
ships with the Claude app and the Claude Code extension). Both take the prompt
on stdin and return a schema-checked JSON object. `backend/ai/claude_code.py`
finds the newest installed CLI, runs it one-shot in restricted mode with no
session, settings, MCP servers or CLAUDE.md files, and allows only web search
and fetch when the action needs the web. It has no Gmail access, so the email
worker stays on Codex. Claude Code serves both the agent runs (discovery,
research, advisor, match) and the nine specialists above, chosen per tier in
Settings.

One choice on the Settings page drives every agent: it becomes the gateway
default and, for providers the specialist team can run on, both tiers. Keys
pasted on that page are written to `career-dashboard/.env` (0600, git-ignored),
checked with a free model-list call, and never returned to the browser. With a
key, OpenRouter, Gemini and Kimi join the gateway through LangChain
(`HostedProvider` in `providers.py`). Work the chosen provider cannot do is not
failed but routed: `resolve()` sends web research to the first ready provider
with web search (Claude Code, Codex, OpenAI) and Gmail to Codex, and Settings
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
