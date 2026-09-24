---
name: profile-intake
description: >-
  Record new facts about Annie into the workspace so every future resume can use them. Use when she
  says "I built X", "I finished the AWS course", "I got a certification", "I left InsOps", answers a
  question in QUESTIONS-FOR-YOU.md (publication details, the 94% figure, city, salary), pastes an
  updated CV, or asks to "update my profile". Extractive only: every recorded line traces to her own
  words, and nothing reaches a resume until it is in the evidence registry.
---

# Profile intake

Her facts live in `career-dashboard/data/context/`: her own numbered files (`01-basics.md` … `09-anything-else.md`, `files/`) and the evidence registry `evidence.yml` that every resume line must cite. `data/config/profile.yml` holds identity, tracks and policy.

## Absolute rule

**Extractive, not generative.** Every line you write traces to something Annie said or supplied. Missing details go into `QUESTIONS-FOR-YOU.md` as questions, never into a file as a plausible guess. Never promote a skill level she did not claim; never turn coursework into work experience; never assign a years total.

## When she tells you something new

1. Write it into the right numbered file in her words, and **tell her exactly which file** (the one exception to "never write to context/").
   - A finished build or course → `04-projects.md` or `06-achievements.md`; a skill she now really has → `05-skills.md` at the level she states.
   - An answer to an open question → the relevant file, and mark the question answered in `QUESTIONS-FOR-YOU.md` with the date.
2. Register it in `evidence.yml`: a new or updated claim/project with `status`, `approved_external_use`, `source_refs` (file and section) and, for a project, `resume_content` (title, context, 2–3 bullets in her wording). A study-plan proof artifact she has actually finished becomes a normal project here.
3. Bump `candidate_revision` in **both** `evidence.yml` and `profile.yml` (e.g. `2026-09-18.1` → `2026-10-02.1`).
4. Check: `career check` (the workspace validator; `career` is `.\career.cmd` on Windows and `./career` elsewhere) and the test suite.
5. Tell her what changed and that open drafts need **Sync profile & rank projects** in Resume Studio to pick it up.

## Open questions that change what resumes may say

- **Q3 publications** — `PUB-001` stays `hold` until she gives title, venue, year, author position and a link. Then it becomes a claim and a Publications section can be discussed with her.
- **Q4 the ~94% figure** — attributed to Dräger (confirmed 2026-09-18); keep "approximately" until she says whether it was measured.
- **Q2 InsOps** — whether she is still there and in what capacity (the dates say "Present").
- **Q5 city, Q6 salary, Q10 work-authorization line, Q11 LinkedIn** — each changes the header, the search or the forms.

Edits made in the dashboard's Profile tab are captured as `user_updated` knowledge and pause new drafts until reconciled into the registry the same way.
