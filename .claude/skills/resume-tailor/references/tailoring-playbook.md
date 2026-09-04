# Tailoring playbook

How to pick the base, frame the content, and keep it ATS-clean. Generic by design: the person-
specific tables live in `system/profile/positioning.md` and `system/profile/skills-matrix.md`.

## 1. Track selection

1. Tokenise the JD (title, responsibilities, requirements).
2. Count matches against each archetype's `signals` in `system/config/profile.yml`.
3. Highest count wins. Within 20% of each other → hybrid.
4. Tie → the track with the lower competition level in `system/profile/positioning.md`.
5. State the decision in one line: *"Track B (Operations) — 6 signal hits vs 2; using
   resume-track-b.tex."*

Hybrid recipe: Track A base, one Track B project, and two Track B bullets in the most recent role.
Never merge two full resumes — the result reads as unfocused to both audiences.

## 2. Section order

**Experienced (2+ years):** Header → Summary → Experience → Projects → Skills → Education →
Publications → Certifications.

**Graduate / career changer:** Header → Summary → Education (with relevant modules) → Projects →
Experience (internships, part-time, volunteer) → Skills → Certifications.

The difference matters: putting a thin Experience section first on a graduate CV invites the
reviewer to conclude "no experience" before seeing the projects.

## 3. Summary (2–3 lines, rewritten every time)

Formula: `<role identity from the JD> with <honest experience statement> in <the JD's core
technologies>. <Strongest relevant proof>. <What they are looking for, matching this role>.`

- Experienced: lead with years and the strongest quantified outcome.
- Graduate: lead with the degree and specialisation, then the strongest project, then the domain
  interest. Never write "seeking a challenging role in a reputed organisation".
- Never claim years the profile does not have. "Graduate with academic and project experience in X"
  is stronger than a vague claim that collapses in the first screening call.

## 4. Experience bullets

`action verb → what → tool/method → outcome`

- 3–5 bullets for the most recent role, 2–3 for older ones.
- Lead each role with its most JD-relevant bullet, not its chronologically first task.
- Keep real numbers. With no number, use scope: "across 4 product teams", "for a 12-table
  warehouse", "on a 30-device fleet".
- Label role type honestly: Intern, Contract, Part-time, Research Assistant.
- Mirror the JD's verbs where truthful. If the JD says "triage", write "triaged".

## 5. Dynamic selection from the knowledge base (the core move)

`system/profile/master-profile.md` is a **superset** — it holds far more modules, projects, and skills than
fit on a resume. Tailoring is a *selection* problem: score everything against this JD, keep the
best, drop the rest for this application only. Nothing is deleted from the knowledge base; it just
doesn't appear on *this* resume.

**Selection algorithm (run for projects, modules, and skill categories):**

1. Build a **JD requirement set**: the must-haves, nice-to-haves, and domain keywords from Step 1.
2. Score every item in the knowledge base by overlap between its `Tags:` / `Synonyms:` and the JD
   requirement set. A project that shares 4 tags with the JD beats one that shares 1.
3. Break ties by: recency, presence of a real outcome number, and confidence level (`core` > `working`
   > `exposure`).
4. **Fill the page budget by rank** (see §7): take the top-scoring items until the target length is
   reached, then stop. A one-page graduate CV might show the top 3 projects and 5 modules; a
   two-page CV shows more.
5. Everything not selected stays in the knowledge base for the next, different JD.

**Projects — reframe the selected ones to the company (the highest-leverage edit):**

1. The new title must describe what the project genuinely does.
2. The stack and outcome stay exactly as recorded in `system/profile/master-profile.md`.
3. Two projects on a two-page resume; three on a one-page graduate CV where they carry the weight
   instead of employment.
4. If nothing scores above a weak match, use the strongest projects unreframed and say so in the
   match assessment.

Example of an honest reframe: an IoT waste-bin project with ultrasonic sensors and a microcontroller
becomes "Sensor-Driven Monitoring System" for an industrial-monitoring employer — same sensors, same
board, same code, framed in their words. It does **not** become "Industrial Fleet Telemetry
Platform" — that describes work that did not happen.

