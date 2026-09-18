# Study plan for Snowflake - Software Engineer - Backend

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map
| Skill / ask | Bucket | Why JD wants it |
|---|---|---|
| Java / Python / C++ / SQL fluency | Have | JD: "Fluency in Java, Python, C++, or SQL" |
| End-to-end customer-facing products (IoT, Kafka, Glue, Databricks projects) | Have | JD: "deep multi-faceted appreciation in building end-to-end customer facing products" |
| Algorithms & data structures | Missing, learnable | JD: "Knowledge of algorithms and data structures" |
| Distributed systems at scale | Learnable (concepts) / structural (years) | JD: "design and build... distributed platforms at scale," "globally distributed infrastructure" |
| Database internals | Missing, learnable | JD bonus: "familiarity with database internals" |
| Data governance / secure data sharing | Missing, learnable | JD: "share data... in governed and secure ways"; bonus "data governance"; data-security-plan clause |
| Payment systems experience | Missing, structural | JD bonus: "payment systems is a plus" |
| 2-7 yrs production large-scale systems | Missing, structural | JD: "2-7 years' industry experience designing, building, and supporting large-scale systems in production" |

No `never_claim_skills` terms (Kubernetes, Terraform, dbt, etc.) appear in this JD's text, so none are in play here.

## Tier 1 - before the screening call (week 1-2)
1. **Algorithms & data structures** - named directly in the JD. Learn arrays/hash maps, trees, graphs, heaps, complexity analysis. Resource: NeetCode 150 (free, neetcode.io). Self-check: solve one array/hash problem and one graph/tree problem in 30 min, then state their time/space complexity out loud.
2. **Distributed systems vocabulary** - JD: "distributed platforms at scale," "globally distributed infrastructure." Learn replication, partitioning, consensus basics (Raft), CAP theorem. Resource: MIT 6.5840 Distributed Systems lecture notes (free, pdos.csail.mit.edu/6.824). Self-check: explain the CAP tradeoff and the difference between replication and sharding, unaided, in 5 minutes.
3. **Data governance basics** - JD: "governed and secure ways," "abide by the company's data security plan." Learn RBAC, data lineage, access scoping. Resource: CMU 15-445 database systems intro lectures (free, 15445.courses.cs.cmu.edu), which cover authorization concepts. Self-check: describe how you'd design read-scoped access to a shared dataset for an external partner.

## Tier 2 - before the technical round (week 2-5)
1. **Database internals** - JD bonus ask. Learn B+trees, write-ahead logs, and query execution basics via CMU 15-445. Artefact: a short Python notebook implementing a toy B+tree or LSM-tree, with a written comparison of read/write tradeoffs.
2. **Governed data-sharing demo** - JD: "share data internally... or outside with external organizations... in governed and secure ways." Artefact: a small repo (Flask, which she already knows) exposing a dataset through scoped, permissioned API keys, with a README explaining the access-control design.
3. **System design for distributed platforms** - JD: "design and build features, and/or distributed platforms at scale." Artefact: a 1-2 page written system-design doc sketching a simplified "data sharing service," explicitly built on her existing Kafka/AWS Glue/Databricks project experience.

## Honest answers for the structural gaps
- **2-7 years large-scale production experience**: "My production experience is project- and internship-based rather than years running systems at Snowflake's scale, but I've built and operated streaming and data-pipeline systems end to end — Kafka, AWS Glue, Databricks — and I'm using this time to go deeper on distributed-systems fundamentals."
- **Payment systems**: "I haven't worked on payment systems specifically. What transfers is the same discipline around data integrity, auditability, and access control that payment systems demand, which is exactly what I've been building into my data-governance prep."

## When this may go on the resume
Only after each item above is actually learned or built, an artefact exists, it's written into data/context/, and it's re-registered as a skill — never before.
