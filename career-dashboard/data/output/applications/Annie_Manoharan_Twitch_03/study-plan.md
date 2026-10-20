# Study plan for Twitch - Software Engineer, Data Platform

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map
| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Bachelor's CS or equivalent | Have | 'Bachelor's degree... or equivalent'; education is present and a held degree is never a gap. |
| Python | Have | Bonus 'Golang or Python'; Python is registered. |
| AWS | Have | Bonus 'Amazon Web Services'; registered EC2/S3/RDS/EMR/Glue/Lambda cover vocabulary. |
| Streaming/distributed compute evidence | Have | '200 billion events a day' maps to registered Kafka/Flink/Spark and the IoT analytics project. |
| Scalability, concurrency, distributed-systems fundamentals | Missing but learnable | Must-have 'Familiarity with scalability, concurrency... distributed systems'; she has parts, not crisp interview language. |
| API design | Missing but learnable | Must-have names 'API design'; no registered REST/gRPC term and gRPC is never-claim. |
| Data modeling | Missing but learnable | Must-have and the genuine gap; needed for 'data warehouses and pipelines'. |
| AI coding tools | Missing but learnable | 'Enhance our workflows using AI tooling' and 'Familiarity with AI coding tools'; adjacent GenAI skills exist, workflow evidence is thin. |
| Golang | Never-claim | Bonus 'Golang'; learn enough to compare tradeoffs, never say she has it. |
| Highly available production ownership at Twitch scale | Missing and structural | 'receives over 200 billion events a day' and 'next petabyte' imply years of operating blast radius she cannot fake. |
| Open-source contributions | Missing but learnable | Bonus; small docs/tests PRs are feasible, not a resume claim yet. |

## Tier 1 - before the screening call (week 1-2)
1. Data modeling for warehouses: learn star schema, facts/dimensions, SCDs, partitioning vs clustering. Resource: Kimball dimensional modeling techniques summary. Self-check: sketch events, users, streams, games for Twitch chat and defend grain in 5 sentences.
2. API design fundamentals: resource naming, pagination, idempotency, versioning, errors, rate limits. Resource: freeCodeCamp 'REST API Best Practices' or Microsoft REST guidance. Self-check: design 'GET /channels/{id}/metrics' and explain 429/ETag choices.
3. Scalability vocabulary: horizontal scaling, backpressure, sharding, hotspots, exactly-once vs at-least-once. Resource: Kafka documentation design section. Self-check: explain how a partition key can create a hot shard during a big stream.
4. Concurrency fundamentals: threads vs async, locks, queues, backpressure, tail latency. Resource: Python concurrency docs plus her registered Multithreading as base. Self-check: describe a producer-consumer pipeline and where p99 blows up.
5. AI coding tools workflow: use Copilot-style tools for tests, refactors, docs while verifying output. Resource: GitHub Copilot docs/prompting guide. Self-check: state one rule she uses to catch plausible-but-wrong generated code.

## Tier 2 - before the technical round (week 2-5)
1. Twitch-shaped AWS lakehouse: rehearse S3/Glue/EMR/Lambda patterns without claiming Redshift/Kinesis. Artefact: one-page architecture walkthrough for ingest -> raw S3 -> curated tables -> dashboards with failure modes.
2. Kafka depth beyond usage: partitions, consumer groups, ISR, retention, rebalancing, DLQ. Artefact: notebook or repo `kafka-notes` with a tiny local producer/consumer and rebalancing experiment.
3. Flink depth for live decisions: windows, watermarks, state, checkpoints, exactly-once sinks. Artefact: PyFlink/Flink SQL mini-demo counting events per streamer with late data, plus README on checkpoint recovery.
4. Data-warehouse modeling lab: model Twitch-like events into fact tables and incremental loads using Databricks/Delta Lake or SQL she has. Artefact: GitHub repo with schema diagram, DDL, sample queries, and tests for duplicate/out-of-order events.
5. Go comparison literacy only: learn syntax, goroutines, channels, why infra teams pick Go. Resource: A Tour of Go. Artefact: short written comparison 'Python service vs Go service for a metrics API' marked learning notes, not experience.

## Build-now project (only if the JD needs a project type she has none of)
Not required: the JD reacts to existing registered Kafka/Flink/Spark/AWS plus the 'Real-Time Medical IoT Analytics Platform'. Extend that project instead: goal, replay 1M synthetic live events; data, JSON chat/viewer events; stack, Python, Kafka/Flink SQL, S3-compatible local store, Glue-style catalog notes; evaluation, end-to-end latency, duplicate rate, recovery after kill; deliverable, repo with README and Grafana screenshot; hours, 18-24; label: not built yet.

## Honest answers for the structural gaps
- Scale: 'I have built streaming analytics projects with Kafka/Flink and AWS services, but I have not operated a platform at 200 billion events per day; I am ready to learn that ownership from senior engineers.'
- Go: 'Python is my working language; I am studying Go because platform teams use it, but I would not present myself as a Go engineer yet.'

## When this may go on the resume
Only after a topic is learned, proven by an artefact, written into data/context/, and then re-registered; never before.
