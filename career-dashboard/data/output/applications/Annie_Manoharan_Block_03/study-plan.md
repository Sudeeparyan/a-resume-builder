# Study plan for Block - Software Engineer, Finance Applications

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| Java, Python | Have | "Languages: Kotlin, Java, Python, JavaScript" |
| Apache Kafka, event-driven architectures | Have | "event streams, and messaging patterns" for integrations |
| AWS (EC2, S3, Lambda, Glue), MySQL, REST APIs, CI/CD, Docker | Have | "Infrastructure: AWS", "Data: MySQL", "APIs and integrations" |
| ETL/pipelines, operational analytics | Have | "building data pipelines or reporting systems" (nice to have) |
| Prompt engineering, LangChain, local LLMs | Have (adjacent) | "AI-first mentality", but JD means agentic coding tools specifically |
| Financial vocabulary: GL, reconciliation, revenue, FP&A, tax | Missing, learnable | "from revenue streams to reconciliations to GL to street reporting" |
| Workflow/state-machine systems | Missing, learnable | "configurable workflow engines, rules-based routing… human-in-the-loop steps" |
| Idempotency, audit trails, access controls by default | Missing, learnable | "audit trails, access controls, and data governance baked in" |
| Platform migration patterns | Missing, learnable | "migration of business-critical workflows… zero disruption during cutover" |
| Agentic engineering: Claude Code, Goose, MCP | Missing, learnable | "Direct AI agents across the full development lifecycle" |
| Kotlin, DynamoDB, Prometheus/DataDog, LaunchDarkly | Missing, learnable | Listed under "Technologies We Use and Teach" |
| gRPC / Protocol Buffers | Never-claim (learn, don't claim) | "Protocols: HTTP, JSON, gRPC, Protocol Buffers" |
| Kubernetes | Never-claim (learn, don't claim) | "Infrastructure: AWS, Kubernetes" |
| Snowflake | Never-claim (learn, don't claim) | "Data: DynamoDB, MySQL, Kafka, Snowflake" |
| 6+ years on complex systems | Structural | "6+ working on complex systems and delivering quality software" |
| Financial-services production background | Structural | "Experience working on financially sensitive or regulated systems" |

## Tier 1 - before the screening call (week 1-2)

1. **Finance platform vocabulary** — the JD's "revenue streams to reconciliations to GL". Learn double-entry basics, what a general ledger is, what reconciliation means. Resource: Khan Academy "Accounting and financial statements" (free). Self-check: in 30 min, explain on paper how a Square seller payment flows from revenue event to GL entry to a reconciled report, and where it could break.
2. **Workflow/state machines** — the JD's "entities move through complex lifecycles with branching logic, SLAs, and human-in-the-loop steps". Resource: Temporal's free "Temporal 101" course docs. Self-check: model an invoice-approval lifecycle (states, transitions, SLA timers, human escalation) as a state diagram without notes.
3. **Idempotency and audit trails** — the JD says these matter "by default". Resource: AWS Builders' Library article "Making retries safe with idempotent APIs" (free). Self-check: sketch an idempotent ledger-write endpoint (idempotency keys, dedup window, immutable audit log) and explain why retries can't double-post.
4. **gRPC + Protocol Buffers (never-claim)** — named in "Protocols". Resource: official grpc.io "Introduction to gRPC" and "Basics tutorial" for Python (free). Self-check: write a small .proto for a ledger service with one unary and one streaming RPC; explain gRPC vs REST trade-offs. Honest line if asked: "I've studied it and built a toy service; I haven't run it in production."
5. **Agentic engineering: Claude Code, Goose, MCP** — the JD's core culture signal ("we expect every engineer to do the same"). She has LangChain/prompt engineering; this is the applied version. Resource: Block's open-source Goose docs (block.github.io/goose) and Anthropic's MCP introduction (free). Self-check: run Goose locally on a small repo task and describe, in 3 sentences, how she'd review and own agent-written code.

## Tier 2 - before the technical round (week 2-5)

1. **Event-driven ledger service** — directly mirrors "backend services… with audit trails". Build a double-entry ledger API in Python or Java: Kafka events, idempotent writes, MySQL, append-only audit table, access checks. Artefact: public GitHub repo with README architecture diagram and tests proving no double-posting under retries.
2. **Platform migration design** — the JD's "Lead a platform migration… zero disruption". Study strangler-fig pattern, dual-writes, backfill, phased rollout, feature flags (LaunchDarkly's free tier). Artefact: a written design doc (repo or gist): "Migrating a vendor reconciliation workflow to an internal system" with cutover plan, rollback, and flag strategy.
3. **DynamoDB data modeling** — named under "Data"; her AWS base makes this fast. Resource: AWS's free "Amazon DynamoDB deep dive" on YouTube/AWS Skill Builder. Artefact: notebook or repo modeling chart-of-accounts access patterns with single-table design, GSIs, and rationale.
4. **Snowflake (never-claim)** — named under "Data". Learn via Snowflake's free 30-day trial + official Quickstart "Getting Started with Snowflake". Artefact: notebook loading sample finance data, running window-function reconciliation queries. Learned, never claimed on the resume.
5. **Kubernetes + observability (K8s never-claim)** — "Infrastructure: AWS, Kubernetes"; "DataDog, Prometheus". Resource: official kubernetes.io tutorials with minikube, plus Prometheus "Getting started" (free). Artefact: short written walkthrough deploying her existing Flask expense-tracker API to minikube with a Prometheus metrics endpoint. Learned, never claimed.

## Build-now project (only if the JD needs a project type she has none of)

She has no workflow-engine project; the JD centers on one. Spec — **"not built yet"**:
- Goal: configurable rules-based workflow engine for invoice approvals.
- Data: synthetic invoices (generated with Pandas) across 3 fake business units.
- Stack: Python, Flask, MySQL, Kafka; states persisted; SLAs as timers.
- Features: YAML-defined state machines per BU, branching rules, human-in-the-loop queue UI, SLA breach events, full audit log.
- Evaluation: replay 10k events; show no lost transitions, audit completeness, latency under load.
- Deliverable: GitHub repo + README with state diagrams and a demo script.
- Hours: ~30-40, fits inside Tier 2 weeks 3-5 alongside item 1.

## Honest answers for the structural gaps

- On "6+ years": "I have fewer years than the posting asks, but I've built and operated distributed streaming systems end-to-end — Kafka, Flink, Airflow — and I'd rather show you the ledger service I built for this process than claim years I don't have."
- On regulated/financial systems: "I haven't shipped inside a regulated finance org yet. I've studied why idempotency, audit trails, and retention matter and built them into my own services — I'm looking for the environment where those defaults are non-negotiable."

## When this may go on the resume

Only after a skill is actually learned AND written into data/context/, then re-registered — and Kubernetes, Snowflake, and gRPC stay off it regardless, per her never-claim list.
