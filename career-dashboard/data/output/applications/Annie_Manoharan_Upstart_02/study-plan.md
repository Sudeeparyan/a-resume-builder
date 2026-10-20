# Study plan for Upstart - Software Engineer, Lifecycle

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python / Java | Have | "Proficiency in at least one backend language such as Kotlin, Java, Ruby, or Python" |
| AWS (EC2, S3, Lambda, Glue, RDS) | Have | "microservices and APIs in a cloud environment (preferably AWS)" |
| Kafka / Flink / Spark, real-time streaming | Have | "real-time event streaming systems and high-throughput messaging architectures" |
| Databricks, ETL/ELT, SQL | Have | "data pipeline tooling (e.g., Airbyte, Fivetran, Databricks)" |
| Docker, CI/CD, Flask, TDD | Have | "Design and build scalable backend services… deploy frequently" |
| Kotlin | Learnable | Listed first among backend languages; trivial hop from Java |
| Microservices & API system design | Learnable | Core of the role; probe depth beyond her project scale |
| CDPs, customer segmentation, campaign orchestration | Learnable | "particularly in environments involving CDPs, customer segmentation, or campaign orchestration" |
| Reverse ETL (Hightouch/Census concept) | Learnable | "reverse ETL workflows" named in impact section |
| Messaging channels: email/SMS/push deliverability | Learnable | Team owns "preference management, email, SMS, push notifications" |
| Marketing automation platforms (Iterable, Braze, SFMC) | Learnable | Named preferred tools; concepts matter more than the GUI |
| 3+ yrs production SWE + leading medium projects | Structural | "3 years of experience… Lead medium-sized projects independently" |
| Supporting Marketing/Growth/GTM teams | Structural | Preferred: "Experience supporting Marketing, Growth, or GTM teams" |
| Airbyte, Fivetran | Never-claim | In never_claim_skills; learn the category, never assert hands-on |

## Tier 1 - before the screening call (week 1-2)

1. **Lifecycle marketing & CDP vocabulary.** Learn what a CDP does, identity resolution, segmentation, and the difference between campaign orchestration and transactional messaging. Resource: Segment's free "CDP guide" (segment.com/resources) plus Iterable's blog glossary. Self-check: explain in 5 minutes, unaided, how customer data flows from product events to an email send, naming each stage.
2. **Reverse ETL concept.** Learn what reverse ETL is, why warehouses push data back to SaaS tools, and where Hightouch/Census fit — conceptually, since Airbyte/Fivetran are never-claim. Resource: Hightouch's free "What is Reverse ETL?" guide. Self-check: draw a reverse-ETL diagram on paper and contrast it with classic ETL in two sentences each.
3. **Email/SMS/push fundamentals.** Deliverability, opt-in/opt-out and preference management, provider APIs (Twilio, SendGrid, FCM/APNs). Resource: Twilio's free Messaging docs and SendGrid's deliverability guide. Self-check: answer "why can a 'sent' email never arrive?" with at least four distinct reasons.
4. **Kotlin crash pass.** Syntax, null safety, coroutines at reading level — enough to say "Java-daily, Kotlin-readable." Resource: official Kotlin Koans (kotlinlang.org). Self-check: complete 10 Koans and rewrite one small Java class in Kotlin.
5. **Her honest position script.** For each must-have, one sentence: what she's built, what she's learning. Self-check: record herself answering "walk me through your microservices experience" in 90 seconds without overclaiming.

## Tier 2 - before the technical round (week 2-5)

1. **Event-triggered messaging pipeline.** Kafka consumer in Python that triggers templated "email/SMS" sends (mocked providers), with idempotency and retry logic. Artefact: public GitHub repo with README architecture diagram and docker-compose one-command run.
2. **Reverse ETL walkthrough.** Model customer segments in PostgreSQL, write a small Python sync that pushes a segment to a mock destination API with diffing and rate limits. Artefact: Jupyter notebook + written walkthrough titled "Reverse ETL, from scratch, no vendor tools."
3. **Marketing-platform API study.** Read Iterable's and Braze's public REST docs; map their objects (users, events, campaigns, journeys) to a generic schema. Artefact: one-page comparison doc she can discuss — shows domain fluency without claiming production use.
4. **Notification-platform system design.** Design Upstart's unified comms platform on paper: ingestion, preferences, scheduling, per-channel workers, observability. Resource: "System Design Interview" (Alex Xu) notification chapter + AWS SQS/SNS docs. Artefact: written design doc with trade-offs section, rehearsed as a 30-minute whiteboard answer.
5. **Experimentation/messaging-analytics depth.** How A/B tests on messaging are measured (holdout groups, conversion attribution) since JD says "experimentation capabilities." Artefact: short notebook simulating a holdout-group lift calculation on synthetic send data.

## Build-now project (only if the JD needs a project type she has none of)

Needed — no messaging/marketing-automation project exists. **Not built yet.**
- Goal: miniature lifecycle-messaging platform proving the JD's core loop: events in, right message out.
- Data: synthetic user events (signups, purchases) generated by a Python producer.
- Stack: Python + Kafka + PostgreSQL (preferences/segments) + mocked SendGrid/Twilio adapters; Docker Compose; GitHub Actions CI.
- Features: preference management (opt in/out per channel), one event-triggered journey (welcome series), one segment-triggered batch campaign.
- Evaluation: idempotent delivery under consumer restarts; unit tests for preference logic; end-to-end test event → mock send.
- Deliverable: repo + README with architecture diagram + 5-minute Loom walkthrough.
- Hours: ~35 over weeks 2-4.

## Honest answers for the structural gaps

- "My professional background is in data and ML engineering — about X years — not three years of pure product-backend work; what transfers directly is building and operating streaming pipelines and APIs in production on AWS."
- "I haven't supported a marketing org before, but I've sat with non-engineering stakeholders to turn fuzzy requirements into shipped pipelines; the CDP and campaign-orchestration domain is what I've been deliberately studying for this role."

## When this may go on the resume

Only after it is learned AND written into data/context/, then re-registered.
