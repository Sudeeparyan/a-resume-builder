# Study plan for Reddit - Software Engineer, Ingestion Platform

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Apache Kafka | Have | Core source system: "100B events per day" ingested |
| Apache Flink / Spark | Have | "batch and streaming based ML and BI workloads" |
| Airflow, Python, Java | Have | "orchestrate these data workloads"; OOP proficiency |
| Amazon S3, Docker, CI/CD, Grafana | Have | "paths to S3/GCS", deployment safety, "actionable observability and alerting" |
| Delta Lake | Have | Adjacent to Iceberg; transferable table-format knowledge |
| Apache Iceberg | Missing, learnable | "production-ready paths to S3/GCS and Apache Iceberg" |
| GCP / GCS | Missing, learnable | "Kafka-to-BigQuery", "paths to S3/GCS" (she knows AWS only) |
| Control plane vs data plane, connector/target-manager APIs | Missing, learnable | "pipeline APIs, controllers, connectors, target managers, sink integrations" |
| Deduplication, dead-letter queues, schema evolution | Missing, learnable | Named verbatim as "reusable capabilities" and reliability practices |
| Platform migration strategy | Missing, learnable | "safe, incremental, and low-touch" migrations off legacy systems |
| Kubernetes | Never-claim — learn only | "pipelines running across Kubernetes clusters"; do not claim it |
| BigQuery | Never-claim — learn only | The current Kafka sink; learn vocabulary, never claim experience |
| Go / Scala | Never-claim | Listed under "Python, Scala, Go, or Java" — Python/Java already cover this |
| 2+ years production SWE experience | Structural | Hard requirement; cannot be learned in weeks |
| Demonstrated large-scale production system design | Structural | "Demonstrated expertise in designing and implementing large-scale systems" |

## Tier 1 - before the screening call (week 1-2)

1. **Ingestion-platform vocabulary: control plane vs data plane.** Learn how controllers, connectors, and sink integrations divide responsibilities. Resource: Confluent's free "Inside Kafka Connect" / data pipeline architecture articles. Self-check: in 30 min, whiteboard a Kafka-to-warehouse platform and label which components are control plane vs data plane, out loud, no notes.
2. **Apache Iceberg fundamentals.** Contrast with Delta Lake (which she has): table format, snapshots, hidden partitioning. Resource: Tabular's free "Apache Iceberg — Getting Started" guide. Self-check: explain schema evolution and partition evolution in Iceberg vs Delta Lake in 5 minutes each.
3. **Delivery semantics: exactly-once, deduplication, dead-letter queues.** The JD lists these as platform capabilities. Resource: Confluent Developer free course module on error handling and DLQs. Self-check: describe three ways duplicates enter a Kafka pipeline and one mitigation per way.
4. **GCP vocabulary for an AWS person.** GCS vs S3, BigQuery slots vs Redshift-style warehouses (learn-only; BigQuery is never-claim). Resource: Google Cloud's free doc "Google Cloud for AWS professionals". Self-check: map ten AWS services she uses to their GCP equivalents from memory.
5. **Schema evolution and registry patterns.** The JD names "schemas" and "schema evolution" under reliability. Resource: Confluent Schema Registry fundamentals (free docs). Self-check: explain backward vs forward compatibility and what breaks a consumer in each.

## Tier 2 - before the technical round (week 2-5)

1. **Iceberg depth: compaction, snapshot expiration, partition evolution.** Artefact: a Jupyter notebook using PySpark (Have) writing Iceberg tables, demonstrating a schema change and a partition-spec change with before/after query results.
2. **End-to-end ingestion pipeline with DLQ and dedup.** Build Kafka → Flink → Iceberg with a poison-record path. Artefact: a public repo with README, docker-compose, and a test that injects a malformed event and shows it land in the DLQ.
3. **Kubernetes for data workloads (learn-only, never claim).** Resource: the free official Kubernetes tutorials plus minikube. Artefact: a written walkthrough of deploying the pipeline's components on minikube — kept as a private learning note, since Kubernetes is on her never-claim list.
4. **Sink design: BigQuery-style warehouse vs Iceberg-on-object-storage.** Learn-only for BigQuery. Artefact: a one-page written comparison of cost, latency, and schema-evolution trade-offs between a managed warehouse sink and an open table format — exactly the "beyond Kafka-to-BigQuery" expansion the JD describes.
5. **Pipeline observability.** She has Grafana; extend it to ingestion metrics (lag, DLQ rate, throughput). Artefact: a Grafana dashboard JSON plus alert rules committed to the repo from item 2.

## Build-now project (not built yet)

- Goal: a miniature self-serve ingestion platform, mirroring the JD's control plane/data plane split.
- Data: synthetic clickstream events (~1M/day via a Python generator), 5% deliberately malformed.
- Stack: Kafka (source), Flink SQL (transform + dedup), Iceberg on MinIO as the S3-compatible sink, Airflow for orchestration, Grafana for lag/DLQ dashboards, GitHub Actions for CI/CD.
- Control plane: a small Flask (Have) API that registers a new "pipeline" and writes its config; a controller loop that applies it.
- Reliability features: dead-letter topic for malformed events, schema evolution demo (add a field mid-stream), idempotent sink writes.
- Evaluation: inject a schema change and a poison record; pipeline must keep running, DLQ must capture the record, new field must appear queryable.
- Deliverable: public repo with architecture diagram, README, demo script, and a 10-minute recorded walkthrough.
- Hours: ~60-75 over weeks 2-5. Kubernetes deployment optional and kept out of all public claims.

## Honest answers for the structural gaps

- **2+ years production experience:** "My production experience comes from research and project environments rather than two years in industry. What I can show is that I build like it's production — tested, monitored, documented — and I'm upfront that I'm earlier in that journey than the posting describes."
- **Demonstrated large-scale system design:** "I haven't operated systems at Reddit's 100B-events-per-day scale. I have built streaming pipelines end to end and studied how systems like this one are architected, and I'd want to earn that scale experience here rather than pretend I already have it."

## When this may go on the resume

Only after a skill above is genuinely learned AND written into data/context/, then re-registered — never before, and never-claim items never.
