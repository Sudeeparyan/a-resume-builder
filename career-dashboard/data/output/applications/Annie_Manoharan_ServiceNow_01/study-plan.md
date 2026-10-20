# Study plan for ServiceNow - Software Engineer, Core Infrastructure - Moveworks (New Grad)

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| "programming fundamentals in at least one backend language such as Java... Python, C++" | Have (Java, Python, C++ all registered) | Daily implementation language |
| "data structures, algorithms, and object-oriented design" | Have (Design patterns, Pacman Search coursework) | New-grad interview core |
| "building RESTful APIs/services, request/response handling, error handling" | Have (Flask, Expense Tracker project) | Service development |
| "event streaming" / "Kafka... is a plus" | Have (Apache Kafka, Medical IoT Analytics) | Their event backbone |
| "containers, and cloud platforms" | Have (Docker, EC2/S3/Lambda, Linux) | Deploy/runtime substrate |
| "concurrency... scalability, caching, messaging" | Partially have (Multithreading, Kafka); distributed-systems depth missing | Core infra design |
| "rate limiting and circuit breaking", "feature flags and A/B testing", "distributed configuration management and hot reloading", "traffic capture and replay" | Missing, learnable 3-6 weeks | The actual services this team builds |
| "distributed logging, tracing, monitoring, and alerting" | Partially have (Grafana); OpenTelemetry/tracing missing | Observability mandate |
| "distributed key value store, schema-less data store" | Partially have (MongoDB); internals (consensus, partitioning) missing | Storage-layer ownership |
| "operating... open source technologies like Kafka, Elasticsearch or Opensearch, Istio" | Kafka Have; Elasticsearch/Opensearch Never-claim; Istio learnable conceptually (needs k8s, which is never-claim) | Ops maturity signal |
| "Go" | Never-claim (she has Java/Python/C++; JD says "such as") | Team language |
| "Redis" (implied by KV store/rate limiting) | Never-claim — learn, never claim | Common implementation choice |
| Operating production infra at scale ("designing and operating reliable and resilient foundational services") | Structural — years of production/on-call experience | What separates new grads from infra veterans |

## Tier 1 - before the screening call (week 1-2)

1. **Distributed-systems vocabulary.** Consistency, partitioning, replication, consensus (Raft at concept level), CAP. Resource: the free System Design Primer (github.com/donnemartin/system-design-primer). Self-check: in 30 min, whiteboard from memory how you'd scale a key-value store and what breaks first.
2. **Rate limiting & circuit breaking** (JD lists both verbatim). Token bucket vs. sliding window; breaker states. Resource: free sections of the "Rate Limiting" and "Circuit Breaker" chapters on patterns.ambig.com / Microsoft Azure architecture center docs. Self-check: explain a breaker state diagram and where it sits relative to retries.
3. **Feature flags & A/B testing mechanics** (JD: "system for feature flags and A/B testing"). Targeting, gradual rollout, kill switches. Resource: OpenFeature docs (openfeature.dev). Self-check: describe a flag-based canary rollout and its rollback path in 5 sentences.
4. **Config management & hot reload** (JD verbatim). Push vs. pull, versioning, consistency. Resource: free etcd and Consul intro docs. Self-check: sketch two designs for hot-reloading config to 1,000 services.
5. **Microservice metrics** (JD: "methodologies and metrics to measure performance"). RED/USE methods, p50/p99, SLI/SLO. Resource: Google SRE book, free online (sre.google/sre-book), Monitoring chapter. Self-check: define an SLO for a login API and pick its SLIs.

## Tier 2 - before the technical round (week 2-5)

1. **Distributed tracing with OpenTelemetry** (JD: "distributed logging, tracing"). Instrument a two-service Flask app, propagate trace context, export to Jaeger via Docker. Artefact: small repo with docker-compose, instrumented services, screenshots of a trace waterfall.
2. **Traffic capture & replay** (JD verbatim). Study goreplay/mitmproxy; build a replay harness that records requests to one Flask service and replays against a shadow instance. Artefact: repo with replay script + a short README on fidelity pitfalls (side effects, non-idempotency).
3. **KV-store internals.** LSM vs. B-tree, WAL, partitioning. Resource: free CMU 15-445 lectures (YouTube). Artefact: written walkthrough (~800 words) of how a write flows through an LSM store.
4. **Kafka depth beyond her project.** Consumer groups, rebalancing, exactly-once, lag monitoring. Resource: free Kafka docs design section. Artefact: notebook/gist demonstrating consumer-lag alerting logic against her Medical IoT pipeline.
5. **Interview algorithm reps.** Distributed-infra-flavored problems (LRU cache, rate limiter, design a URL shortener). Resource: NeetCode free list. Artefact: 25 solved problems with notes in a repo.

## Build-now project (only if the JD needs a project type she has none of)

She has no project that is *infra services themselves* — her projects consume infrastructure rather than build it, and this JD builds it. Spec (label: **not built yet**):
- **Goal:** a mini "platform services" repo: feature-flag service + rate limiter + traffic replay harness.
- **Data:** synthetic HTTP request logs generated by a load script.
- **Stack:** Python/Flask, Docker Compose, Kafka (Have), OpenTelemetry; no Kubernetes, Redis, Go (never-claim).
- **Evaluation:** p99 latency under 2x load with limiter on vs. off; flag rollout rollback demo.
- **Deliverable:** public repo with README architecture diagram and load-test numbers.
- **Hours:** ~25 across weeks 3-5.

## Honest answers for the structural gaps

- On production scale: "I haven't operated infrastructure at Moveworks' scale yet — my Kafka and AWS work is project-scale. What I can show is that I've studied the failure modes and built small versions of the services this team runs."
- On Go/Elasticsearch: "My daily languages are Java, Python and C++, and my search experience is limited; I pick up new stacks quickly and I'm already working through the concepts."

## When this may go on the resume

Only after each item is learned AND written into data/context/, then re-registered — never before.