**Modules — promote what the JD names.** If the JD asks for "distributed systems" and the knowledge
base lists that module, surface it on the Education line for this application. If the JD names a
topic and no module matches, that is a gap — handle it in §8, never invent a module.

## 5b. Letting the research drive the emphasis

The JD tells you what the recruiter typed. The research (`system/modes/deep.md`) tells you what the company
actually runs and where it is going. When they disagree, the research usually wins — but only ever in
these five ways, all of which move *real* facts around:

| Move | Example |
|------|---------|
| **Promote** a real skill the research shows is central, even if the JD mentions it once | Their eng blog is all Kubernetes; the JD says "containers" once → Kubernetes leads the Skills section |
| **Re-word** a real skill into the company's own vocabulary | They say "observability"; the profile says "monitoring" → write observability, since the work is the same |
| **Re-order** sections and bullets so their priority is in the first third | A platform-migration team gets the migration project first |
| **Re-frame** a project toward their domain (title and framing only — never the facts) | See §5 |
| **Answer** a pressure the research surfaced, using real evidence | They just had a data-quality incident; the profile has a validation pipeline → lead with it |

And one move that is **forbidden**: adding a skill because the research shows they want it. That is
exactly the case the upskilling plan exists for. If the demand map (`system/modes/deep.md` §6) put a skill in
the *Upskilling* or *Honest gap* column, it does not appear on this resume in any form.

The test to apply: *"could the candidate answer three follow-up questions about this line in an
interview?"* If not, it does not belong on the page — it belongs in
`output/NN_Company_Role/study-plan.md`.

## 5c. The signature project — one per company, never repeated

Every resume carries **exactly one signature project**: the project chosen and positioned for *this
company alone*, sitting first in the Projects section, written in their vocabulary, aimed at the work
the research says this hire will actually do. The other one or two projects on the page are
supporting cast and may repeat across applications. The signature project may not.

This is the single highest-leverage difference between ten near-identical resumes and ten resumes
that each look built for one employer.

### Choosing it

1. Score the whole Projects & Build Bank against **the demand map** (`system/modes/deep.md` §6), not just
   the JD's keyword list — the company's real stack and roadmap carry as much weight as the JD text.
2. Exclude anything already used as a signature project for another live application (check
   `system/data/signature-projects.md`).
3. The top scorer becomes the signature project. Reframe it per §5: **the title and framing change,
   the facts never do.**
4. Place it first under Projects, give it one more bullet than the supporting projects, and make sure
   the JD's top two must-haves appear inside those bullets — truthfully.

### When nothing in the bank fits (the build-now case)

Sometimes the company expects a kind of project the candidate has genuinely never built. Do **not**
put a project on the resume that does not exist. Instead:

1. Say so plainly, in one line: *"Nothing in your bank matches what they'll expect — here's the
   fastest honest fix."*
2. Design a **build-now project** in the upskilling plan (`system/modes/upskill.md`): scoped to days rather
   than months, using the company's actual stack, aimed at their actual problem, and specified
   tightly enough to start today — goal, stack, milestones, and the resume bullets it will earn once
   it exists.
3. Ship this resume with the best available real project as signature, and say clearly that it is a
   weaker slot.
4. The moment the candidate says they have built it, append it to `system/profile/master-profile.md` with
   tags and **regenerate this company's resume** with it in the signature slot. Applications stay
   open for weeks — a rebuilt resume can often still go in, and it is ready for every similar company
   afterwards.

Never present a planned project as a built one. Never write it in the future tense on the resume, in
a "Currently building" line, or anywhere else on the page. It lives in the upskilling plan until it
is real.

### Keeping the registry

Maintain `system/data/signature-projects.md` — one row per application:

```
| NN | Company | Role | Signature project | Origin | Reframed as | Date |
```

