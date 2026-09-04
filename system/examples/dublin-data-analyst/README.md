# Example — Dublin Data Analyst (fictional)

**"Aoife Byrne" is not a real person.** This folder is a worked reference showing:

1. **A known-good Overleaf resume** — [`resume.tex`](resume.tex) is fully filled (no `{{TOKENS}}`)
   and built on the same macros as `system/templates/latex/resume-track-b.tex`. Paste it into overleaf.com
   (compiler: pdfLaTeX) and Recompile to see the exact layout and one-page fit before you tailor
   your own.
2. **How a NON-software profile fills the template** — the friends using this workspace span
   software, data, and medtech. This example shows the **data** shape: how the two tracks are named,
   which modules/projects get surfaced, and Irish CV conventions (no photo, no DOB, right-to-work
   line, LinkedIn).

See [`profile-snippet.yml`](profile-snippet.yml) for how `system/config/profile.yml`'s tracks and
archetypes would look for this person — copy the *shape*, never the content.

## Track-naming examples across domains

The template ships with two generic tracks you rename per person. Some patterns:

| Person | Track A (primary lane) | Track B (adjacent lane) |
|--------|------------------------|-------------------------|
| Data analyst (this example) | Data Analytics / BI | Data Engineering / Analytics Engineering |
| Software / AI grad | AI / ML Engineering | Backend / Platform Engineering |
| Medtech software | Medical Device Software / V&V | Embedded / Firmware / Test Automation |

Each track has its own LaTeX base and framing; the tailor classifies each JD into A, B, or hybrid.
