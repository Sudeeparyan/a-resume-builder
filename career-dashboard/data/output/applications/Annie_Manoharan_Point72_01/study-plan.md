# Study plan for Point72 - Software Engineer, Macro Quant Analytics Technology

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| C#, .NET backend ("production-quality backend software in C#") | Have | Core language for the macro analytics library |
| Python, C++ ("exposure to C++... performance- or analytics-oriented") | Have | Research tooling and performance-critical paths |
| Kafka, streaming pipelines ("streaming and messaging systems, such as Kafka") | Have | Real-time market data and derived data pipelines |
| Docker, AWS/cloud deployment ("cloud or hybrid environments") | Have | Service packaging and deployment |
| SQL, PostgreSQL, ClickHouse, data modeling generally | Have | Persistence for historical analytics |
| Testing, CI/CD, monitoring ("SDLC best practices... code coverage, monitoring") | Have | Reliability of shared analytics platforms |
| Distributed-systems design ("consistency, time-series or event-driven architectures") | Have (fundamentals via Flink/Kafka/multithreading) | Correctness and latency guarantees |
| gRPC ("APIs (REST/gRPC)") | Never-claim — learn now, never list | Inter-service protocol the team standardizes on |
| Time-aware data modeling ("time-aware (historical and real-time) data models") | Missing, learnable in 3-6 weeks | Consistency across backtest vs. live analytics |
| Financial markets: rates, FX, derivatives ("how pricing and risk analytics are applied") | Missing, learnable in 3-6 weeks (vocabulary) | Partnering with quants and PMs |
| Kubernetes ("familiarity with containerized environments") | Never-claim — learn now, never list | Operating containerized services |
| 3-10 years production backend experience ("3-10 years of experience developing production-quality backend software") | Missing, structural | Seniority and judgment; cannot be compressed into weeks |
| Production finance/trading systems exposure | Missing, structural | Domain trust with investment professionals |

## Tier 1 - before the screening call (week 1-2)

1. **gRPC fundamentals** (JD: "APIs (REST/gRPC)"). Learn: protobuf schemas, unary vs. streaming RPCs, deadlines, gRPC vs. REST trade-offs. Resource: Microsoft Learn "Introduction to gRPC on .NET" (free). Self-check: in 30 min, explain aloud when gRPC beats REST for internal analytics services and sketch a .proto for a price-quote stream.
2. **Time-series / event-driven design vocabulary** (JD: "time-series or event-driven architectures"). Learn: event time vs. processing time, bitemporal tables, watermarks, idempotent consumers. Resource: "Designing Data-Intensive Applications" chapters 1-3 (free via many university libraries) plus Kafka docs on semantics. Self-check: whiteboard in 30 min how you'd keep a backtest dataset and a live feed consistent.
3. **Rates, FX, derivatives basics** (JD: "awareness of financial markets and instruments, including rates, FX, and derivatives"). Learn: what a swap, future, and FX forward are; what "pricing" and "risk" (Greeks, DV01) mean. Resource: Investopedia's free tutorials on swaps, FX forwards, and options Greeks. Self-check: in 30 min, explain DV01 and a vanilla interest-rate swap to a non-finance friend.
4. **Modern C# performance idioms** (JD: "high-performance distributed systems... latency"). Learn: Span<T>, Memory<T>, ArrayPool, async/await pitfalls, GC modes. Resource: Microsoft's free "Performance best practices with C#" talk/blog series on .NET. Self-check: explain in 30 min how you'd reduce allocations in a hot pricing loop.
5. **Kubernetes concepts only** (JD asks "familiarity" — learn, never claim). Learn: pods, deployments, services, configmaps, probes. Resource: kubernetes.io free "Kubernetes Basics" tutorial. Self-check: describe in 30 min what happens when a pod dies mid-request.

## Tier 2 - before the technical round (week 2-5)

1. **gRPC service in C#** — build a small market-data server exposing unary and server-streaming RPCs. Artefact: GitHub repo with .proto files, a .NET server, and a README walkthrough of a latency benchmark vs. a REST equivalent.
2. **Time-aware data model** — design a bitemporal schema for tick data in ClickHouse or PostgreSQL (both already hers). Artefact: repo with DDL, sample ingest script, and a written note on as-of queries and why they matter for backtesting.
3. **Derived-data Kafka pipeline in C#** (JD: "derived data generation and persistence"). Artefact: repo where a C# consumer computes rolling VWAP from a raw-trade topic into a derived topic, with idempotent writes and a Grafana dashboard (Grafana is registered).
4. **Local Kubernetes deployment, labeled as learning** — deploy item 1's service to kind/minikube with probes and resource limits. Artefact: manifests plus a written walkthrough of a rolling update. Present it only as "I taught myself this," never as experience.
5. **Mini pricing/risk notebook in Python** (JD: "pricing, risk, and global market data workflows"). Artefact: Jupyter notebook pricing a bond and an FX forward, computing DV01 and simple Greeks, with plain-English commentary she could narrate to a PM.

## Build-now project (only if the JD needs a project type she has none of)

**Not built yet.** Goal: a C# "macro rates analytics service" mimicking this team's world — none of her projects are finance or time-aware analytics services. Data: free daily treasury yield-curve and FX rates (FRED/ECB CSVs). Stack: .NET 8, gRPC + REST endpoints, PostgreSQL bitemporal store, Kafka for derived curves, Docker. Scope: ingest historical series, serve as-of queries, compute derived forward curves. Evaluation: correctness checks against published curve math; p99 latency measured and documented. Deliverable: public repo with README architecture diagram and a one-page design note on consistency choices. Hours: ~40 across weeks 3-6.

## Honest answers for the structural gaps

- On "3-10 years production backend": "My production experience is earlier in its arc than the top of your range, but I've built and operated streaming data systems end-to-end in school and research settings, and I've spent the last month going deep on exactly the stack in this job description. I'd rather show you that work than inflate a number."
- On finance: "I haven't worked in markets before. I learned the basics of rates, FX, and derivatives because this role needs them, and I built a small pricing notebook to make sure I actually understood the math — what I'd need from the team is the domain depth that only comes from sitting next to your quants."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
