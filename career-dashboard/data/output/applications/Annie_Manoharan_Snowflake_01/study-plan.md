# Study plan for Snowflake - Software Engineer - Database Engineering

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why JD wants it |
|---|---|---|
| Java / C++ | Have | "Fluency in Java or C++" |
| Linux | Have | "development in a Linux environment" |
| Multithreading / concurrency | Have | "Systems programming skills including multi-threading, concurrency" |
| Testing, debugging, documentation | Have | "implementation testing, debugging and documentation" |
| Bachelor's + Master's degree | Have | "Bachelor's degree... Masters or PhD preferred" — she holds both; not a gap |
| SQL (as a user) | Have | "SQL or other database technologies" |
| Spark / large-scale data processing | Have | "large-scale data processing solutions like Hadoop and Spark" |
| Columnar databases (via ClickHouse) | Have | "Columnar Databases" |
| Distributed systems fundamentals (CAP, transactions, consistency) | Missing, learnable | "large scale distributed systems, transactions and consistency models" |
| Query optimization / execution / compiler design | Missing, learnable | "Query optimization, query execution, compiler design" |
| Storage-engine internals (B-tree / LSM) | Missing, learnable | "storage engines like RocksDB, InnoDB, BerkeleyDB" |
| Database replication technology | Missing, learnable | "Experience in database replication technology" |
| Data structures & algorithms depth | Missing, learnable | "strong CS fundamentals including data structures, algorithms" |
| Production distributed KV store internals (FoundationDB-scale) | Structural | "internals of distributed key value stores like FoundationDB" |
| Production MySQL/PostgreSQL internals engineering | Structural | "Experience with MySQL, PostgreSQL internals" |
| Hadoop | Never-claim | listed among "large-scale data processing" tools in the JD |
| Snowflake (the platform, as a used product) | Never-claim | JD references building "the Snowflake Data Cloud" itself — she cannot claim prior use of it as a tool |

## Tier 1 - before the screening call (week 1-2)

1. **Distributed systems vocabulary** (CAP theorem, consistency models, 2PC). Resource: MIT 6.824 lecture notes (pdos.csail.mit.edu/6.824). Self-check: explain, in 30 minutes without notes, the difference between strong and eventual consistency and when each applies.
2. **Query optimization basics** (cost-based vs rule-based, join ordering). Resource: CMU 15-445 Intro to Database Systems lectures (15445.courses.cs.cmu.edu). Self-check: sketch how a query planner would choose a join order for a 3-table query.
3. **Storage engine shapes** (B-tree vs LSM-tree tradeoffs). Resource: RocksDB wiki (github.com/facebook/rocksdb/wiki). Self-check: write, from memory, why LSM-trees favor write throughput and B-trees favor point reads.
4. **Replication concepts** (leader-follower, quorum writes). Resource: PostgreSQL replication docs (postgresql.org/docs/current/high-availability.html). Self-check: describe how a replica catches up after a network partition.
5. **DS&A refresh for systems interviews**. Resource: MIT OCW 6.006 Introduction to Algorithms. Self-check: solve one graph and one tree problem timed at 20 minutes.

## Tier 2 - before the technical round (week 2-5)

1. **Toy LSM-tree storage engine in C++**: memtable + SSTable flush + simple compaction. Proof artefact: a small GitHub repo with a README benchmarking write throughput vs a naive approach.
2. **Mini SQL query optimizer**: parse a SQL subset, build a logical plan, apply one rewrite rule (predicate pushdown). Proof artefact: a repo with before/after query plans on 2-3 example queries.
3. **Simplified Raft-based key-value store** (in-memory, single leader, log replication). Proof artefact: a repo plus a short write-up of what breaks under a simulated leader crash — directly answers "internals of distributed key value stores like FoundationDB."
4. **PostgreSQL internals walkthrough**: use `EXPLAIN ANALYZE` on a moderately complex query, read the planner's chosen path, annotate it. Proof artefact: a written walkthrough (notebook or markdown) explaining each plan node.
5. **Lock-free / concurrent data structure in C++**: e.g., a concurrent queue, benchmarked against a mutex-guarded version. Proof artefact: a small repo with a benchmark table — deepens her existing multithreading skill into systems territory.

## Honest answers for the structural gaps

- *Distributed KV store / storage engine internals*: "I haven't built a production storage engine, but I've studied RocksDB's and FoundationDB's design and built a simplified LSM-tree and Raft store to understand the tradeoffs firsthand — I'd want to pair with someone who's shipped one at scale."
- *MySQL/PostgreSQL internals*: "I've used these databases extensively as an application developer, and I've since studied their query planners and replication internals, but I haven't worked inside their codebases — that's the gap I'd expect to close on the job."

## When this may go on the resume

Only after an item here is actually learned and demonstrated (repo, benchmark, or write-up exists), and only once it's written into data/context/ and re-registered as a skill.
