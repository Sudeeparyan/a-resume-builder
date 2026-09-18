# Mode: Upskill — What to Learn for This Company, Between Applying and Interviewing

Runs after every tailored resume. Output: `study-plan.md` in the application folder. In the app, Resume Studio → **Write study plan** (or `backend/scripts/workspace.py run --kind study_plan --job-id JOB_ID`) runs the study-planner agent (`backend/workflows/agents/study-planner.md`) on the gaps the match check found.

## Why this exists

From "applied" to "first interview" is typically three to six weeks in the US market. If Annie knows exactly what this company will probe, she can close real gaps before anyone asks.

| Goal | Owned by | Rule |
|------|----------|------|
| **Get shortlisted** (Fight 1) | the resume | Only facts already in `data/context/` and the registry. Nothing aspirational. |
| **Win the interview** (Fight 2) | this plan | Everything the company will expect that she does not have yet. |

**The wall is absolute.** A skill in this plan is a skill she does not have. It never appears on the resume, in the skills section or anywhere else, not as "familiar with", not as "exposure to", in no softened form, until it is learned **and** written into `data/context/` and re-registered. Say this in one line every time you hand over a plan.

## Inputs

1. The saved JD: must-haves, nice-to-haves, tools named in passing.
2. `company-research.md`: real stack, roadmap, what the team builds next.
3. The registry's skills and projects (titles only) and the never-claim list (`SKILL-NEVER-001`).
4. The match check's `missing_unsupported` list.
5. `data/output/SUMMARY.md` → "What to study this week": a gap that recurs across open applications ranks higher.

## Demand map first

| Bucket | Meaning | Goes where |
|--------|---------|------------|
| **Have** | Registered skill or project | Resume, front and center |
| **Have, skills-list only** | `SKILL-TOUCHED-001` items (Docker, CI/CD …) | Resume skills list only; Tier 2 here to make it interview-safe |
| **Missing, learnable** | Not held; learnable in the shortlisting window | This plan |
| **Missing, structural** | Years of production experience, a clearance, a specific degree | Named in the match assessment with an honest answer |

Eight to twelve items is a plan; thirty is a wish list nobody starts.

## Tiers

- **Tier 1 — before the screening call (weeks 1–2).** At most 5 items, straight from the JD's must-haves: vocabulary and fundamentals, one specific free resource each, a 30-minute self-check.
- **Tier 2 — before the technical round (weeks 2–5).** At most 5 items: depth on what this company actually runs. Each ends in a **proof artifact** (a small repo, notebook, dashboard or test suite sized to a weekend).
- **Tier 3 — first 90 days (post-offer).** At most 4 items from the roadmap; it makes the "where do you want to grow" answer specific.

Every row: the company's own name for the skill, why this company (a specific JD line or research finding, or cut the row), priority, current level, target level, honest hours, one named resource, the proof artifact and the resume line it becomes **once done**.

## How learning gets back onto the resume

1. Annie says "I built the X thing" or "I finished the AWS course".
2. You record it in the right `data/context/` file (and say which), then add it to `evidence.yml` with a revision bump.
3. From then on every resume can use it, including a rebuild for this company.
4. Tick off any matching item in `QUESTIONS-FOR-YOU.md`.

Offer this at the end of every plan: "When you finish any of these, tell me and I'll add it to your profile so it starts appearing on your resumes."

## Signature project: defense brief or build-now spec

Every plan carries one of these.

**A. Defense brief** (the signature project exists): the 30-second walkthrough; why it matters to this company; architecture; the stack and why each piece; three real decisions and their trade-offs; what broke and the fix; every real metric from the registry; scale honesty (what it did not do); where it would break at their scale; 8–10 likely questions with honest answers. If a fact is not in `data/context/`, ask her; never write an architecture she did not build.

**B. Build-now spec** (nothing in the bank fits): goal in the company's problem language, why it fits, their actual stack, scope in/out, 3–5 demoable milestones, honest total hours, the Tier 1/2 rows it teaches, and the resume lines it would earn, clearly marked **not yet true**. Then say: "This isn't on your resume and won't be until you've built it. If you build it, tell me and I'll rebuild this company's resume with it in the signature slot."

## Always include

- Five likely probe questions, each mapped to the tier item that prepares for it.
- A two-sentence honest answer to the biggest gap that cannot close in time.
- Their interview process if research found it (marked inferred if inferred).

## Rules

- Re-running for the same company overwrites the same file; never delete a plan after a rejection.
- A certification listed as a target is never implied as held.
- Honest time estimates; six months goes in Tier 3.
- If web research was unavailable: "JD-only plan — company research was not available, so the stack items are inferred."
