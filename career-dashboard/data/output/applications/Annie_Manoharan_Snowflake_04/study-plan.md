# Study plan for Snowflake - Software Engineer (AI-Native), Database Engineering

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| C++, Java, Python ("proficiency in one or more") | Have | Core engine implementation languages |
| Bachelor's/Master's in CS or related | Have | Baseline qualification; she holds both |
| Distributed systems fundamentals ("distributed execution, storage systems, concurrency, fault tolerance") | Have (basics, via Spark/Flink/Kafka/Multithreading) — depth in Tier 2 | Engine work is distributed execution and storage |
| AI coding agents ("strong hands-on experience... model strengths, failure modes, limitations") | Missing, learnable | The role's defining ask; screened on it early |
| Measuring agent effectiveness ("systematically measuring their effectiveness") | Missing, learnable | Preferred qualifier that separates power users |
| Database internals ("query optimization or execution... large-scale storage and retrieval") | Missing, learnable | Preferred qualifier; heavily probed in the technical round |
| 2+ years operating complex production systems | Missing, structural | Cannot be manufactured in weeks |
| Go, Rust ("such as... Go, Rust") | Never-claim | Optional in the JD's list; her C++/Java/Python already satisfy it |
| Snowflake platform itself | Never-claim | Learn the architecture concepts; never claim product experience |

## Tier 1 - before the screening call (week 1-2)

1. **AI coding agents as a workflow, not a toy.** Learn agentic coding loops (plan -> generate -> verify -> iterate) and where agents fail: hallucinated APIs, silent test weakening, context rot. Resource: Anthropic's "Claude Code" docs and best-practices guide (free). Self-check: in 30 minutes, explain three concrete failure modes and one mitigation each, aloud, without notes.
2. **Database internals vocabulary.** Storage vs. execution, row vs. columnar, vectorized execution, cost-based optimization. Resource: Carnegie Mellon 15-445 lectures 1-6 (free on YouTube). Self-check: draw the lifecycle of one SQL query from parse to result in 30 minutes.
3. **Snowflake's architecture as a concept.** Decoupled storage/compute, virtual warehouses, micro-partitions. Resource: Snowflake's official "Key Concepts & Architecture" docs (free). Self-check: explain why storage/compute separation matters for elasticity, in writing, one page. This is conceptual literacy — she must never claim Snowflake experience.
4. **Distributed execution refresher aimed at her gap.** Shuffle, partitioning, stragglers, fault recovery. Resource: MIT 6.824 lecture notes on MapReduce/Spark (free). Self-check: explain how Spark recovers a lost partition, and contrast with Flink checkpointing (she knows these tools; now explain the *why*).

## Tier 2 - before the technical round (week 2-5)

1. **Query execution depth.** Volcano/iterator model vs. vectorized push models. Resource: CMU 15-445 lectures 7-13 plus the paper "Volcano vs. Vectorized" summaries. Artefact: a written walkthrough comparing the two models with a worked example query.
2. **Query optimization fundamentals.** Cost models, join ordering, statistics. Resource: CMU 15-721 (advanced) optimization lectures (free). Artefact: a notebook that takes 5 join queries through a simple rule-based vs. cost-based optimizer she implements in Python.
3. **Measured AI-agent usage (the preferred qualifier, verbatim).** Build a personal harness: run a coding agent on 10 small tasks, log success rate, edit distance, and failure classes. Artefact: a small repo with the benchmark script, results table, and a one-page "what I changed in my prompts/workflow" memo.
4. **Columnar storage and compression.** Parquet layout, encoding, predicate pushdown. Resource: Parquet format documentation plus "Dremel" paper (free). Artefact: a notebook that reads Parquet files, measures compression ratios across encodings, and explains the results.
5. **Fault tolerance and operability.** Retries, idempotency, observability — the JD's "reliable, observable solutions with measurable outcomes." Resource: "Designing Data-Intensive Applications" chapters 1-3 (library). Artefact: a written postmortem-style analysis of a failure in her Medical IoT platform, reframed with these concepts.

## Build-now project (database engine internals — she has no project of this type)

**Label: not built yet.** Goal: a mini vectorized SQL query engine in C++ (her strongest systems language). Data: TPC-H SF1 lineitem table exported to Parquet. Stack: C++20, Apache Arrow/Parquet C++ library, CMake, Google Benchmark. Scope: SELECT with filters, one aggregate (GROUP BY SUM), one hash join, over columnar batches of 1024 rows. Evaluation: compare against DuckDB on the same queries; report execution time and rows/sec; document why DuckDB wins (it will). Deliverable: public repo with README covering architecture, benchmark numbers, and a "what I learned about vectorized execution" section. Effort: ~40 hours over weeks 3-6. This artefact speaks directly to "query optimization or execution... large-scale storage and retrieval systems."

## Honest answers for the structural gaps

**"2+ years building and operating complex production systems"**: "My production experience comes from academic and personal systems, not multi-year industry operations — I want to be upfront about that. What I can show is that I built and operated a real-time IoT analytics pipeline with Kafka and Flink, and I understand what 'operability' demands: monitoring, failure handling, and measurable outcomes, which is exactly what I'm eager to do at Snowflake's scale."

**Depth in distributed systems**: "My distributed systems exposure is through Spark, Flink, and Kafka rather than kernel-level database work — that's why I built a small vectorized query engine to close the gap, and I'd love to walk you through what it taught me."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — nothing in this plan is resume material today.

*Word count: ~880.*
