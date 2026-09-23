# Study plan for Snowflake - Software Engineer - AIM Virtualization

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| "2-7 years of experience in SQL" | Have (SQL, PostgreSQL, MySQL, SQL Server, Flink SQL) | Core working language of the platform |
| "other functional programming languages" | Have (Python, Java, C++ suffice as evidence of range) | Their runtime is compiler-adjacent code |
| "Solid knowledge of database internals, including query parsing, optimization, and execution" | Missing, learnable (plan below) | The literal product: a virtualization runtime that re-executes foreign SQL on Snowflake |
| "syntactic and semantic analysis" | Missing, learnable | Parsing/validating source-dialect SQL before translation |
| "wire protocols" | Missing, learnable | Emulating client protocols so "existing applications instantly work on Snowflake" |
| "data ingest/egress" | Have (ETL/ELT, Kafka, Spark, Flink) | Bulk migration path for customers moving platforms |
| "AI-based development / AI-driven software synthesis workflows" | Have foundation (LangChain, RAG, Prompt engineering, Llama 3.2, Ollama); depth learnable | Team is "one of Snowflake's leading teams in AI-driven software synthesis" |
| "BS/MS/PhD in Computer Science" | Have (MS, University of Arkansas) | Stated education bar |
| Snowflake platform internals | Never-claim as experience; learn as domain knowledge | The product itself — learn its architecture, never say she's used it |
| 2-7 years professional experience | Structural | Cannot be manufactured; answer honestly (below) |

## Tier 1 - before the screening call (week 1-2)

1. **Query processing pipeline vocabulary** — parser, binder/semantic analyzer, logical plan, optimizer, physical plan, executor; know what each stage does to a SELECT. Resource: CMU 15-445 lecture 1-3 (free on YouTube). Self-check: in 30 min, hand-trace `SELECT a, COUNT(*) FROM t WHERE b > 5 GROUP BY a ORDER BY 2 LIMIT 10` through all six stages on paper.
2. **Reading query plans** — EXPLAIN/EXPLAIN ANALYZE in PostgreSQL: sequential vs index scan, nested loop vs hash join, cost units. Resource: PostgreSQL docs "Using EXPLAIN". Self-check: run EXPLAIN on three joins in a local Postgres, predict which plan wins and why, then verify.
3. **Snowflake architecture as domain knowledge** — separation of storage/compute, virtual warehouses, micro-partitions, result caching; enough to discuss the product intelligently, never as usage experience. Resource: Snowflake official docs, "Key Concepts & Architecture". Self-check: whiteboard the three-layer architecture and explain why it helps migration customers, in 30 minutes, unaided.
4. **SQL dialect differences** — why "without changing SQL or APIs" is hard: dialect grammar differences, type systems, NULL/semantics edge cases (Oracle vs Postgres vs SQL Server, all of which she has touched). Resource: sqlglot GitHub README + docs (open-source SQL transpiler). Self-check: list 10 concrete dialect incompatibilities (e.g., TOP vs LIMIT, NVL vs COALESCE) from memory.
5. **AI-assisted engineering narrative** — turn her existing LangChain/RAG work into a story about directing AI to generate and verify code, since the JD stresses "direct AI systems to synthesize components." Resource: Snowflake engineering blog posts on AI-assisted development. Self-check: 30-min rehearsal — explain aloud, twice, how she'd use an LLM to generate a SQL parser rule plus tests, and how she'd verify it.

## Tier 2 - before the technical round (week 2-5)

1. **Parsing and semantic analysis** — grammars, ASTs, recursive-descent vs parser generators, binding names/types to catalog entries. Artefact: a small repo with a hand-written recursive-descent parser in Python for a SELECT/WHERE/GROUP BY subset, with an AST pretty-printer and 30+ tests.
2. **Query optimization** — logical rewrite rules (predicate pushdown, projection pruning) and cost-based join ordering. Artefact: extend the repo with a rule-based optimizer that rewrites plans, plus a notebook comparing before/after row estimates on TPC-H-style data.
3. **Execution models** — volcano/iterator model vs vectorized/batch execution; why Snowflake is vectorized. Artefact: a written walkthrough (markdown in the repo) showing the same query executed both ways on a 1M-row synthetic table, with timing numbers.
4. **Wire protocols** — how a client actually talks to a database: message framing, startup, query/response cycle. Artefact: a toy server implementing the PostgreSQL v3 wire protocol subset (startup, simple query) that psql can connect to, with a README walkthrough.
5. **AI-based synthesis workflow** — JD's "engineering processes around AI-based software synthesis." Artefact: a short written design doc: how to use an LLM to generate dialect-translation rules, with golden-file tests and diff review as the verification loop.

## Build-now project (only if the JD needs a project type she has none of)

She has no database-internals project; every existing project is CV, embedded, IoT, or LLM apps. **Mini query engine — "not built yet".** Goal: a working subset SQL engine demonstrating the full parse-plan-execute pipeline the JD names. Data: generated TPC-H-like tables (lineitem, orders) as CSV/Parquet, ~1M rows. Stack: Python (or C++ if she wants to lean into performance), Pandas only for CSV loading — engine logic hand-written. Scope: SELECT, WHERE, JOIN (hash join), GROUP BY, ORDER BY, LIMIT. Evaluation: correctness vs SQLite on 20 test queries; latency vs naive execution to show optimizer wins. Deliverable: public repo with parser, planner, optimizer rules, iterator-model executor, pytest suite, and a README design walkthrough. Hours: ~40 over weeks 2-5 (this IS the Tier 2 artefact, consolidated).

## Honest answers for the structural gaps

- **2-7 years experience:** "I'm earlier in my career than the upper end of that range, but I've built and shipped data pipelines and ML systems end to end, and I've spent the last weeks going deep on exactly what this team does — I can show you a query engine I built to prove it."
- **Production database internals depth:** "My internals knowledge is newly built, not battle-tested at production scale — but it's fresh, I've implemented it rather than just read about it, and depth is what I'm here to grow."
- **Snowflake itself:** "I haven't worked on Snowflake professionally; I've studied its architecture closely because what AIM is doing — virtualization as the migration path — is the most interesting problem in data right now."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
