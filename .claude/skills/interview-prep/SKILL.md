---
name: interview-prep
description: >-
  Prepare Annie for a specific interview: map her real stories to the job's requirements, predict the
  questions, defend every line of the resume she sent, and rehearse honest answers to gaps. Use for
  "I have an interview at X", "help me prepare for this screening call", "what will they ask me",
  "practice questions for this JD", or when an application moves to interview. Never invents an
  experience to answer a question with.
---

# Interview prep

Follow `career-dashboard/.github/agents/interview-coach.agent.md`. It reads `career-dashboard/data/context/` (and `08-voice.md` for how she talks), `data/interview-prep/story-bank.md`, and the application folder `data/output/applications/Annie_Manoharan_<Company>_<NN>/`: the JD, `company-research.md`, `study-plan.md` (its signature-project defense brief) and the resume actually sent.

Deliver: an interview map (10–15 questions → story → opening line → risk), resume defense per role and project, honest gap answers, technical drilling at entry-level depth, six questions to ask them, and logistics.

Rules: every story traces to `data/context/`; never a years total (walk the roles and dates instead); no publication while `PUB-001` is on hold; the ~94% figure is Dräger's and "approximately". When she has an interview, record it (dashboard status → interview, or `career.py update JOB_ID --status interview`); that also takes the application out of ghosted.
