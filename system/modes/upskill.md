# Mode: upskill — what to learn for THIS company, between applying and interviewing

Runs automatically after every tailored resume (`resume-tailor` Step 8). Output goes to
`output/NN_Company_Role/study-plan.md`.

## Why this mode exists

Shortlisting takes weeks. From "applied" to "first interview" is typically **3–6 weeks** in the US
market, and often longer for larger employers. That waiting time is the single most usable asset the
candidate has: if they know *exactly* what this company will probe, they can close real gaps before
anyone asks about them.

So the job splits in two:

| Goal | Owned by | Rule |
|------|----------|------|
| **Get shortlisted** | the resume | Only facts already in `system/profile/master-profile.md`. Nothing aspirational. |
| **Win the interview** | this plan | Everything the company will expect that the candidate does not yet have. |

**The wall between them is absolute.** A skill in the upskilling plan is a skill the candidate does
*not* have yet. It does not appear on the resume, in the summary, or in the skills section — not as
"familiar with", not as "exposure to", not in any softened form. It goes on the resume only after
they have actually learned it *and* it has been added to `system/profile/master-profile.md`. Say this to
the user every time, in one line, so the boundary is never blurry.

## Inputs

1. The JD — must-haves, nice-to-haves, and the tools named in passing.
2. `output/NN_Company_Role/research.md` — the research: real stack, roadmap, what the team is building next
   (`system/modes/deep.md` §2, §4, §4b, §8).
3. `system/profile/skills-matrix.md` — what the candidate already holds and at what level
   (`core` / `working` / `exposure`).
4. `context/QUESTIONS-FOR-YOU.md` — requirements that have already come up for other companies. A skill that
   appears here three times is worth learning before one that appears once.

## The demand map (build this first)

For every skill the JD or the research names, place it in one of four buckets:

| Bucket | Meaning | Goes where |
|--------|---------|------------|
| **Have — core/working** | Real, evidenced in the profile | On the resume, front and centre |
| **Have — exposure** | Touched once, coursework level | On the resume only as familiarity; **Tier 2** here to make it interview-safe |
| **Missing but learnable** | Not held; realistically learnable in the shortlisting window | **This plan** |
| **Missing and structural** | Years of production experience, a security clearance, a specific degree | Not learnable in weeks — name it as a real gap in the Match Assessment and say how to answer it honestly |

Do not pad the plan. Eight to twelve items is a plan; thirty is a wish list nobody starts.

## Tiers

### Tier 1 — Before the screening call (week 1–2)
The things a recruiter or hiring manager will ask about in the first 30 minutes, sourced straight
from the JD's must-haves. Vocabulary and fundamentals: enough to discuss each item confidently and
say honestly where the candidate is on it. Cap: **5 items.**

### Tier 2 — Before the technical round (week 2–5)
Depth on what the company actually runs (from the research, not just the JD) — their real stack,
their domain, their scale. Includes hardening any `exposure`-level skill the JD leans on. Cap:
**5 items.** Each Tier 2 item should end in a **proof artefact** (below).

### Tier 3 — First 90 days on the job (post-offer)
What the role grows into, from the company's roadmap. Not needed to get hired; it is what makes the
final-round "where do you want to grow" answer specific and credible. Cap: **4 items.**

## Row format

Every item is a table row:

| Field | Rule |
|-------|------|
| Skill | The JD's or the company's own name for it, not a generic category |
| Why this company | One line tied to a *specific* JD line or research finding. If you can't name one, cut the row |
| Priority | 🔴 blocker · 🟠 likely probed · 🟡 nice to have |
| Current level | From `system/profile/skills-matrix.md`: none / exposure / working |
| Target level | What "enough for this interview" means, concretely |
| Est. time | Realistic hours, spread over the shortlisting window |
| Resource | **One** canonical free-or-cheap resource, named exactly (official docs, a specific course). Never "search online". Cite a URL when the web was reachable; mark unverified links as unverified |
| Proof artefact | The small thing they build to make it real — and the resume line it becomes once done |

## Proof artefacts — how learning gets back onto the resume

A skill learned from a video is not claimable. A skill used to build something is. Each Tier 1 and
Tier 2 item names one small, finishable artefact — a script, a dashboard, a deployed container, a
notebook, a test suite — sized to a weekend, not a semester.

When the candidate finishes one, the loop closes:

1. They tell the assistant "I built the X thing."
2. The assistant appends it to `system/profile/master-profile.md` (Projects & Build Bank, with `Tags:`).
3. It is now a claimable fact, so **every future resume** — including a re-run for this same
   company — can use it.
