# Profile notes — positioning, voice and the honesty rules

Companion to `evidence.yml` (the wording authority). Built from `08-voice.md` and the four-track positioning of the earlier workspace.


Derived from the 14 resumes she already writes. Each track has a proven layout; this file makes
the choice automatic instead of manual.

## Track selection

Count JD keyword hits, highest wins. Ties break toward the track with the stronger signature
project for that company.

| Track | Selects on | Lead section | Signature project pool |
|---|---|---|---|
| **A — Data / Analytics Engineering** | data pipeline, ETL, ELT, Airflow, Spark, Databricks, Kafka, Flink, warehouse, lakehouse, SQL, streaming, ingestion | Experience (InsOps first) | P1, P4, P6 |
| **B — ML / AI Engineering** | machine learning, deep learning, PyTorch, computer vision, LLM, RAG, NLP, model training, inference, MLOps, generative AI | Research (AICV first) or Projects | P2, P3, P4, P5 |
| **C — Software Engineering** | software engineer, backend, OOP, C++, C#, .NET, data structures, algorithms, design patterns, API, SDLC, testing | Experience (Soliton first) | P6, P1, P10 |
| **D — Embedded / Test Automation** | embedded, firmware, RTOS, microcontroller, FPGA, Verilog, LabVIEW, TestStand, V&V, hardware, SDET, test automation | Experience (Soliton first) | P7, P8, P9 |

Reference layouts from her own files: A → `_DE`; B → `_A` / `_DS`; C → `_S`; D → `_ES` / `_H`.

## Headline framing per track