`Origin` is `existing` (from the bank), `reframed` (bank project, new angle), or `to-build` (does not
exist yet — resume shipped without it). The registry is what guarantees ten companies get ten
different signature projects, and what stops the same project being sold two different ways to two
teams who talk to each other.

### The defence brief

Every signature project gets a **project defence brief** written into that company's upskilling plan
(`system/modes/upskill.md` → "Project defence brief"). It exists because the signature project is the thing
the interview will dig into hardest, and the candidate may have built it a year ago. The brief is
what they revise the night before.

## 5d. Then audit it

The draft is not finished. Run the three passes in `references/recruiter-audit.md` — recruiter
critique, XYZ rewrite of every bullet, then the ATS-plus-hiring-manager scan — and save the audited
version. The pre-audit draft never becomes the deliverable.

## 6. Technical skills

- 4–6 categories, ordered per the archetype block in `system/profile/skills-matrix.md`.
- Within each category, the JD's requested tools first.
- Drop categories the JD does not touch — a wall of every skill ever seen reads as noise and dilutes
  keyword density.
- Never list a skill at `exposure` level next to `core` skills without qualification. Put
  coursework-level knowledge in an "Academic exposure" line or leave it out.

## 7. Page fit

| Profile | Target |
|---------|--------|
| 2+ years experience | 2 pages, ~95% of page 2 filled |
| Graduate / < 1 year | 1 page, completely filled |
| Academic CV (research roles) | No limit, publications first |

Too long → trim the oldest role's bullets, then the least relevant project bullet, then the least
relevant publication. Too short → add technical depth to existing bullets, add a project, add
relevant coursework. Never pad with soft-skill filler.

## 8. Gaps — and the "did you forget to add it?" loop

For every JD must-have, decide which of three buckets it falls in:

**(a) Found in the knowledge base** → use it, reframed in the JD's wording.

**(b) NOT FOUND anywhere in the knowledge base** → this is the critical case the candidate asked
for. They have studied a lot; some of it may simply be missing from `system/profile/`. So do **not** just
call it a gap — first hand it back to them:

> ⚠️ **NOT IN YOUR PROFILE — did you forget to add it?**
> This JD requires **{{requirement}}**. I searched your full knowledge base (modules, projects,
> training, skills) and could not find it. If you *have* done this — a module, a class project, a
> tool you used once — add it to `context/` (or directly to
> `system/profile/master-profile.md`) and re-run, and I'll put it on the resume. If you genuinely haven't,
> it's a real gap (below).

List every such item under a **"Check your memory"** heading, separately from true gaps. Never
silently invent the skill to fill the hole.

**Log it so it isn't lost.** Append each bucket-(b) item to `context/QUESTIONS-FOR-YOU.md` under its **Open**
heading — `- [ ] <requirement> — came up for <Company> (<role>), <YYYY-MM-DD>` — skipping any
requirement already listed there. Over several applications this becomes the candidate's backfill
punch-list; adding one entry to `system/profile/` can lift several future matches at once.

**(c) Genuinely not held** (candidate confirms they haven't done it) →
1. Say whether it is a hard blocker or a nice-to-have.
2. Name the closest honest adjacent experience and how far the analogy stretches.
3. Suggest one real, specific, quickly-obtainable certification or course that would close it.
4. **Put it in the upskilling plan** (`system/modes/upskill.md` → `output/NN_Company_Role/study-plan.md`),
   tiered by whether it is needed for the screening call, the technical round, or the first 90 days.
   Shortlisting takes 3–6 weeks; most of these are closable in that window, and a gap with a study
   plan against it is a far better interview answer than a gap with a shrug. It still does not go on
   *this* resume — it goes on the next one, after it is learned and added to `system/profile/`.

Never paper over a gap by adding the skill to the resume. The match assessment is where gaps get
named — that is what makes the score meaningful.

## 9. Multi-version hygiene

- One `.tex` per application, numbered. Never edit yesterday's file for today's application.
- Keep the JD next to it in `output/` — six weeks later you will not remember which version was sent.
- Record the resume version in the tracker row.
