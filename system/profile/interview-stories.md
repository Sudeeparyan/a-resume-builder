# Interview stories — STAR bank

Built only from facts in `context/`. Nothing invented. Where a detail is unknown, it says so —
fill it in from memory before the interview rather than guessing on the day.

---

## S1 — Sole ownership of a production medical-device project
**Use for:** ownership · autonomy · dealing with ambiguity · "tell me about your biggest project"

- **Situation.** At Soliton Technologies, a medical-device client (Medtronic — confirm Q4) needed
  their manual test suite automated under medical-device quality and validation requirements.
- **Task.** She was the **sole developer** on it.
- **Action.** Built a C# WPF desktop application integrating C#, Python and LabVIEW test workflows;
  implemented reusable object-oriented components; integrated automated testing and validation
  workflows for repeatable verification.
- **Result.** Roughly **94% of manual test cases automated**, meeting medical-device quality and
  validation requirements.

**This is her strongest story and the one interviewers will dig hardest into.** Expect: how did you
scope it alone? how did you validate correctness in a regulated environment? what did you do when
you were blocked with nobody to ask? what was the 6% you couldn't automate, and why?
⚠️ The 6% answer is not in `context/` — she needs to prepare it.

---

## S2 — Sub-second streaming with correctness under out-of-order data
**Use for:** technical depth · system design · "hardest technical problem"

- **Situation.** High-frequency medical IoT telemetry (ventilator data) needed real-time anomaly
  scoring.
- **Task.** Ingest, process and score it end to end at sub-second latency.
- **Action.** Apache Flink SQL + Kafka; temporal **OVER windows partitioned by device ID**
  computing rolling **Z-scores over 5-second sliding intervals**; **custom watermark delay
  strategies** for out-of-order streams; ClickHouse **MergeTree schemas sorted by composite keys**
  aligning disk layout to clinical query patterns; an isolated Python multi-topic batch consumer;
  Grafana on the OLAP tier.
- **Result.** Sub-second latency with anomalies surfaced live on clinical dashboards.

Expect: why watermarks and not processing time? what's your late-data policy? why ClickHouse over
Postgres? what breaks at 10x volume? Event-time vs. processing-time is the question that separates
people who used Flink from people who understand it — she should be able to answer it cold.

---

## S3 — Research with measured results
**Use for:** ML depth · rigor · handling failure

- **Situation.** AICV Lab needed automated gait assessment for multiple chickens from video.
- **Task.** Detect, track and score gait across many birds in frame.
- **Action.** YOLO11n-Pose keypoints + OC-SORT tracking + many-to-one LSTM classifier; built the
  dataset pipeline (4,569 frames, 11,422 boxes, 55 expert-annotated sequences); spatial
  normalization into local coordinate spaces to remove translational variance.
- **Result.** **mAP 91.83% at 1,250 FPS, MOTA 0.93, IDF1 0.91.**

Expect: why OC-SORT over ByteTrack/DeepSORT? what caused ID switches? how did you validate against
expert annotation? what did spatial normalization actually fix?

---

## S4 — Teaching at scale
**Use for:** communication · mentoring · "explain something complex simply"

100+ students in Programming Foundations (C++), ~180 in Database Management Systems, across
Sep 2024 – May 2026. Lab instruction, debugging help, assessments.

⚠️ No specific student anecdote is in `context/`. She needs one concrete example ready — a student
who was stuck on something specific and how she unblocked them.

---

## S5 — Cross-language systems integration
**Use for:** "worked across boundaries" · pragmatism

C# + Python + LabVIEW in one application at Soliton. C++ + MySQL + Python in the Expense Tracker.
Kafka + Flink + ClickHouse + Grafana in P1. The recurring theme: she gets heterogeneous systems
talking to each other.

---

## S6 — Hardware/software co-design
**Use for:** embedded and medical-device interviews

FPGA autonomous vehicle: custom MicroBlaze SoC on Xilinx Arty, sensors and motor drivers through
AXI IP cores, firmware in Vitis, Quad-SPI flash boot with an SREC bootloader, debugging across the
FPGA/processor/peripheral boundary.

Expect: why a soft-core processor instead of an MCU? what did the bootloader have to handle? how
did you debug across the hardware/software line?

---

## Gaps in the story bank — prepare these before any onsite

No story currently exists in `context/` for:

- **Conflict with a teammate or manager.** Asked in nearly every behavioral loop.
- **A failure, and what changed afterward.** Asked nearly as often.
- **Receiving hard critical feedback.**
- **Missing a deadline or descoping under pressure.**
- **Disagreeing with a technical decision and being overruled.**

These are real experiences she has — they just aren't written down. They need capturing into
`context/09-anything-else.md` before an onsite, not improvised in the room.

## Questions she should ask them

- What does the first 90 days look like for this role?
- What is the on-call and incident load actually like?
- Who owns data quality when a pipeline silently produces wrong numbers?
- How does the team decide what to build next?
- **Sponsorship, asked cleanly and late:** "I'm authorized to work in the US on F-1 OPT and I'm
  STEM-eligible, so I can start immediately without sponsorship. Could you tell me how the company
  handles longer-term sponsorship?" — factual, leads with what she can do now, and only then asks.
