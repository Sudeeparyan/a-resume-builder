# 04 — Projects

Status: FILLED (from `context/files/`, 2026-09-04)

This is the bank the **signature project** is chosen from — exactly one per application, never
repeated across companies. Supporting projects may repeat. Registry:
`system/data/signature-projects.md`.

Nine real, built projects. Every metric below is transcribed from a resume.

---

## P1 — Real-Time Medical IoT Analytics Platform
**Stack:** Apache Kafka, Apache Flink, Flink SQL, Python, ClickHouse, Grafana
**Tracks:** Data/Analytics Engineering (primary), ML/AI, Software
**Appears on:** `_A`(no), `_AN`, `_D`, `_DA`, `_DE`, `_SD`, `_SDA`

- Developed an end-to-end, **sub-second latency** streaming platform using Apache Flink SQL and
  Apache Kafka to ingest, process, and score high-frequency medical IoT device data
- Implemented temporal Flink **OVER windows partitioned by device ID** to dynamically compute
  rolling **Z-scores over 5-second sliding intervals**, applying custom watermark delay strategies
  to cleanly handle out-of-order data streams
- Designed high-performance ClickHouse schemas using the **MergeTree engine sorted by composite
  keys** to physically align disk layouts with clinical querying patterns, isolating ingestion via
  an optimized Python multi-topic batch consumer
- Integrated a Grafana visualization layer on the ClickHouse OLAP tier, delivering real-time
  clinical dashboards monitoring raw **ventilator telemetry** and surfacing streaming Z-score
  anomalies

**Why it is the strongest general-purpose signature project:** real streaming architecture,
event-time semantics, watermarking, OLAP schema design, and a medical domain that pairs with the
Soliton medical-device history.

---

## P2 — MiGa: Multi-Chicken Gait Assessment (AICV Lab)
**Stack:** YOLO11n-Pose, OC-SORT, LSTM, PyTorch
**Tracks:** ML/AI (primary), Data Engineering
**Appears on:** `_A`, `_AN`, `_DA`, `_SA`, `_SDA`
Also listed under Research Assistant in `03-experience.md` — it is lab work, so present it as
research, never as a personal side project.

- YOLO11n-Pose keypoint estimation + OC-SORT multi-object tracking + many-to-one LSTM classifier
- Data engineering framework producing **4,569 frames / 11,422 bounding boxes** and **55
  expert-annotated sequences**
- Spatial normalization into local coordinate spaces to eliminate translational variance
- **keypoint mAP 91.83% @ 1,250 FPS · 0.93 MOTA · 0.91 IDF1**

---

## P3 — DualFit: Two-Stage Virtual Try-On via Warping and Synthesis (AICV Lab)
**Stack:** PyTorch, Res-UNet, flow-based warping, inpainting
**Tracks:** ML/AI (primary)
**Appears on:** `_A`, `_DA`, `_SA`, `_SDA`

- Two-stage VTON model: flow-based garment warping + Res-UNet image synthesis
- Preprocessing and inpainting pipelines to improve garment alignment and visual realism
- **VITON-HD: 24.9 PSNR · 0.913 SSIM · 5.261 FID**

Possible publication — see Q3. If the ICCV claim is real, this becomes the single strongest asset
on the resume and a genuine O-1 argument.

---

## P4 — Local LLM-Powered News Research Platform
**Stack:** Python, LangChain, Streamlit, FAISS, Ollama, nomic-embed-text, Llama 3.2, WebBaseLoader
**Tracks:** ML/AI (primary), Data Engineering
**Appears on:** `_A`, `_DA`, `_DS`, `_SA`

- End-to-end local ETL pipeline using Streamlit and WebBaseLoader to ingest, clean, chunk, and
  preprocess unstructured web content on demand
- Local vector storage architecture using **FAISS + nomic-embed-text** to serialize
  high-dimensional embeddings, bypassing redundant ingestion and reducing processing latency
- **RAG** pipeline via LangChain orchestrating semantic queries against vectorized data using local
  **Llama 3.2** instances

---

## P5 — Resume Classification Model
**Stack:** Python, Scikit-learn, Pandas, TF-IDF, Logistic Regression, Flask
**Tracks:** ML/AI (primary), Software
**Appears on:** `_DS` only

- End-to-end NLP classification pipeline: TF-IDF feature extraction + Logistic Regression across
  **25 job-role categories**
