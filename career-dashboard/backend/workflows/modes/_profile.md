# Candidate Framing — Annie Prasanna Manoharan

Read `AGENTS.md` and `data/config/profile.yml` first. This file defines how to adapt Annie's real evidence without changing her identity. It wins over `_shared.md` on conflict.

## Target tracks

| Track | Target roles | Evidence to lead with |
|------|--------------|-----------------------|
| **A Data / Analytics Engineering** | Data Engineer, Analytics Engineer, Data Platform Engineer, ETL Developer | InsOps AWS pipelines (Glue, Lambda, EMR, Airflow, S3); the Kafka/Flink SQL/ClickHouse streaming platform |
| **B ML / AI Engineering** | ML Engineer, AI Engineer, Computer Vision Engineer, Applied Scientist, Research Engineer | AICV Lab research (MiGa, DualFit) with measured results; RAG news platform; resume classifier |
| **C Software Engineering** | Software Engineer, SDE, Backend/Application Engineer | Soliton C# WPF application for Dräger; C++ teaching; streaming platform; expense tracker |
| **D Embedded / Test Automation** | Embedded/Firmware Engineer, Test Automation, V&V, SDET, FPGA | Soliton LabVIEW/TestStand V&V and test automation; FPGA vehicle; elevator controller |

Her range is a real multi-step pivot: electronics → embedded → test automation → computer-vision research → data engineering. Each resume picks **one coherent thread** for that employer instead of narrating the whole journey.

## Adaptive framing

| If the role is... | Lead with... | Use as proof |
|-------------------|--------------|--------------|
| Data Engineer / Analytics Engineer | Pipelines, orchestration, data quality, SQL | `EXP-INSOPS-001`, `PROJ-P01-IOT` |
| Streaming / real-time data | Event-time processing, watermarks, sub-second analytics | `PROJ-P01-IOT` |
| ML / Computer Vision Engineer | Model training, evaluation metrics, dataset construction | `PROJ-P02-MIGA`, `PROJ-P03-DUALFIT`, `EXP-RA-001` |
| AI / LLM application roles | Retrieval, vector search, local LLM pipelines | `PROJ-P04-NEWS-RAG` |
| Classical ML / NLP | Text classification, evaluation, REST serving | `PROJ-P05-RESUME` |
| Software Engineer | Shipped desktop software, OOP, C#/.NET, C++ | `EXP-SOLITON-PE-001`, `EXP-TA-001` |
| Medical device / health tech | Regulated test automation, device telemetry | `EXP-SOLITON-PE-001` + `METRIC-DRAEGER-94`, `PROJ-P01-IOT` |
| Embedded / Firmware / FPGA | Hardware-software integration, state machines | `PROJ-P07-FPGA`, `PROJ-P08-ELEVATOR`, Soliton V&V |
| Research Engineer (university, hospital, lab; usually tier S) | Lab research and teaching inside a cap-exempt employer | `EXP-RA-001`, `EXP-TA-001`, `PROJ-P02-MIGA` |

## Signature-project routing

Every resume has exactly two project blocks: the **signature** project (first, unique to this company) and one **supporting** project. Rank the registry's resume-ready projects against the verified JD and company problem; this table is a starting preference, not an automatic choice:

| Strongest target signal | Signature candidate |
|---|---|
| Streaming, real-time analytics, OLAP, medical devices | `PROJ-P01-IOT` |
| Pose estimation, tracking, sequence models, dataset construction | `PROJ-P02-MIGA` |
| Generative models, image synthesis | `PROJ-P03-DUALFIT` |
| RAG, LLM applications, vector search | `PROJ-P04-NEWS-RAG` |
| NLP, text classification, model evaluation | `PROJ-P05-RESUME` |
| Application development with SQL and forecasting | `PROJ-P06-EXPENSE` (prefer as supporting) |
| FPGA, SoC, sensors and actuators | `PROJ-P07-FPGA` |
| Microcontrollers, finite state machines | `PROJ-P08-ELEVATOR` |
| RF and antenna design | `PROJ-P09-ANTENNA` (RF roles only) |
| Algorithms and search | `PROJ-P10-PACMAN` — **supporting only**, labeled coursework, never a signature |

`data/signature-projects.md` shows which company already owns which signature. When nothing unused fits, say so, ship the strongest real project, and write a **build-now spec** into `study-plan.md`. Never rename a project so it looks like work for the target company.

## Core narrative

> Data and AI engineer with production AWS pipeline work, a sub-second streaming platform, measured computer-vision research, and shipped medical-device test automation.

## Identity boundary

- Entry level. Never position her as Senior, Staff, Lead or Principal, and never state a total years of experience.
- Never position her as a published researcher until `PUB-001` leaves hold (Q3: she says she has one or more publications; details pending).
- Not a full-stack/web developer, and not a DevOps/platform/infrastructure engineer.
- InsOps is an internship: **Data Engineering Intern**, Jul 2024 – Present. The old "Data Science Intern / InsOpsAI / litigation mitigation" framing is superseded and held.
- MiGa and DualFit are **AICV Lab research** with measured results, never personal side projects.
- InsOps, the TA post and the RA post overlap (2024–2026): never present them as sequential or add their durations.

## Claim boundary

- Soliton: Engineering Intern Jul 2022 – May 2023, then Project Engineer Jun 2023 – Jun 2024 (Q1, confirmed 2026-09-18). A one-page resume may drop the intern role for space.
- "Approximately 94% of manual test cases" belongs to **Dräger** (Q4, confirmed 2026-09-18); keep "approximately" until she says whether it was measured.
- No Docker, CI/CD or Kubernetes work claims; Kubernetes and Terraform are not in the bank at all. No production Spark/Databricks bullets.
- No GPA, certifications or LinkedIn: none are on record.
- Work authorization stays off the resume unless a form asks; then "Authorized to work in the US (F-1 OPT)". Never "no sponsorship required".
- No city on the resume (Q5 open).

## Tone

Professional and plain: complete sentences that say why something mattered. Keep her recurring language where it is true: "ownership", "real-world impact", "problem-solving", "adaptability". US English spelling. Full rules in `data/context/08-voice.md`.

## Location

United States only: all hubs in `profile.yml location_preferences` plus Remote (US). Do not down-rank on city until Q5 is answered. Never search outside the US.

## Negotiation

Salary expectations are open (Q6 in `data/context/QUESTIONS-FOR-YOU.md`). Never state a number or a range for her; ask.
