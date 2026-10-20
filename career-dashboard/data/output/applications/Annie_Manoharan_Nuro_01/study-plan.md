# Study plan for Nuro - New Grad Software Engineer, Routing

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| React | Never-claim (learn ok, never assert) | "design, build, and ship full-stack applications using React, TypeScript" |
| TypeScript | Learnable | same JD line |
| C++ | Have (registered) | "software modules written in C++ that operate onboard the vehicle" |
| Graph/search fundamentals | Have (Pacman Search Algorithms project) | "routing algorithms... graph data structures" |
| Routing at scale (contraction hierarchies, time-dependent routing) | Learnable | "optimizing routing algorithms and understanding road network graphs" |
| Map data (OSM-style road graphs) | Learnable | "receive live map updates" |
| ETA/monitoring analytics | Learnable (Grafana, Pandas registered) | "monitoring and analytics infrastructure that supports routing performance and ETA accuracy" |
| Traffic simulation | Learnable | "simulation tools that shape the company's strategy for robot deployment" |
| Microservices design | Learnable (Flask, Docker, design patterns registered) | "designing microservices" |
| REST APIs, PostgreSQL, AWS, CI/CD, streaming | Have (Flask, PostgreSQL, AWS, CI/CD, Kafka, MQTT) | "RESTful or gRPC APIs", "relational databases", "cloud infrastructure", "Pub/Sub, streaming pipelines" |
| gRPC / Protocol Buffers | Never-claim (learn ok) | Bonus: "Experience with Protocol Buffers and gRPC" |
| Kubernetes | Never-claim (learn ok) | Bonus: "Exposure to Kubernetes" |
| Production onboard-vehicle software | Structural | "operate onboard the vehicle... interface with motion planning" |
| Bachelor's in CS-related field | Have (education; never a gap) | Minimum Qualifications |

## Tier 1 - before the screening call (week 1-2)

1. **TypeScript fundamentals** — JD: "React, TypeScript, and modern web development practices". Learn: type annotations, interfaces, generics, tsconfig strict mode. Resource: the official TypeScript Handbook (typescriptlang.org/docs). Self-check: convert a 100-line JS file to strict TS with zero `any` in 30 minutes.
2. **Routing algorithm vocabulary** — JD: "optimizing routing algorithms". She has A*/Dijkstra from Pacman; add contraction hierarchies and time-dependent routing. Resource: OSRM's public docs/wiki on routing at scale. Self-check: explain in one paragraph, unaided, why plain Dijkstra is too slow at country scale and how CH fixes it.
3. **Map data basics** — JD: "road network graphs", "live map updates". Learn OSM nodes/ways/tags and how a routable graph is built. Resource: OpenStreetMap Beginners' Guide (wiki.openstreetmap.org). Self-check: download a city extract and count routable ways by highway tag.
4. **gRPC/Protobuf concepts (learn-only)** — JD bonus: "Protocol Buffers and gRPC". Learn service definitions, message types, unary vs streaming RPCs. Resource: grpc.io "What is gRPC?" Self-check: write a `.proto` for a RouteService with a streaming ETA method from memory.
5. **React mental model (learn-only)** — JD: "frontend architecture decisions, component libraries". Learn components, props, hooks, state lifting. Resource: react.dev "Learn React". Self-check: build a small counter-plus-list app unaided and explain useEffect dependencies out loud.

## Tier 2 - before the technical round (week 2-5)

1. **Mini routing engine.** Python or C++ over an OSM extract: build the road graph, implement Dijkstra and A* with haversine heuristic, benchmark runtime vs graph size. Artefact: public GitHub repo with README containing benchmark tables.
2. **ETA accuracy study.** Simulate predicted vs realized travel times on 100 origin-destination pairs; compute MAE/MAPE by time-of-day; discuss why ETA accuracy matters (JD: "more accurate ETAs"). Artefact: Jupyter notebook with charts and a written error analysis.
3. **Fleet traffic simulation.** Build a SUMO scenario with 10-50 delivery vehicles; measure fleet throughput and ETA drift under congestion. Artefact: repo with scenario configs plus a one-page written walkthrough of findings.
4. **gRPC demo service (learn-only).** Small Python RouteService defined in protobuf with server-streaming ETA updates and a demo client. Artefact: small repo; stays off the resume.
5. **Microservices decomposition doc.** Take her existing Medical IoT platform and write a design doc splitting it into microservices with API contracts, failure modes, and tradeoffs (JD: "instinct for making the right tradeoffs"). Artefact: written design doc she can walk an interviewer through.

## Build-now project — not built yet

**Fleet routing ops dashboard (full-stack).** Goal: a small end-to-end app echoing Routing-team work — request routes, view ETAs, watch simulated vehicles. Data: one OSM city extract plus simulated vehicle telemetry (reuse her Kafka/MQTT streaming experience). Stack: TypeScript + React frontend (learning exercise), Flask API (Have), PostgreSQL (Have), Docker Compose (Have). Features: map view of computed routes, ETA table, live simulated positions via server-sent events. Evaluation: 100 random OD pairs routed correctly; ETA error stats displayed; API p95 under 300 ms. Deliverable: public repo, README with screenshots, 3-minute demo video. Effort: roughly 40-50 hours across weeks 3-6. Note: React output here is learning evidence only and remains never-claim.

## Honest answers for the structural gaps

- "I haven't shipped software that runs on a real vehicle. What I do have is embedded C and C++ on FPGAs and microcontrollers, including an FPGA-based autonomous vehicle project, so I'm comfortable with resource-constrained, deterministic code — and I'm eager to learn your onboard stack."
- "My systems experience is coursework and personal projects, not production scale. I bring TDD habits and end-to-end ownership, and I plan to close the production gap fast through code review and mentorship."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — and never-claim skills (React, gRPC, Kubernetes) never go on the resume at all.