- Preprocessed **962 unstructured resumes** into TF-IDF feature representations
- **89.48% test accuracy, 88% macro F1** across **193 held-out test samples**
- Deployed through a **Flask REST API** for real-time prediction

Best-quantified ML project in the bank. Underused — appears on only one resume.

---

## P6 — Expense Tracker with Predictive Analytics
**Stack:** C++, MySQL, Python, SQL
**Tracks:** Software (primary), Data/Analytics
**Appears on:** `_AN`, `_D`, `_DE`(no), `_ES`, `_S`, `_SA`, `_SD`, `_SDA`

- Cross-language expense management application integrating C++ business logic with a MySQL
  database for storing, retrieving, categorizing, and processing historical expense data
- Optimized SQL queries generating category-based expense summaries and reports
- Python analytics over historical spending patterns generating next-month expense predictions

Most-repeated project. Weakest differentiator — prefer it as a supporting project, rarely a
signature one.

---

## P7 — FPGA-Based Autonomous Vehicle
**Stack:** Xilinx Arty FPGA, MicroBlaze SoC, Vivado, Vitis, AXI IP cores, Quad-SPI, SREC bootloader
**Tracks:** Embedded/Test Automation (primary)
**Appears on:** `_EM`, `_ES`, `_H`

- Autonomous line-following vehicle on a Xilinx Arty FPGA with a custom MicroBlaze-based SoC
- IR line sensors, ultrasonic sensors, and motor drivers integrated through **AXI IP cores** in
  Vivado for real-time sensor acquisition and actuator control
- Embedded firmware in C using Vitis for line tracking, obstacle detection, sensor processing, and
  motor control
- **Quad-SPI flash boot with an SREC bootloader** enabling autonomous startup after power-up
- Debugged hardware-software interfaces across FPGA logic, MicroBlaze, sensors, and motor control

---

## P8 — Elevator Control System
**Stack:** PIC16F887, Embedded C, Proteus, MPLAB IDE
**Tracks:** Embedded (primary)
**Appears on:** `_EM`, `_ES`(no), `_H`

- Multi-floor elevator control system implementing a **finite state machine** for floor selection,
  position detection, movement, and real-time control
- Bidirectional motor control using relay circuits and digital sensor inputs
- LCD and 7-segment displays for real-time floor/status indication; simulated and debugged in
  Proteus and MPLAB IDE

---

## P9 — Antenna Design (two related projects)
**Stack:** Ansys HFSS, SIW, RF/microwave simulation
**Tracks:** Embedded/RF only — rarely relevant to software roles
**Appears on:** `_T`

**Biosensing Antenna Design** — antenna for 5G and biosensing applications; optimized unit-cell
dimensions and geometry; iterative parametric simulation.

**SIW & Deep-Well Cavity Antenna** — Substrate Integrated Waveguide + deep-well cavity structures;
full-wave EM simulation and parametric optimization; supported fabrication and physical
implementation. Linked to the NIT internship in `03-experience.md`.

---

## P10 — Pacman Search Algorithms
**Stack:** Python, BFS, A*, admissible heuristics
**Tracks:** Software (coursework-level)
**Appears on:** `_A`, `_S`

- Custom problem states, successor functions, goal conditions, and state representations for
  maze-based environments
- BFS and A* with admissible heuristics
- Greedy approximation strategy for large state spaces where optimal search was too expensive

**Label this as coursework.** It is a standard CS course assignment (Berkeley Pacman) and
recruiters recognize it. Use only when a JD explicitly emphasizes algorithms/DSA, never as a
signature project.

---

## Coverage gaps worth knowing

| Commonly demanded | Present in the bank? |
|---|---|
| Kafka / Flink / streaming | Yes — P1 |
| Cloud data pipelines (AWS Glue/Airflow) | Yes — but only as InsOps work, not a standalone project |
| RAG / LLM applications | Yes — P4 |
| Classical ML with metrics | Yes — P5 |
| Computer vision | Yes — P2, P3 |
| Embedded / FPGA | Yes — P7, P8 |
| **Web / full-stack app** | **No** — no React/Node/Django project anywhere |
| **Kubernetes / Terraform / IaC** | **No** |
| **dbt / Snowflake / modern warehouse** | **No** |
| **CI/CD pipeline built by her** | **No** — listed as a skill, never evidenced |

When a JD needs something in the "No" rows, do not invent it. Ship the strongest real project and
write a build-now spec into that company's `study-plan.md`.
