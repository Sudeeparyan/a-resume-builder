# 09 — Anything else

Status: FILLED — observations from the 14 resumes that no other file captures.

## The 14 variants and what each was aimed at

Decoded from content. The suffix is the target role.

| File | Target | Leads with | Signature project |
|---|---|---|---|
| `_A` | AI / ML Engineer | Projects, then RA | Local LLM News Research |
| `_AN` | Business / Data Analyst | RA (analyst framing) | Real-Time Medical IoT |
| `_D` | Data Engineer (no InsOps) | TA | Real-Time Medical IoT |
| `_DA` | Data + AI hybrid | Projects | Real-Time Medical IoT |
| `_DE` | Data Engineer (with InsOps) | InsOps | Real-Time Medical IoT |
| `_DS` | Data Scientist | InsOps (InsOpsAI framing) | Resume Classification |
| `_EM` | Embedded Engineer | TA | FPGA Autonomous Vehicle |
| `_ES` | Embedded Software | Soliton | FPGA Autonomous Vehicle |
| `_H` | Hardware / Medical Device | Soliton (Dräger detail) | FPGA Autonomous Vehicle |
| `_S` | Software Engineer | TA | Expense Tracker |
| `_SA` | Software + AI | RA | Expense Tracker |
| `_SD` | Software Developer | Projects | Real-Time Medical IoT |
| `_SDA` | Software + Data + AI | RA | Real-Time Medical IoT |
| `_T` | Telecom / RF | Projects (antennas) | Biosensing Antenna |

**What this proves:** she already understands tailoring. She is manually maintaining fourteen
parallel documents and hand-editing them per application. That is the time sink this workspace
exists to remove — not a lack of skill, a lack of automation.

**What it also creates:** fourteen files that have drifted apart. The Soliton dates disagree
between them (Q1), the InsOps title disagrees (Q2), and there is no single authoritative version.
`system/profile/master-profile.md` becomes that single version.

## Header inconsistency
`_DE` renders the portfolio and GitHub as the words "Portfolio" and "GitHub" (hyperlinked). The
other 13 print full URLs. `_S` is the only one appending a title to the name
("Annie Prasanna Manoharan - Software Engineer").

Full URLs are safer for ATS text extraction — hyperlink text can be lost when a parser flattens
the PDF. Default to full URLs.

## Section ordering varies deliberately
Some lead Projects before Experience (`_A`, `_DA`, `_SD`, `_T`), others lead Experience
(`_DE`, `_DS`, `_S`). The choice tracks whichever is stronger for that target. Preserve this as a
per-track setting rather than fixing one order.

## What is conspicuously missing across all 14
- No LinkedIn URL
- No city or location line
- No summary or objective
- No publications, certifications, or awards
- No GPA
- No work-authorization statement

The last one is worth a decision. US postings frequently screen on work authorization, and a
one-line statement — "Authorized to work in the US on F-1 OPT; STEM OPT eligible through
[date]" — can pre-empt a rejection. It also volunteers immigration status before a human has
read the resume. Currently omitted on all 14. See Q10.

## Non-obvious strengths to exploit

1. **The medical-device thread runs through everything** — Soliton (Medtronic, Dräger), the
   ventilator telemetry platform, medical IoT. That is a genuine domain specialization and a real
   differentiator for medtech employers, who cluster in Boston, Minneapolis, and the Bay Area and
   sponsor regularly.
2. **Hardware-to-LLM range is unusual.** FPGA and firmware at one end, RAG pipelines and fine-tuned
   language models at the other, production data pipelines in between. Most candidates have one
   band of that spectrum.
3. **She is already inside a cap-exempt employer.** University TA and RA appointments. Cap-exempt
   employers file H-1B year-round with no lottery, and she knows how that world works.
4. **Teaching scale is quantified** — 100+ and ~180 students. Useful evidence of communication
   ability for roles that ask for it.
