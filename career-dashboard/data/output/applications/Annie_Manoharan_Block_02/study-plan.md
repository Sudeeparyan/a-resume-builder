# Study plan for Block - Software Engineer, Payment Interfaces

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Apache Kafka | Have | "Technologies We Use and Teach: Kafka" |
| AWS (EC2, S3, Lambda, RDS, Glue) | Have | "Technologies We Use and Teach: AWS" |
| AI-assisted engineering | Have (LangChain, prompt engineering, local LLMs) | "Fluency with AI-assisted engineering tools... validate generated code" |
| CI/CD, Docker, TDD, design patterns | Have | "own testing, rollout", "automation to reduce repetitive operational work" |
| Payment API concerns: idempotency, retries, async processing, backward compatibility, partial failures | Learnable | "An understanding of payment API concerns such as idempotency, retries..." |
| Kotlin | Learnable (Java is Have; Kotlin is not registered) | "Technologies We Use and Teach: Kotlin" |
| TypeScript | Learnable (not registered) | "Technologies We Use and Teach: TypeScript" |
| Incident response, SLOs, postmortems | Learnable (Grafana is Have) | "on-call rotation, investigate incidents... preventive engineering" |
| Production payments experience | Structural | "Experience building, maintaining, and scaling customer-facing financial or payment APIs... This is a requirement" |
| High-volume production operation record | Structural | "high-volume, highly available distributed systems where correctness... matter" |
| 8 yrs + Bachelor's / 6 yrs + Master's | Structural (her Master's degree itself is never a gap) | "A minimum of 8 years of related experience with a Bachelor's degree; or 6 years and a Master's" |
| Go | Never-claim (may be learned later, never claimed) | "Technologies We Use and Teach: Go" |

## Tier 1 - before the screening call (week 1-2)

1. **Idempotency and retries.** The JD: "idempotency, retries... without compromising financial correctness." Learn idempotency-key lifecycle, safe retry semantics, exponential backoff with jitter. Resource: Stripe's idempotent-requests docs plus the AWS Builders' Library article "Timeouts, retries, and backoff with jitter." Self-check: explain on paper what happens when a POST /payments times out after the charge succeeded, and how the key prevents a double charge.
2. **Async processing, webhooks, backward compatibility.** The JD: "asynchronous processing, backward compatibility." Learn webhook delivery (at-least-once, signatures, DLQs) and additive-only API evolution. Resource: Stripe webhooks documentation. Self-check: sketch a v1-to-v2 change adding a field and argue why old clients never break.
3. **Kotlin for a Java developer.** The JD lists Kotlin first under technologies. Resource: kotlinlang.org "Java to Kotlin" migration guide and Kotlin docs on coroutines. Self-check: write a data class, a null-safe call chain, and one suspending function from memory.
4. **TypeScript basics.** Resource: The TypeScript Handbook (official). Self-check: type a JSON payment response and catch a deliberate type error.
5. **Incident response vocabulary.** The JD: "on-call rotation, investigate incidents." Learn SLOs, error budgets, blameless postmortems. Resource: Google SRE Book (free online), chapters on monitoring and postmortem culture. Self-check: write a one-page postmortem for an imaginary payments outage in 30 minutes.

## Tier 2 - before the technical round (week 2-5)

1. **The build-now project below** — Artefact: public repo with README and design doc.
2. **Kafka correctness patterns.** Her Kafka is registered; go deeper into consumer-side idempotency, ordering, and dead-letter queues for financial events. Artefact: a demo that runs a duplicate-producer/retry storm and shows exactly-once-effect at the consumer, with a notebook of results.
3. **Distributed failure modes of payment systems.** Artefact: a written walkthrough (markdown, ~5 pages) of timeouts, partial failures, and reconciliation, each tied to a JD phrase — this doubles as interview prep.
4. **Observability for a payment API.** The JD: "improve performance, observability, fault tolerance." Artefact: Grafana dashboard (Grafana is Have) plus a written SLO: latency, error rate, duplicate-charge rate = 0.
5. **Kotlin backend in anger.** Artefact: the same repo from item 1, written in Kotlin — proof she can work in their primary language, stated honestly as "recently learned."

## Build-now project (she has no payment-API project)

**PayGate-mini — idempotent payment API (not built yet)**
- Goal: a small customer-facing payment API demonstrating every JD concern: idempotency, retries, async webhooks, partial-failure handling.
- Stack: Kotlin (Ktor), PostgreSQL (Have), Kafka (Have) for async events, Docker (Have), deployed on AWS free tier (Have). Flask/Python alternative acceptable if Kotlin slows her down.
- Features: POST /payments with idempotency keys; retry-safe client SDK; webhook dispatcher with DLQ; simulated downstream outage.
- Evaluation: a chaos test — kill the "processor" mid-request, fire duplicate requests — must produce zero double charges; results table in README.
- Deliverable: GitHub repo, README with architecture diagram and the Tier-2 walkthrough linked.
- Hours: ~35 over weeks 2-5.

## Honest answers for the structural gaps

- **No production payments experience:** "I haven't run payment systems in production yet, and I won't pretend otherwise. I built PayGate-mini to learn the failure modes hands-on — idempotency, retries, reconciliation — and my streaming and data work taught me correctness under retries at volume. I know Block's scale is deeper, and that gap is exactly why I prepared this way."
- **Years of experience:** "I hold a Master's degree, so I read the requirement as six years. My years are in data, streaming, and embedded systems rather than payments specifically — distributed correctness transfers, the payments domain is what I'm learning now, and I'd rather be honest about that than oversell."

## When this may go on the resume

Only after a skill is actually learned AND written into data/context/, then re-registered — nothing in this plan is resume material today.
