# Study plan for Anthropic - Full Stack Engineer, Education Labs

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, API design, data pipelines | Have | "Solid back-end and data pipeline experience: Python, API design, analytics infrastructure" — covered by Python, Flask, PostgreSQL, Airflow, Grafana |
| LLMs in production / AI-native UX | Have | "Building AI-native product experiences or working with LLMs in production" — LangChain, RAG, prompt engineering, Ollama |
| CSS | Have | "Strong front-end craft: ... CSS" — registered |
| CI/CD, Git, Docker | Have | Supports "independently driving features from prototype to production" |
| TypeScript/JavaScript | Missing, learnable | "Strong front-end craft: TypeScript/JavaScript" — transferable from Java/C#/Python |
| React | Missing, learnable; Never-claim | Core of their front-end stack; on never-claim list, so learn it, never assert it before re-registration |
| Interaction design, motion, "front-of-the-frontend" | Missing, learnable | "Particular attention to the front-of-the-frontend: motion, polish, and interaction feel" |
| Experimentation frameworks, A/B testing, capability analytics | Missing, learnable | "Analytics that measure capability development in production" |
| HCI / learning sciences fundamentals | Missing, learnable | "Background in learning sciences, cognitive science, HCI ... (formal or self-directed)" — self-directed is allowed |
| 6+ years shipping web products | Missing, structural | "6+ years building and shipping web products, with deep expertise across the stack" |
| Portfolio of interaction designs | Missing, structural (partially buildable) | "A portfolio showcasing innovative interaction designs" — real artefacts in Tier 2 shrink this |
| Strategy, cross-team influence, prioritization | Missing, structural (behavioral) | "Shaping team strategy, building conviction across cross-functional stakeholders" — answer from project leadership she genuinely has |

Education is not a gap: she holds a BE and an MS, satisfying the Bachelor's minimum and the relevant-field requirement.

## Tier 1 - before the screening call (week 1-2)

1. **TypeScript fundamentals.** What: types, interfaces, generics, strict mode, how it differs from Java/C#. Resource: the official TypeScript Handbook (typescriptlang.org/docs/handbook). Self-check: explain structural typing vs. C# nominal typing in 2 minutes, then type a small JSON API response without looking anything up.
2. **React mental model.** What: components, props/state, hooks, rendering. Resource: react.dev "Learn React" (Quick Start + Thinking in React). Self-check: sketch a component tree for a chat interface on paper and explain when state should lift up.
3. **The JD's own vocabulary: capability over engagement.** What: be ready to argue against "time-on-site" metrics. Resource: Anthropic's mission/research page (anthropic.com/research) plus the JD itself. Self-check: give three ways to measure that a user got *more capable*, not more active.
4. **A/B testing basics.** What: hypothesis, randomization, significance, novelty effects. Resource: Evan Miller's "How Not to Run an A/B Test". Self-check: explain why peeking at results early inflates false positives.
5. **HCI crash vocabulary.** What: cognitive load, scaffolding, deliberate practice, transfer. Resource: free chapters of Don Norman's *Design of Everyday Things* summaries via the Interaction Design Foundation's open literature. Self-check: apply "scaffolding" to one feature idea for Claude in education.

## Tier 2 - before the technical round (week 2-5)

1. **React + TypeScript practice app.** Rebuild a small interactive UI (flashcard trainer or prompt playground). Proof artefact: a public GitHub repo with a README explaining component decisions.
2. **Motion and polish.** CSS transitions, spring physics, view transitions. Resource: Josh Comeau's free CSS/animation articles. Proof artefact: a single demo page with three polished micro-interactions, deployed on GitHub Pages.
3. **Claude API in production patterns.** What: streaming, tool use, prompt caching, evals. Resource: Anthropic's official docs (docs.anthropic.com). Proof artefact: a short written walkthrough, "How I'd build a capability-building tutor on the Claude API," in the repo.
4. **Capability-growth analytics.** What: define a metric for skill gain (pre/post task performance, hint-independence over time) and how to A/B test it. Proof artefact: a Jupyter notebook on synthetic user data computing a simple capability-growth metric.
5. **One learning-science deep dive.** What: deliberate practice and desirable difficulties (Bjork). Proof artefact: a one-page written synthesis connecting the research to a concrete feature idea — this doubles as interview material for "strong perspective on how technology should enhance human capabilities."

## Build-now project (only if the JD needs a project type she has none of)

She has no full-stack web product with a real front-end; this JD centers on one. **Not built yet.**
- Goal: AI-native skill-building app — a Socratic coding tutor that adapts difficulty as the user improves.
- Users/data: herself plus 3-5 volunteer users; log attempts, hints used, time-to-solve.
- Stack: React + TypeScript front-end (motion-polished), Python Flask API (existing strength), PostgreSQL, Claude API for tutoring dialogue.
- Feature core: hint tapering — fewer hints as measured competence rises; capability dashboard, not engagement stats.
- Evaluation: pre/post task scores per user; does hint-independence improve week over week?
- Deliverable: deployed demo + repo + 1-page writeup of what the data showed.
- Hours: ~40-50 across weeks 3-6.
- Note: uses React, a never-claim skill — it stays off the resume until learned and re-registered per the rule below.

## Honest answers for the structural gaps

- "I don't have six years of shipping consumer web products — most of my work has been ML and data systems, plus internal tools. What I do have is end-to-end ownership: I've taken models and pipelines from prototype to production alone, and I've spent the last month building production-style React work to close the gap."
- "My interaction-design portfolio is recent and small — I'd rather show you two polished things I built this quarter than pad it. Here's the repo and the demo; the writeup explains my design reasoning."
- "I haven't run capability-growth experiments at scale, but I've designed the metric and tested it on my own project's users — here's the notebook and what I'd do differently with real traffic."

## When this may go on the resume

Only after each skill is learned AND written into data/context/, then re-registered — never before, and React stays unclaimed until that happens.
