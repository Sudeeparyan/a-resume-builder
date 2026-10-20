# Study plan for Roku - Software Engineer - Content Ingestion

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, C++ | Have | "Proficiency in one or more of: Python, Bash, C++, or Go" |
| AWS (EC2, S3, RDS, Glue, Lambda) | Have | "cloud platforms such as AWS and/or GCP" |
| Docker, Git, CI/CD, Linux | Have | "Manage containerized deployments… CI/CD pipelines and version control via Git" |
| Kafka, Postgres, MongoDB, Grafana | Have | "message queues… relational (Postgres) and non-relational (MongoDB)… Prometheus and Grafana" |
| Flask (APIs), ETL/ELT, Airflow | Have | "APIs and batch jobs for asset ingestion, processing, and distribution" |
| LangChain, prompt engineering | Have (partial) | "agentic AI workflows within active code repositories" |
| Bash scripting | Learnable (wk 1-2) | Named first in the language list; "strong foundation in… scripting" |
| GCP fundamentals | Learnable (wk 2-5) | "full-stack operations across cloud and on-premises… AWS and GCP" |
| Ansible | Learnable (wk 2-5) | "infrastructure… using Terraform and Ansible" |
| Prometheus + Alertmanager | Learnable (wk 2-5) | "monitoring, alerting, and observability using… Prometheus, Grafana, and Alertmanager" |
| Caching strategies, horizontal/vertical scaling | Learnable (wk 1-2) | "Understanding of message queues, caching strategies, and horizontal/vertical scaling" |
| ACR / content-ingestion domain | Learnable (wk 1-2) | "real-time content matching… for Roku's ACR platform" |
| MCP servers, agentic coding harness fluency | Learnable (wk 2-5) | "coding harnesses like Claude Code or Cursor, MCP servers, custom skills" |
| Terraform | Never-claim (learn only) | "Create and manage infrastructure… using Terraform" |
| Kubernetes | Never-claim (learn only) | "Manage containerized deployments using Docker and Kubernetes" |
| Go | Never-claim (skip — Python/C++ satisfy the list) | one-of language list |
| 1-3 years professional experience | Structural | "1–3 years of hands-on engineering experience" |
| On-call for critical production services | Structural | "participating in on-call rotations" — she has no production on-call history |

## Tier 1 - before the screening call (week 1-2)

1. **Bash scripting fundamentals** — pipes, exit codes, cron, writing a log-parsing script. Resource: *The Linux Command Line* (free PDF, linuxcommand.org). Self-check: in 30 min, write a script that tails a log, counts 5xx errors per minute, and alerts over a threshold — no notes.
2. **Scaling & caching vocabulary** — horizontal vs vertical scaling, cache-aside vs write-through, where Redis/CDN caches sit (concept only; Redis is never-claim as a skill). Resource: ByteByteGo's free "Scaling 101" articles/newsletter. Self-check: whiteboard aloud in 30 min how an ingestion API handling "millions of assets" scales from 1 to 100 machines.
3. **ACR and content-ingestion domain** — what Automatic Content Recognition is, how linear-feed fingerprinting works, what "asset ingestion" means for a streaming platform. Resource: Roku's own engineering blog (engineering.roku.com) plus the ACR Wikipedia overview. Self-check: explain in 2 minutes, out loud, what the Content Ingestion team produces and who consumes it.
4. **Message-queue depth beyond Kafka usage** — consumer groups, idempotency, dead-letter queues, backpressure, framed as ingestion concerns. Resource: Kafka's free official design docs. Self-check: in 30 min, write one page on how she'd make a partner-file ingestion job exactly-once.
5. **Honest-status script** — one sentence per missing tool stating where she is ("learning Ansible this month, built X with it"). Self-check: say each one without apologizing or inflating.

## Tier 2 - before the technical round (week 2-5)

1. **GCP core services mapped from AWS knowledge** — GCE≈EC2, GCS≈S3, Cloud SQL≈RDS, Pub/Sub≈Kafka-lite. Resource: Google Cloud Skills Boost free tier. Artefact: a written side-by-side migration walkthrough of her IoT analytics platform from AWS to GCP (markdown doc in a repo).
2. **Ansible for instance setup** — playbooks, roles, inventory, idempotent config. Resource: Jeff Geerling's free *Ansible for DevOps* (early chapters) and docs.ansible.com. Artefact: a repo with a playbook that provisions an Ubuntu VM with Docker, Postgres, and her ingestion app.
3. **Prometheus + Alertmanager on top of her Grafana knowledge** — metrics types, PromQL basics, alert rules, PagerDuty-style routing. Resource: prometheus.io docs + free "Prometheus Up & Running" excerpts. Artefact: a docker-compose demo where her Flask API exports metrics, Prometheus scrapes, Alertmanager fires a rule; screenshot + README.
4. **Agentic toolchain story** — the JD explicitly probes "MCP servers, custom skills… verify its output." Resource: Anthropic's free MCP documentation. Artefact: a short written walkthrough of driving an agent on an unfamiliar open-source repo, with verification steps she ran.
5. **On-call & observability literacy** — SLOs, error budgets, runbooks, incident retros. Resource: Google SRE book free chapters (sre.google). Artefact: a mock runbook for her demo pipeline, including alert thresholds and rollback steps.

## Build-now project (only if the JD needs a project type she has none of)

**Not built yet.** The JD runs Kubernetes/Terraform and she has no such project. Spec: **partner content-ingestion mini-platform**. Goal: simulate a content partner dropping metadata/video-manifest files; ingest, validate, store, expose status API. Data: synthetic asset manifests (JSON, ~10k records, seeded errors). Stack: Python + Flask API, Postgres, Docker, Terraform (localstack or free-tier AWS) for infra, Minikube for Kubernetes deployment, Prometheus+Grafana for monitoring. Evaluation: pipeline survives a killed pod, rejects malformed manifests, dashboard shows ingest rate and error alerts. Deliverable: public repo with README, architecture diagram, and a 5-minute demo video. ~40 hours across weeks 2-5. This stays off the resume until built and re-registered — Terraform/Kubernetes are never-claim until then.

## Honest answers for the structural gaps

- **1-3 years experience:** "I'm early-career — my experience is project and research based, including building streaming and ETL platforms end to end. I'm upfront that I haven't held a multi-year production role yet, and I'm looking for exactly this kind of team to grow in."
- **On-call:** "I haven't been on a production on-call rotation, but I've studied SRE practices and built alerting into my own projects — I take ownership seriously and I'm ready to carry a pager."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
