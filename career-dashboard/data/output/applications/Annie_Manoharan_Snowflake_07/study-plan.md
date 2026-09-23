# Study plan for Snowflake - Software Engineer - Backend

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill the JD names | Bucket | Why the JD wants it |
|---|---|---|
| Fluency in Java, Python, C++, or SQL | Have | "Fluency in Java, Python, C++, or SQL" |
| Algorithms and data structures | Have | "Strong fundamental computer science skills" |
| 2-7 years building large-scale systems in production | Missing - structural | "2-7 years' of industry experience designing, building, and supporting large-scale systems in production" |
| End-to-end customer-facing products | Missing - structural (partial) | "Deep multi-faceted appreciation in building end-to-end customer facing products" |
| Distributed platforms at scale | Missing - learnable | "Design and build features, and/or distributed platforms at scale" |
| Database internals | Missing - learnable | "Familiarity with database internals ... is a plus" |
| Data governance | Missing - learnable | "...or data governance ... is a plus"; "sharing live data in governed and secure ways" |
| Snowflake / Data Cloud / secure data sharing | Never-claim | The product itself; learn it, never list it |

## Tier 1 - before the screening call (week 1-2)

1. **Cloud data warehouse architecture** (reacting to "Data Cloud", "Open Lakehouse"). Learn storage/compute separation, columnar storage, multi-cluster compute, why Snowflake beats shared-nothing designs for elasticity. Resource: Snowflake docs, "Key Concepts & Architecture" (docs.snowflake.com). Self-check: in 5 minutes, out loud, explain why decoupling storage from compute matters and one tradeoff it creates.
2. **Distributed systems vocabulary** ("distributed platforms at scale", "globally distributed infrastructure"). Learn partitioning/sharding, replication, consistency models, CAP, idempotency, backpressure. Resource: System Design Primer (free, github.com/donnemartin/system-design-primer). Self-check: pick her IoT project and explain where each of these concepts applies or would break.
3. **Database internals fundamentals** ("database internals ... is a plus"). Learn B-tree vs LSM-tree indexes, buffer pool, query execution pipeline, transactions/ACID. Resource: CMU 15-445 lecture videos (free on YouTube). Self-check: trace one SQL query from parse to result on paper.
4. **Data governance vocabulary** ("governed and secure ways", confidentiality duties). Learn RBAC, column/row-level security, secure views, data sharing vs data copying. Resource: Snowflake docs, "Snowflake Security & Governance Overview." Self-check: describe how to share one table with an external org without copying it, naming the mechanisms.
5. **Honest position statements.** Draft one sentence per gap above stating where she actually is (e.g., "coursework + personal projects, not production scale"). Self-check: say each without apologizing or inflating.

## Tier 2 - before the technical round (week 2-5)

1. **Snowflake hands-on (learning only - never-claim as a skill).** Free trial: load data, create a share, use Time Travel, set a row access policy. Artefact: a private repo with SQL scripts plus a written walkthrough of what she tried and what surprised her.
2. **Database internals depth.** Implement a small B-tree index or LSM-tree key-value store in Java or Python with tests. Artefact: GitHub repo (~300-500 lines) with README explaining design choices; be ready to whiteboard it.
3. **Distributed systems depth.** Implement consistent hashing plus simple leader election in Python, simulating node failure. Artefact: small repo with a failure-scenario demo script and short write-up.
4. **How Snowflake actually works underneath.** Read Snowflake's public engineering material on FoundationDB metadata and the original SIGMOD paper ("The Snowflake Elastic Data Warehouse"). Artefact: one-page written summary she could discuss: storage format, metadata layer, query processing, concurrency.
5. **System design interview format.** Practice two full backend design prompts (e.g., "design a data-sharing service") out loud, 40 minutes each, focusing on requirements first. Artefact: two written design docs with tradeoff sections.

## Build-now project

**"Governed Mini Data Share" (not built yet).** The JD centers on "build the backend services for data cloud to help our customers to share data." Goal: a multi-tenant REST service where one tenant publishes a dataset and another queries it under enforced policies. Data: any public tabular dataset (e.g., NYC taxi or COVID open data). Stack: Java or Python + PostgreSQL (both registered skills) with an RBAC metadata layer, row/column masking rules, and audit logging. Evaluation: policy tests (denied access must fail), simple load test with locust or k6 showing latency under concurrent readers. Deliverable: public repo with README architecture diagram, tests, and a 1-page tradeoffs doc. Hours: ~25-30 across weeks 3-5.

## Honest answers for the structural gaps

- **On "2-7 years of production experience":** "I don't have years of production-scale experience yet - my background is research and project work in ML systems and streaming pipelines, like a real-time medical IoT analytics platform. I know that's the gap, and it's exactly why I've spent the last month building and reading for production patterns."
- **On customer-facing products:** "My work so far has been research and personal projects rather than shipped customer products, but I built my expense-tracker app end to end - data model to UI to deployment - and I'm eager to do that with real users and real stakes."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered - never before.
