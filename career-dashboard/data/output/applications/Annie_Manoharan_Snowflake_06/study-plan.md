# Study plan for Snowflake - Software Engineer- Openflow

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Java | Have | "Proficiency in Java... experience working in large, shared codebases" |
| Kafka / Flink / Airflow | Have | "Bonus: ...streaming/flow technologies such as Apache NiFi, Kafka, Flink, or Airflow" |
| Docker, CI/CD, AWS (EC2/S3/Lambda/Glue), Linux, Grafana | Have | "cloud-native services... using containers, CI/CD, and modern monitoring and logging stacks" |
| Multithreading, SQL, design patterns, TDD | Have | "operating systems and networking basics, including multithreading, memory management" |
| CS fundamentals (algorithms, data structures, systems design) | Have (coursework/projects) | "Strong computer science fundamentals" — refresh, not learn |
| Apache NiFi / Openflow dataflow model | Missing, learnable | Openflow is built on NiFi; control plane / data plane work assumes its mental model |
| Distributed-systems concepts: replication, partitioning, fault tolerance, exactly-once semantics | Missing, learnable | "Practical experience with distributed systems concepts such as concurrency, replication, partitioning, streaming, and fault tolerance" |
| Observability & on-call / incident response practice | Missing, learnable | "Operate and support the components you build, including monitoring, on-call participation, incident response" |
| Performance profiling & debugging at scale | Missing, learnable | "Analyze and improve performance... using metrics, profiling, and experimentation" |
| Snowflake platform & data-movement domain | Never-claim (learn it, never list it) | Role powers data movement "across Snowflake and non-Snowflake environments" |
| Go / Scala / Kubernetes | Never-claim | JD alternatives to Java and common platform tooling — learning optional |
| 2+ years industry backend/platform experience | Missing, structural | "2+ years of industry experience building and operating backend or platform services" |

## Tier 1 - before the screening call (week 1-2)

1. **Distributed-systems core vocabulary.** Replication, partitioning/sharding, consensus basics, idempotency, exactly-once vs at-least-once, backpressure — the JD names these outright. Resource: *Designing Data-Intensive Applications* (Kleppmann) chapters 5, 6, 11 via free excerpts + the author's talks. Self-check (30 min): explain to a voice recorder, unprompted, how a Kafka consumer group gives at-least-once delivery and what you'd add for exactly-once.
2. **Apache NiFi / Openflow fundamentals.** FlowFile, processor, connection, controller services; the control-plane vs data-plane split. Resource: Apache NiFi official docs ("Getting Started" + "Overview"). Self-check: sketch on paper how a NiFi flow moves files S3→warehouse and name where backpressure lives.
3. **Java concurrency in depth.** The JD's "multithreading... debugging performance and scale issues" means interviews probe beyond basics. Resource: "Java Concurrency in Practice" free chapter + Baeldung concurrency series. Self-check: implement a bounded blocking queue with locks, then explain its contention points.
4. **On-call & incident-response vocabulary.** SLOs, error budgets, runbooks, postmortems — JD says "on-call participation, incident response... post-incident reviews." Resource: Google SRE book, free online (chapters on monitoring and postmortems). Self-check: write a one-page mock postmortem for a Kafka lag incident.
5. **Systems-design interview format.** Resource: free "System Design Primer" repo (solutions section only). Self-check: talk through "design a data-ingestion pipeline" in 30 minutes, recorded.

## Tier 2 - before the technical round (week 2-5)

1. **NiFi hands-on flow.** Run NiFi in Docker (she has Docker), build a flow ingesting JSON from a local directory into PostgreSQL with error routing. Artefact: a small repo with the flow template (XML), a README architecture diagram, and screenshots.
2. **Fault-tolerant Java streaming service.** Extend her existing Kafka knowledge: a Java producer/consumer pair with retries, dead-letter topic, and a partition-skew demo. Artefact: GitHub repo with a README measuring throughput before/after partitioning changes — direct proof for "replication, partitioning, streaming, and fault tolerance."
3. **Observability walkthrough.** Add metrics + Grafana dashboards (she has Grafana) to the Tier-2 service: lag, error rate, p99 latency. Artefact: written walkthrough with dashboard screenshots explaining which metrics she'd alert on and why — answers "modern monitoring and logging stacks."
4. **Profiling practice.** Use JVisualVM/async-profiler on her own service to find one real bottleneck and fix it. Artefact: a short write-up with flame graphs before/after — mirrors "using metrics, profiling, and experimentation to guide optimizations."
5. **Snowflake domain literacy (learn-only).** Read Snowflake's public docs on Openflow, Snowpipe, and connectors so she understands the product context. Artefact: internal notes only — Snowflake is a never-claim skill; this knowledge is spoken context, never a listed skill.

## Honest answers for the structural gaps

**2+ years industry experience:** "Most of my production-style work is academic and project-based — I've built and operated streaming pipelines with Kafka and Flink in my own projects and labs, and I'm upfront that I haven't yet done that inside a large shared production codebase. That's exactly what I want this role to teach me, with guidance from senior engineers, as the posting describes."

**Operating/on-call at scale:** "I haven't carried a pager yet. What I have done is study SRE practice seriously and instrumented my own services with metrics and alerting, so I understand the discipline — I'm ready to join the on-call rotation with mentorship from day one."

## When this may go on the resume

Only after a skill here is actually learned, built, and written into data/context/, then re-registered — never before.
