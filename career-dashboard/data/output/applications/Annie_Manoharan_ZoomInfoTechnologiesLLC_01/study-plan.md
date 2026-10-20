# Study plan for ZoomInfo Technologies LLC - Software Engineer III - Data Acquisition

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| Java, OOP ("Strong proficiency with Java") | Have | Core language of the acquisition services |
| Apache Airflow ("workflow orchestration") | Have | Scheduled batch ETL/ELT jobs |
| Apache Kafka ("streaming technologies such as Kafka") | Have | Event-driven ingestion |
| Apache Spark / PySpark ("DataProc, Spark") | Have | Distributed processing |
| ETL/ELT, data validation and quality ("ingest, validate, normalize, enrich") | Have | Core of Data Acquisition |
| SQL, schema design, data modeling | Have | Storage/query and data quality work |
| Cloud, AWS ("at least one cloud provider") | Have | Cloud-fluent, but JD prefers GCP |
| Docker, CI/CD, Grafana, Linux | Have | Production engineering practices, observability |
| GCP services: GCS, Pub/Sub, Dataflow, DataProc ("preferably GCP") | Missing, learnable | Their actual stack; AWS concepts transfer |
| Apache Beam / Google Dataflow | Missing, learnable | Named first in their processing list |
| Pipeline observability at scale ("throughput, latency, cost, error rates") | Missing, learnable | They probe operational maturity |
| Controlled backfills, dedup strategies | Missing, learnable | Data-quality interview staples |
| 3+ years professional engineering, "operating production data pipelines" | Missing, structural | Time and production scale cannot be compressed into weeks |
| Kubernetes/GKE, Terraform, Snowflake, BigQuery, Spark Streaming (nice-to-haves) | Never-claim | May be studied privately; never asserted as hers |

## Tier 1 - before the screening call (week 1-2)

1. **GCP vocabulary via AWS mapping.** Learn GCS, Pub/Sub, Dataflow, DataProc as counterparts to S3, Kafka, Glue/EMR. Resource: Google Cloud's free "GCP for AWS Professionals" docs and free tier. Self-check: in 30 min, explain aloud when ZoomInfo would pick Pub/Sub vs Kafka and Dataflow vs DataProc, with one trade-off each.
2. **Apache Beam programming model.** PCollections, ParDo, windowing, watermarks, triggers. Resource: Beam Programming Guide (beam.apache.org). Self-check: draw a session-windowed pipeline on paper and explain what a watermark does to late data.
3. **Data acquisition domain language.** Ingestion, normalization, deduplication, enrichment, backfill, schema validation — the JD's own verbs. Resource: Fundamentals of Data Engineering (Reis & Housley), free chapters via O'Reilly trial. Self-check: whiteboard an end-to-end acquisition pipeline in 30 min and name the failure mode at each stage.
4. **Beam-vs-Spark/Flink positioning.** They list Beam, Spark and Flink alternatives; interviewers test judgment. Resource: Beam capability matrix + Dataflow docs. Self-check: 30-min written comparison of Beam vs Spark for a near-real-time feed.
5. **Honest positioning script.** Prepare a 60-second answer on where she is with GCP: strong AWS/Kafka/Spark base, actively ramping on GCP. Self-check: record it, replay, remove anything that overstates.

## Tier 2 - before the technical round (week 2-5)

1. **Beam/Dataflow batch pipeline.** Build a Java Beam job that ingests a public dataset, validates schema, dedups and writes partitioned output, run locally on DirectRunner. Artefact: GitHub repo with README, sample input/output and design notes.
2. **Streaming ingestion demo.** Pub/Sub (free tier) or local emulator feeding a Beam streaming job with windowing and late-data handling. Artefact: same repo, second module, plus a 1-page walkthrough of throughput and watermark behavior.
3. **Pipeline observability lab.** Instrument the pipeline with throughput, latency and error-rate metrics into Grafana (already Have). Artefact: dashboard screenshot plus a written SLI/SLO definition for the pipeline.
4. **Data-quality and backfill design doc.** Write how she would do schema validation, dedup, retries and a controlled backfill for a 1TB/day feed. Artefact: 2-page design document in the repo.
5. **Failure-mode drill.** Practice troubleshooting narratives: skewed keys, poison messages, slow sinks, cost spikes on Dataflow. Artefact: written incident walkthrough (symptom, hypothesis, fix, prevention) for two simulated failures.

## Build-now project (not built yet)

She has streaming/ML projects but no data-acquisition pipeline project; this JD needs one.

- Goal: mini B2B-style data acquisition system mirroring the JD's "acquire, transform, validate, store".
- Data: public company/domain datasets (e.g., SEC EDGAR filings or open business registries), plus a simulated webhook feed.
- Stack: Java + Apache Beam (batch + streaming), Pub/Sub emulator or Kafka, Airflow for scheduling, PostgreSQL sink, Docker Compose.
- Evaluation: dedup rate, schema-rejection rate, end-to-end latency, restart/backfill correctness after a kill.
- Deliverable: public repo with architecture diagram, Grafana dashboard, and a README covering failure modes.
- Hours: ~40 over weeks 2-5, overlapping Tier 2 items 1-3.

## Honest answers for the structural gaps

- "I have under three years of professional experience, so I won't claim otherwise; what I bring is hands-on pipeline work with Airflow, Kafka, Spark and Flink in research and project settings, and I'd rather show you my beam acquisition repo than inflate a number."
- "My production exposure is on AWS, not GCP, and not yet at ZoomInfo's scale. The concepts — partitioning, backpressure, exactly-once trade-offs — transfer, and I've been drilling the GCP equivalents specifically for this role."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — never before, and never any never-claim skill in any wording.
