# Study plan for Twilio - Software Engineer - Video

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Java / JVM, 2-3+ yrs large-scale distributed | Structural | "Minimum 2-3+ years of hands-on experience... on JVM based technologies" |
| RESTful services, API design | Have (Flask projects) | "Experience building RESTful services, API design" |
| Event-driven: Kafka | Have | "event-driven architectures (Kafka, SQS)" |
| Event-driven: SQS | Missing, learnable | Same line; AWS-native queue semantics |
| CI/CD pipelines | Have | "Understanding of CI/CD pipelines" |
| AWS (EC2/S3/RDS/Lambda/Glue/EMR) | Have | "cloud infrastructures such as AWS, GCP..." |
| Grafana | Have | "monitoring/alerting tools (Prometheus, Datadog, Grafana)" |
| Prometheus, Datadog | Missing, learnable | Same line; metrics/alerts are how Voice Trust proves reliability |
| On-call, incident response | Structural | "Experience with on-call rotations, incident response" |
| AI coding assistants + evaluating AI code | Have (Prompt engineering, LangChain) | "Demonstrated proficiency working with AI coding assistants... show examples" |
| CS fundamentals, Bachelor's degree | Have (MS, University of Arkansas; degrees never gaps) | "Strong Computer Science fundamentals... Bachelor's degree" |
| SQL/NoSQL scaling, caching | Partially Have (PostgreSQL, MongoDB); caching patterns learnable; Redis = Never-claim | "scaling data tiers employing a variety of SQL/NoSQL database and caching technologies" |
| Horizontally-scalable production backends | Structural | "proven ability to design and develop horizontally-scalable, resilient... systems" |
| SIP protocol | Missing, learnable (fundamentals) | "Knowledge and experience working with SIP protocol" |
| STIR/SHAKEN | Missing, learnable (fundamentals) | "Knowledge and experience working with Stir/Shaken protocol" — core to Voice Trust's caller-ID mission |

## Tier 1 - before the screening call (week 1-2)

1. **SIP essentials** — the role is Voice; learn sessions, INVITE/ACK/BYE, REGISTER, response codes, SDP basics. Resource: RFC 3261 (sections 1-13) plus Twilio's own SIP docs. Self-check: in 30 min, draw a call-setup ladder diagram and explain a 487 vs 486 response aloud.
2. **STIR/SHAKEN** — this team's reason to exist ("ensure their customers will answer their calls"). Learn attestation levels A/B/C, PASSporT tokens, certificates. Resource: FCC STIR/SHAKEN overview + ATIS-1000074 summary. Self-check: explain in writing, in 5 sentences, why SHAKEN needs a certificate authority.
3. **SQS vs Kafka mental model** — she has Kafka; learn SQS semantics (at-least-once, visibility timeout, FIFO vs standard, DLQs). Resource: AWS SQS Developer Guide core sections. Self-check: 30-min written comparison of when you'd pick SQS over Kafka for call-event processing.
4. **Prometheus data model** — metrics types, labels, PromQL basics, alert rules. Resource: prometheus.io "Overview" + "Querying basics". Self-check: write 5 PromQL queries against a demo endpoint and explain each.
5. **On-call vocabulary** — SLOs/SLIs, error budgets, incident severity, postmortems, so she can discuss the on-call requirement honestly. Resource: Google SRE book, chapters "Embracing Risk" and "Postmortem Culture" (free online). Self-check: write a mock postmortem for a past project bug.

## Tier 2 - before the technical round (week 2-5)

1. **Prometheus + Grafana on a real service** — instrument a small HTTP service with counters/histograms, build a dashboard, set one alert. Artefact: public repo with docker-compose (app + Prometheus + Grafana), a dashboard JSON, and screenshots; Docker and Grafana are registered skills. Reacting to: "monitoring/alerting tools (Prometheus, Datadog, Grafana)".
2. **Low-latency Java service design** — the JD demands "high throughput and low latency". Learn JVM GC basics (G1), connection pooling, backpressure, p99 thinking. Artefact: a written walkthrough (markdown doc) of load-testing a Java endpoint with `wrk`, showing latency percentiles before/after tuning.
3. **Distributed-systems design reps** — idempotency, retries with jitter, circuit breakers, horizontal scaling. Resource: "Designing Data-Intensive Applications" chapters 1-8 or the free System Design Primer (GitHub). Artefact: a one-page design doc for a rate-limited call-routing API, written as detailed prose — Twilio explicitly values "detailed prose".
4. **AI-assisted workflow evidence** — the JD says "describe your workflows and show examples" and "demonstrate with metrics". Artefact: a short written walkthrough of building one Tier-2 artefact with an AI assistant: prompts used, what she rejected and why (correctness, security), rough time saved.
5. **SIP hands-on** — parse a real SIP trace. Artefact: a notebook or markdown walkthrough annotating a captured INVITE-to-BYE exchange header by header, including how STIR/SHAKEN Identity headers attach.

## Build-now project (only if the JD needs a project type she has none of)

She has no production-style Java backend project; her portfolio is ML, IoT and embedded. **Not built yet.** Spec: Goal — a "call-event ingest" service mimicking Voice Trust's shape. Data — synthetic call records (call SID, from/to, SIP code, attestation level). Stack — Java (registered) REST API, Kafka (registered) as the event bus, PostgreSQL (registered) storage, Prometheus metrics + Grafana (registered) dashboard, GitHub Actions CI/CD (registered). Evaluation — a wrk load test showing throughput and p99 latency, plus one triggered alert. Deliverable — public repo: service, docker-compose, dashboard JSON, CI logs, README design doc. Hours — roughly 25-35 across weeks 2-5. No never-claim technology is used.

## Honest answers for the structural gaps

- **2-3+ years production JVM**: "My Java experience is real but project-scale, not multi-year production. I've been closing that deliberately — here's a low-latency service I built and load-tested, and here's what I learned about the JVM under pressure."
- **On-call / incident response**: "I haven't carried a pager in production. I have owned failures end-to-end on my own systems — here's a postmortem I wrote — and I've studied SRE incident practice so I can be useful in a rotation from week one."
- **Proven horizontal scale**: "I understand the patterns — statelessness, backpressure, idempotent consumers — and can walk you through applying them, but I won't claim production scale I haven't run."

## When this may go on the resume

Only after it is learned AND written into data/context/, then re-registered.
