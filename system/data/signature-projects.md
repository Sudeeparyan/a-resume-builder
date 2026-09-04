# Signature project registry

Every application carries exactly **one** signature project — first in the Projects section,
chosen for that employer alone. **A signature project is never reused across companies.**
Supporting projects may repeat freely.

Project IDs are defined in `context/04-projects.md`.

## Assigned

| # | Company | Role | Signature project | Date |
|---|---------|------|-------------------|------|
| — | (none yet) | | | |

## Available pool, by track

| ID | Project | Best for | Used? |
|----|---------|----------|-------|
| P1 | Real-Time Medical IoT Analytics Platform | Data, streaming, medtech | free |
| P2 | MiGa — Multi-Chicken Gait Assessment | ML/AI, computer vision | free |
| P3 | DualFit — Two-Stage Virtual Try-On | ML/AI, generative | free |
| P4 | Local LLM-Powered News Research Platform | ML/AI, LLM/RAG | free |
| P5 | Resume Classification Model | ML/AI, classical ML | free |
| P6 | Expense Tracker with Predictive Analytics | Software | free |
| P7 | FPGA-Based Autonomous Vehicle | Embedded, FPGA | free |
| P8 | Elevator Control System | Embedded, firmware | free |
| P9 | Antenna Design (Biosensing + SIW) | RF only | free |
| P10 | Pacman Search Algorithms | Software (coursework) | free |

## When the pool runs out

Ten distinct companies need ten distinct signature projects, and there are ten projects — so a
batch of ten uses the pool exactly once. Beyond that, either:

1. **Reframe** — the same project aimed at a different domain with different vocabulary counts as
   distinct only if the framing genuinely changes what it demonstrates. Record the framing here,
   not just the project ID.
2. **Build one.** If nothing fits what a company expects, say so plainly, ship the strongest real
   project in the slot, and write a **build-now spec** into that company's `study-plan.md`. Once
   she confirms it is built, add it to `context/04-projects.md` and regenerate that resume — their
   process usually runs for weeks, so there is normally still time.

Never put an unbuilt project on a resume, in any tense.

## Coverage gaps (from `context/04-projects.md`)

No project exists for: web/full-stack · Kubernetes/IaC · dbt/Snowflake/modern warehouse · a
CI/CD pipeline she built. When a JD leans on those, expect a build-now spec rather than a match.