4. If it closed an item in `context/QUESTIONS-FOR-YOU.md`, tick that item off there too.

Offer this explicitly at the end of the plan: *"When you finish any of these, tell me and I'll add
it to your profile so it starts appearing on your resumes."*

## The signature project — brief and build spec

Every resume carries exactly one **signature project**, chosen for this company alone
(`.claude/skills/resume-tailor/references/tailoring-playbook.md` §5c). It is the thing the interview will dig into hardest, so
every plan carries one of the following two sections.

### A. Project defence brief — when the signature project already exists

The candidate may have built it a year ago. This is what they revise the night before the call:

| Section | What goes in it |
|---------|-----------------|
| What it does, in 30 seconds | The spoken answer to "walk me through this project" |
| Why it matters to **this** company | Ties the project to the JD line or research finding that made it the signature pick |
| Architecture | Components and how data moves between them. A short diagram in text is fine |
| Stack, and why each piece | Every tool named on the resume line, with the reason it was chosen over the obvious alternative |
| The three decisions | The real trade-offs made, and what the alternative would have cost |
| What broke, and the fix | Interviewers probe failure harder than success. The honest version is the strong one |
| Numbers | Every real metric, from `system/profile/master-profile.md`. Anything still `[FILL IN]` gets asked here |
| Scale honesty | What it did **not** do — 10k rows not 10M, one node not a cluster. Say it before they find it |
| Where it would break at their scale | Shows engineering judgement rather than defensiveness |
| 8–10 likely questions | Ranked by likelihood, each with the honest answer and which revision item covers it |

If a fact needed for the brief is not in `system/profile/master-profile.md`, ask the candidate — never write
a plausible architecture they did not build. Their own project is the one thing they cannot bluff.

### B. Build-now spec — when nothing in the bank fits this company

If no real project matches what this company expects, the resume ships with the best available one
and this section specifies the project that *would* have been perfect:

| Section | What goes in it |
|---------|-----------------|
| Goal | The one sentence, in the company's own problem language |
| Why it fits them | The JD lines and research findings it answers |
| Stack | Their actual stack, from the research — not a generic one |
| Scope | Explicitly what is **in** and what is **out**. Small enough to finish |
| Milestones | 3–5 checkpoints, each a day or two, each independently demoable |
| Est. total | Honest hours. If it needs three weeks, say three weeks |
| Learning attached | Which Tier 1/2 rows above this project teaches in passing |
| Resume lines it earns | The exact bullets that become claimable **once it is built** — written now so the payoff is visible, marked clearly as not-yet-true |

Then say plainly: *"This isn't on your resume and won't be until you've built it. If you build it,
tell me — I'll add it to your profile and rebuild this company's resume with it in the signature
slot. Their process runs weeks, so there's usually still time."*

## Interview-shaped extras (always include)

- **Likely probe questions** — 5 questions this company is likely to ask, drawn from the JD and the
  research, each mapped to the Tier item that prepares for it.
- **The honest answer to the biggest gap** — a scripted two-sentence answer to the one gap that
  cannot be closed in time: name it, state what is genuinely adjacent, state what is being done
  about it now. Never a bluff; the plan itself is the evidence of the last part.
- **Their interview process** — if the research found it (stages, formats, take-home, panel), list
  it, and mark it inferred if inferred.

## Re-runs and updates

- Re-running the same company overwrites the same file — one plan per application, kept current.
- When a batch (`system/modes/batch.md`) covers many companies, also refresh
  the **"What to study this week"** table in `output/SUMMARY.md`: skills ranked by how many open
  applications need them. That
  file answers the real question — *"of everything, what do I study first this week?"*
- **Always update `system/data/signature-projects.md`** with this application's row, so no two
  companies receive the same signature project.
- When the candidate reports finishing a build-now project, add it to `system/profile/master-profile.md`,
  flip its registry row from `to-build` to `existing`, regenerate that company's resume with it in
  the signature slot, and replace section B of this plan with a section A defence brief.
- Never delete a plan after a rejection. The next company in that sector wants the same things.

## Honesty gates

- Nothing in this plan may migrate to a resume, cover letter, or LinkedIn profile before it is
  learned **and** written into `system/profile/master-profile.md`.
- Never state or imply a certification is held because it is listed here as a target.
- Time estimates are honest ones. If something genuinely takes six months, say six months and put it
  in Tier 3 rather than pretending it fits the window.
- If web research was unavailable, build the plan from the JD alone and label it clearly:
  *"JD-only plan — company research was not available, so the stack items are inferred."*
