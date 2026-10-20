# Study plan for OpenAI - Software Engineer, Quality & Developer Tools | Consumer Devices

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, C, C++ | Have | "proficient in Python, C, C++, or Rust" |
| Linux, Git, Docker, CI/CD | Have | "strong Linux fundamentals", "building CI/CD pipelines" |
| Test automation, TDD, NI TestStand | Have | "deep experience building software quality, test automation" |
| Embedded C, ESP32, SPI/I2C/UART, MQTT | Have | "hardware-software integration", "automated flashing, provisioning" |
| Grafana, Streamlit | Have (adjacent) | "dashboards and alerts for pass rates" |
| Buildkite | Missing, learnable | "Integrate test suites with Buildkite, enforce promotion criteria" |
| Hardware-in-the-loop lab design | Missing, learnable (conceptually) | "designing and operating hardware-in-the-loop labs and device orchestration" |
| Flake detection & quarantine | Missing, learnable | "detect and quarantine flaky tests; drive root-cause analysis" |
| systemd/udev depth | Missing, learnable | "strong Linux fundamentals, including... udev/systemd" |
| Release gates, staged rollout/rollback | Missing, learnable | "promotion criteria for staging and production", "staged rollouts, and rollback/forward strategies" |
| Rust | Never-claim | Listed as alternative language; on her never-claim list — learn basics, never assert proficiency |
| HIL labs "at scale", hardware shipped at scale | Structural | "demonstrated success... at scale" — years of production lab operation |

## Tier 1 - before the screening call (week 1-2)

1. **Buildkite pipeline model** — JD: "Integrate test suites with Buildkite." Learn agents, pipelines-as-YAML, steps, artifacts, test analytics. Resource: Buildkite official docs (buildkite.com/docs) Quickstart + Test Analytics guides. Self-check (30 min): sketch a 3-stage pipeline (unit -> integration -> HIL gate) on paper with promotion conditions, and explain each step aloud.
2. **udev/systemd fundamentals** — JD: "processes, networking, storage, and udev/systemd." Learn unit files, targets, journald, and how udev rules map a plugged-in device to a /dev node. Resource: freedesktop.org systemd man pages (systemd.unit, udev(7)). Self-check: write a udev rule that names a USB serial device consistently and a systemd service that starts a logger on boot; explain both without notes.
3. **Flaky-test vocabulary** — JD: "flake detection and quarantine, signal-quality guardrails." Learn: quarantine tags, rerun budgets, flake rate dashboards, bisection. Resource: Google's Testing Blog, "Flaky Tests at Google and How We Mitigate Them." Self-check: define flake rate, quarantine SLA, and three root-cause classes from memory.
4. **Release gating concepts** — JD: "enforce promotion criteria", "staged rollouts, and rollback/forward." Learn canary/staged rollout, rollback vs roll-forward, artifact traceability. Resource: Martin Fowler, "ContinuousDelivery" and "CanaryRelease" articles. Self-check: argue rollback vs roll-forward for a firmware regression in 5 sentences.
5. **HIL lab anatomy** — JD: "racks, power and networking systems, and orchestration for device testing." Learn: PDUs, network switches, device under test (DUT), flashing/provisioning loops, telemetry capture. Resource: "Hardware-in-the-Loop Testing" overview articles + NI HIL documentation. Self-check: draw a rack diagram and walk the flash-test-telemetry cycle.

## Tier 2 - before the technical round (week 2-5)

1. **Buildkite pipeline repo** — Build a real pipeline for one existing project (e.g., the Medical IoT platform): unit tests, artifact upload, a promotion gate using Buildkite's block step. Artefact: public repo with `pipeline.yml`, screenshots of a green run and a blocked promotion.
2. **Flake-quarantine harness** — Write a pytest plugin/script that reruns failures N times, tags flaky tests, emits a flake-rate report, and auto-excludes quarantined tests. Artefact: repo + sample HTML/markdown flake report run against deliberately flaky tests she seeds.
3. **Device-flashing orchestrator prototype** — Script (Python + pyserial/adb-style) that provisions and flashes an ESP32 over UART, runs a smoke test, and captures logs/telemetry with timestamps. Artefact: repo with README walkthrough and a captured log showing flash -> test -> report.
4. **Quality-signals dashboard** — Grafana (registered skill) dashboard fed by a tiny pipeline-results database: pass rate, flake rate, mean time to triage, release-readiness flag. Artefact: dashboard JSON + screenshot set + one-page note on which metrics gate a release.
5. **systemd/udev hands-on lab** — A systemd-managed test-runner service with automatic device attach via udev rule, journald logging, and restart policy. Artefact: short written walkthrough (markdown) with the unit file, udev rule, and journalctl output.

## Build-now project (only if the JD needs a project type she has none of)

Her projects include embedded/IoT work but no CI/CD pipeline or device-orchestration project she built end-to-end; the JD demands both ("CI/CD integration & releases", "device orchestration"). **Not built yet.**

- Goal: mini hardware-in-the-loop orchestrator + release gate for one ESP32.
- Data: synthetic firmware builds; test results stored in SQLite/PostgreSQL.
- Stack: Python, ESP32 (registered), Buildkite free tier or self-hosted agent, Grafana.
- Flow: commit -> Buildkite builds firmware -> flashes ESP32 via orchestrator -> runs UART smoke tests -> results to DB -> flake detector -> Grafana dashboard -> promotion gate blocks on failures.
- Evaluation: repro run 20x; flake rate reported; one seeded bug auto-caught.
- Deliverable: public repo, README walkthrough, screenshots of gated release.
- Hours: ~35-45 across weeks 2-5 (this is the Tier 2 items 1-4 wired together).

## Honest answers for the structural gaps

- HIL labs at scale: "I've built and flashed embedded devices hands-on and I understand lab anatomy — racks, provisioning, telemetry. I haven't operated a multi-rack lab at production scale, and I'd ramp on your existing lab quickly because the orchestration concepts are ones I've been practicing."
- Shipped hardware at scale: "My embedded work has been project and prototype scale, not a mass-shipped product line. What transfers directly is test automation, flashing/provisioning, and debugging across software and firmware — the rest I'm prepared to learn fast."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
