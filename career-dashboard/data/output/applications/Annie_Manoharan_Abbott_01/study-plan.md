# Study plan for Abbott - Software Engineer II

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| C, C++, C#, Python | Have | "Experience with C, C++, C# and/or Python is required" |
| Unit/integration & automated testing | Have | "Experience with unit- and integration-level testing and automated testing is recommended" (TDD, Test automation, NI TestStand, LabVIEW registered) |
| Source code management | Have | "source code management is recommended" (Git, Bitbucket) |
| Formal methodologies / Agile | Have | "formal software development methodologies" (Agile/Scrum, Jira) |
| Requirements, V&V, root-cause analysis | Have | "gathering, analyzing, and validating requirements", "root-cause analysis of failures" (V&V registered) |
| Embedded C, FreeRTOS, SPI/I2C/UART | Have | Foundation for "testing embedded software" (ESP32, Arduino, Elevator Control project) |
| Bluetooth Low Energy (protocol + testing) | Learnable | "testing Bluetooth Low Energy within implantable medical devices is desired" |
| IEC 62304 software lifecycle vocabulary | Learnable | Design reviews, requirement/interface specs, "moderate risk" activities signal a 62304 process |
| ISO 14971 risk & hazard analysis | Learnable | "writing, updating, developing and maintaining Hazard/Risk/Cyber Security analysis specifications" |
| Medical device cybersecurity (threat modeling) | Learnable | Same line: cyber security analysis specs |
| MISRA C / static analysis for firmware test | Learnable | Implied by "critical test components" in a cardiac-rhythm context |
| 2+ years testing embedded software | Structural | "Minimum 2 years of experience in testing embedded software" |
| Implantable medical device domain | Structural | "within implantable medical devices" — regulated production experience |
| Never-claim list (Kubernetes, Terraform, dbt, etc.) | Never-claim | Irrelevant to this JD; never asserted anywhere |

## Tier 1 - before the screening call (week 1-2)

1. **BLE fundamentals.** GAP/GATT, services/characteristics, pairing/bonding, connection intervals. Resource: Bluetooth SIG's free "Bluetooth Low Energy Primer" (bluetooth.com). Self-check: explain in 5 minutes how a heart-rate service notifies a phone, and name three things that break BLE links.
2. **IEC 62304 lifecycle vocabulary.** Software safety classes A/B/C, the development/maintenance processes, SOUP. Resource: FDA's free "Content of Premarket Submissions for Device Software Functions" guidance (fda.gov). Self-check: sketch the 62304 V-model from requirements to verification on one page.
3. **ISO 14971 risk vocabulary.** Hazard, foreseeable sequence of events, hazard situation, harm, risk control. Resource: free overview chapter summaries from BSI/IMDRF sites. Self-check: write one hazard analysis row (hazard → sequence → harm → control) for a pacemaker losing BLE connection.
4. **MISRA C awareness.** What it is, why cardiac firmware uses it, common rules. Resource: "MISRA C:2012 guidelines" summary pages and cppcheck docs. Self-check: spot three MISRA violations in a 20-line C snippet you write yourself.
5. **Requirement and interface specification language.** Design inputs, acceptance criteria, traceability, design reviews — the JD's first bullet. Resource: FDA Design Control guidance (free PDF). Self-check: turn a one-line user need into two testable requirements with acceptance criteria.

## Tier 2 - before the technical round (week 2-5)

1. **BLE testing hands-on.** nRF Connect / Wireshark BLE sniffing, notification timing, disconnection edge cases. Artefact: a written walkthrough with captures titled "How I tested a BLE GATT service: 10 cases including radio loss."
2. **C firmware unit testing with Unity + CMock (Ceedling).** Mocking hardware registers, testing state machines. Artefact: a small GitHub repo testing a FreeRTOS task with 15+ unit tests and coverage notes.
3. **Cybersecurity threat modeling for a BLE medical device.** STRIDE over the pairing/data path; AAMI TIR57 concepts. Artefact: a one-page threat model document for her build-now project.
4. **Static analysis in practice.** Run cppcheck with MISRA addon on embedded code, triage findings. Artefact: before/after report committed in the repo showing findings fixed or justified.
5. **Requirements traceability matrix (RTM).** Requirement → design element → test case → result, the JD's "requirement and interface specifications" work. Artefact: an RTM spreadsheet/Markdown for the project, linked in the repo README.

## Build-now project

She has no BLE project; the JD explicitly desires BLE testing. Spec (not built yet):
- Goal: a simulated cardiac telemetry node demonstrating production-grade firmware testing.
- Hardware/data: ESP32 (registered skill); synthetic RR-interval/heart-rate data stream, no real patient data.
- Stack: Embedded C, FreeRTOS, ESP-IDF BLE GATT server; Unity/CMock unit tests; cppcheck static analysis.
- Features: heart-rate service with notifications, connection supervision timeout handling, error-state LED/logging.
- Testing: unit tests for state machine and packet parsing; integration test scripted in Python (Bleak) that connects, streams, drops, reconnects.
- Docs: requirements spec, hazard analysis table (ISO 14971 format), RTM.
- CI: GitHub Actions running unit tests and static analysis on every push — a pipeline she built herself.
- Evaluation: 90%+ unit-test pass, zero unresolved static-analysis defects, integration script passes 10/10 runs.
- Deliverable: public repo with README walkthrough. Estimate: 40-50 hours over weeks 2-5.

## Honest answers for the structural gaps

- **2 years embedded testing:** "My embedded testing has been project-based — the elevator control system and medical IoT platform — rather than two full years in industry, and I'd want to be measured on how quickly my test discipline closes that gap."
- **Implantable devices:** "I haven't worked inside an implantable-device program. I have learned the 62304/14971 framework and built a BLE firmware test project to practice it, and I know the domain rigor is exactly what I'd be joining Abbott to absorb."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before, and nothing from this plan is claimed now.