Never printed as a summary line (she doesn't use one) — this steers ordering and word choice.

- **A:** Data engineer who has shipped production AWS pipelines at InsOps and built a sub-second
  Kafka/Flink/ClickHouse streaming platform end to end.
- **B:** ML engineer with measured computer-vision research (mAP 91.83%, MOTA 0.93) and shipped
  RAG and classical-ML systems, now doing applied AI on insurance data.
- **C:** Software engineer who owned a customer-facing C#/.NET production application solo for a
  medical-device client, with strong C++/DSA foundations and two years teaching them.
- **D:** Embedded engineer with real FPGA/SoC work (custom MicroBlaze, AXI, Quad-SPI boot) and
  professional medical-device V&V automation in LabVIEW, TestStand and Python.

## Reframing map — same fact, different vocabulary

Reframing changes **emphasis and wording only**. The stack and the outcome never change.

| Fact | As Data | As ML/AI | As Software | As Embedded |
|---|---|---|---|---|
| P1 streaming platform | streaming ETL, event-time windowing, OLAP schema design | real-time anomaly scoring, Z-score detection | distributed systems, concurrency, throughput | medical IoT device telemetry ingestion |
| MiGa dataset work | data pipeline, 4,569-frame dataset construction, validation | keypoint detection, MOT, LSTM sequence modeling | automated processing pipeline, reusable workflows | vision on video device streams |
| Soliton WPF app | — | — | C#/.NET desktop application, OOP architecture, sole owner | hardware-in-the-loop test automation, LabVIEW/TestStand |
| InsOps work | AWS Glue/Lambda/EMR/Airflow pipelines, lakehouse ETL | fine-tuning data prep for a domain SLM, feature engineering | metadata-driven automation, schema discovery | — |
| TA role | taught DBMS to ~180 | — | taught C++ to 100+ | taught C++ to 100+ |

## The competition read, per track

- **A — Data Engineering:** highest volume of US openings and the largest share of H-1B sponsors,
  but heavily contested by bootcamp and offshore-experienced applicants. Her edge is the streaming
  depth (Flink event-time semantics is genuinely uncommon at entry level) plus real AWS production
  work. **Best expected-value track.**
- **B — ML/AI:** most competitive of the four. New-grad ML roles attract PhD applicants. Her
  measured research metrics help, and Q3 (publications) would change this materially — with a real
  ICCV paper she is competitive; without one she is one of thousands.
- **C — Software:** largest absolute market, most forgiving on background. Her C#/.NET production
  ownership is a real differentiator against candidates with only coursework. Weakness: no web or
  full-stack project anywhere in the bank.
- **D — Embedded / Test Automation:** smallest market but by far the **least contested**, and her
  profile is unusually strong for it — professional medical-device V&V plus real FPGA/SoC work.
  Medical-device employers cluster in Boston, Minneapolis, and the Bay Area and sponsor regularly.
  **Best conversion-rate track; under-applied relative to its odds.**

## Recommended mix per 10-job batch

4 Data · 2 ML/AI · 2 Software · 2 Embedded — weighted toward volume where she is strongest, while
keeping the low-competition Embedded lane alive. Adjust once real response data accumulates in
`system/data/applications.tsv`.

## Cap-exempt overlay — applies across all four tracks

Universities, national labs, nonprofit research institutes and academic medical centers file H-1B
**year-round with no lottery**. She already works inside one. Track B and Track D map onto these
employers especially well (research engineer, staff scientist, instrumentation and lab software
roles). Rank cap-exempt employers first regardless of which track the posting belongs to.

---

## Spelling and register
**US English.** Optimize, organization, analyze, modeling, labeled, behavior, center.
Say **resume**, never CV.

## The house style, as observed

Her resumes are consistent and disciplined. The pattern to preserve:

1. **Bullets open with a strong past-tense verb** — Developed, Designed, Implemented, Built,
   Integrated, Applied, Automated, Collaborated, Supported, Performed, Achieved.
2. **Technical specificity over adjectives.** She writes "temporal Flink OVER windows partitioned
   by device ID" rather than "advanced streaming techniques". Keep that. It is the main reason the
   resumes read as credible.
3. **Metrics stated bare, no padding** — "89.48% test accuracy", "0.93 MOTA", "approximately 94%
   of manual test cases". Never "significantly improved".
4. **Bullets run one to two lines.** Never three.
5. **No first-person pronouns.** No "I", no "my".
6. **No summary or objective section.** Not one of the 14 resumes has one. Default to omitting it;
   only add one if a specific JD makes it clearly worth the space.
7. **Stack listed on the project title line**, right-aligned — e.g.
   `Real-Time Medical IoT Analytics Platform    Apache Kafka, Apache Flink, SQL, Python, ClickHouse, Grafana`
8. **Skills grouped under bolded category labels**, categories reordered per JD.
9. **Hedged verbs where the contribution was partial** — "Contributed to", "Supported",
   "Assisted with". She is careful about this; do not upgrade her hedges to ownership claims.

## Banned — workspace defaults
passionate about · results-oriented · proven track record · leveraged · spearheaded · synergies ·
robust · seamless · cutting-edge · dynamic professional · think outside the box · go-getter ·
detail-oriented · team player · hard worker

## Banned — from her own observed style
- "Responsible for", "Worked on", "Helped with", "Involved in", "Tasked with" — she never uses
  these and they weaken every bullet.
- Vague intensifiers: "significantly", "greatly", "substantially", "highly".
- Ownership inflation: do not turn "Contributed to InsOpsAI" into "Built InsOpsAI", or
  "Supported DBMS instruction" into "Taught DBMS".

## Handle carefully

- **The ~94% figure.** Real and specific, but see Q4 — confirm it attaches to Medtronic before
  printing it.
- **"Sole developer".** A strong and unusual claim for someone at her level. It appears on 11 of
  14 resumes, so it is clearly hers to make — but it is exactly the line an interviewer will probe.
  Keep it, and make sure the defense brief covers it.
- **Years of experience.** Never state a total until Q1 resolves.
- **Publications.** Never mention until Q3 resolves.
- **Research vs. personal projects.** MiGa and DualFit are AICV Lab work. Present them as research,
  never as independent side projects.
- **Intern titles.** If the InsOps title is "Intern", it stays "Intern". Do not silently promote it
  to "Engineer".
