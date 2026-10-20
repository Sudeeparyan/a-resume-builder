# Study plan for Palantir - Backend Software Engineer - Infrastructure

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Java | Have | "Strong coding skills... such as Java, C++, Python, Rust" |
| Python, C++ | Have | Same requirement line; Palantir polyglot backends |
| Spark, Kafka, Flink | Have | "Open-source technologies like Cassandra, ElasticSearch, Spark, Kafka, Kubernetes, Flink" |
| Docker, Linux, AWS, Git, CI/CD, TDD, Multithreading, Design patterns | Have | "cloud infrastructure", "Industry-standard build tooling", "defensive" code quality bar |
| CS/engineering degree | Have | "Engineering background in Computer Science... or similar field" (MS, University of Arkansas) |
| Cassandra | Missing, learnable (this plan) | "Automating the deployment, management, and operations of... Cassandra, Elasticsearch, Kafka" |
| Gradle | Missing, learnable (this plan) | "Industry-standard build tooling, including Gradle and GitHub" |
| Distributed systems fundamentals | Missing, learnable (this plan) | "database technologies, distributed systems, large scale data systems" |
| Tracing / observability (OpenTelemetry) | Missing, learnable (this plan) | "Tracing and performance observability in high scale distributed microservice architectures" |
| Search & indexing internals | Missing, learnable (this plan) | "performant search and indexing ecosystem for complex granularly permissioned data" |
| Kubernetes | Never-claim (learn concepts only) | "scheduling hundreds of thousands of containers every hour" |
| Elasticsearch | Never-claim (learn concepts only) | Named in technologies and search responsibilities |
| Go, Rust | Never-claim (learn to read only) | "Different backend languages, including Java, Rust, and Go" |
| Production HA distributed systems experience | Missing, structural | "Experience developing and managing highly-available distributed systems is beneficial, but not required" |
| US security clearance | Structural (optional) | "beneficial, but not necessary" |

## Tier 1 - before the screening call (week 1-2)

1. **Distributed systems vocabulary.** JD: "distributed systems, large scale data systems." Learn: replication, partitioning, consistency models, CAP tradeoffs, leader election. Resource: MIT 6.824 lecture videos + notes (free, pdos.csail.mit.edu/6.824). Self-check: in 30 min, whiteboard why a permissioned search system would pick quorum reads vs. leader reads, out loud.
2. **Cassandra data model.** JD: "Automating the deployment... of... Cassandra." Learn: partition keys, clustering columns, tunable consistency, why joins don't exist. Resource: official Apache Cassandra docs, "Cassandra Basics" (cassandra.apache.org/doc). Self-check: design a schema for time-series access logs in 30 min and defend the partition key.
3. **Container orchestration concepts (Kubernetes — learn, never claim).** JD: "orchestrating and efficiently scheduling hundreds of thousands of containers every hour." Learn: pods, schedulers, resource requests/limits, autoscaling. Resource: kubernetes.io tutorials (concepts sections only). Self-check: explain in 30 min what a scheduler does when a node fails mid-rollout.
4. **Search & indexing basics (Elasticsearch internals — concepts, never claim).** JD: "performant search and indexing ecosystem for complex granularly permissioned data." Learn: inverted indexes, Lucene segments, filter vs. query, how ACL filtering composes with ranking. Resource: Elasticsearch guide, "Elasticsearch from the Bottom Up" (free, elastic.co). Self-check: sketch query execution for a permission-filtered keyword search.
5. **Gradle + the honest-status story for every gap.** JD: "build tooling, including Gradle and GitHub." Learn: tasks, dependencies, build.gradle structure (she has Maven-adjacent instincts from Java). Resource: Gradle "Getting Started" guides (gradle.org/guides). Self-check: write a minimal Java build.gradle with a test task from memory, and rehearse one honest sentence per gap: "I haven't used X in production; here's what I know and how I'm learning it."

## Tier 2 - before the technical round (week 2-5)

1. **Cassandra hands-on.** Run a 3-node local cluster, model real data, kill a node, observe hinted handoff. Artefact: a small repo with docker-compose cluster, schema, and a one-page benchmark writeup (throughput at ONE vs. QUORUM).
2. **Distributed tracing.** Instrument a two-service Java or Python demo with OpenTelemetry, export to Jaeger, break something on purpose, find it via traces. Artefact: repo plus a Grafana/Jaeger dashboard walkthrough doc (builds on her Grafana).
3. **Scheduler design literacy.** JD's "hundreds of thousands of containers every hour" is a Borg/Kubernetes-scale claim. Read the Google Borg paper and the Kubernetes scheduler docs. Artefact: a written two-page comparison, "how large-scale container schedulers make placement decisions," in her own words.
4. **Palantir stack reading fluency (Go/Rust — never claim).** Work through a short Go tutorial, enough to read infrastructure code in an interview pairing session without freezing. Artefact: annotated notes on one small open-source Go service (e.g., a Prometheus exporter), showing she can follow the code.

## Build-now project (only if the JD needs a project type she has none of)

Not triggered. The JD's project-shaped demands are CI/CD-adjacent automation (she has CI/CD) and distributed-infrastructure depth, which Tier 2 items 1-3 cover as artefacts. The tempting Kubernetes/Terraform build is off-limits as a claimable skill and must not become a resume line.

## Honest answers for the structural gaps

- **Production distributed systems:** "I haven't operated highly-available distributed systems in production yet — my hands-on experience is project and research scale, with Kafka, Flink and Spark. I've spent the weeks since applying going deep on Cassandra internals and scheduler design, because that's the gap I knew this team would test."
- **Security clearance:** "I don't hold a clearance. The posting says it's beneficial but not necessary, and I'm fully willing to go through the process wherever I'm eligible."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — and Kubernetes, Elasticsearch, Go and Rust stay off permanently, per her never-claim list.
