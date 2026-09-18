---
name: profile-intake
description: >-
  Turn one person's raw, unstructured profile dump into the structured knowledge base this
  workspace runs on. Use when setting up a new candidate, when the user pastes a CV, LinkedIn
  export, transcript, or long brain dump of coursework/projects/skills, when system/profile/ still
  contains {{PLACEHOLDER}} tokens, or when asked to "build the knowledge base", "onboard a new
  person", "set up my profile", or "update the master profile" after new experience. Writes
  system/profile/master-profile.md, positioning.md, skills-matrix.md, interview-stories.md and fills
  system/config/profile.yml. Extractive only — it never invents a fact.
---

# Profile Intake

Convert the user's **`context/` folder** (any format, any length, however messy) into the five
structured files the rest of the workspace reads. Run this before anything else in a fresh
workspace, and again whenever `context/` changes.

`context/` is the source of truth and stays exactly as the user wrote it. `system/profile/*` is your
tidied, structured copy of it — a cache, built for fast selection at tailoring time. You **read**
`context/`; you do not rewrite it.

## Absolute rule

**Extractive, not generative.** Every line you write must trace to a line in `context/` or to an
answer the user gave you in this session. When something is missing, it goes in the gaps report —
never into the file as a plausible guess. A resume built on an invented fact is worse than no
resume.

## Capture everything (build the superset, don't pre-trim)

`system/profile/master-profile.md` is a **complete knowledge base**, not a resume. Your job is to get
*all* of it in, because the `resume-tailor` selects the JD-relevant slice later — it can only select
what you captured. A student's raw dump has far more than fits on two pages; that is correct and
expected. Specifically:

- **Every module / course**, not a curated few. A JD that names "distributed systems" can only
  promote that module if you listed it.
- **Every project** — coursework, personal, training, hackathon — as its own block in the Projects
  & Build Bank. There is no cap. Ten project blocks is normal and good.
- For **every project and skill, write a `Tags:`/`Synonyms:` line** (domains, tools, problem-types,
  and the exact phrasings a JD might use). Tags are what the tailor matches against. `RAG` should
  also carry `retrieval-augmented generation`; `k8s` should also carry `Kubernetes`.
- When in doubt, **include it in the knowledge base and tag its confidence low** — never drop it.

### Where each `context/` file lands

| Read from | Write into |
|-----------|-----------|
| `context/01-basics.md` | `system/config/profile.yml → candidate:` + the master profile's header |
| `context/02-education.md` | Education, with **every** module copied across, and coursework projects |
| `context/03-experience.md` | Work Experience, type labels preserved exactly as stated |
| `context/04-projects.md` | The Projects & Build Bank — one block per project, `Keywords:` → `Tags:` |
| `context/05-skills.md` | The skills inventory: Strong → `core`, Used it → `working`, Touched it → `exposure`. **Never promote a level the user did not claim.** |
| `context/06-achievements.md` | Certifications, awards, hackathons, publications, languages |
| `context/07-preferences.md` | Constraints, compensation, location in `profile.yml`; hard limits and no-go companies into `system/modes/_profile.md` |
| `context/08-voice.md` | Voice notes in `positioning.md`; banned words into `system/modes/_profile.md` |
| `context/09-anything-else.md` | Everything else — mine it hard, it usually holds facts nothing else captured |
| `context/files/` | Read every document. Transcripts are the fastest source of a full module list |

Specifically, never:
- convert coursework into work experience, or a university project into a job
- invent a metric, a percentage, a team size, a date, or a contract value
- add a tool to the skills list because it usually accompanies one that was mentioned
- assign years of professional experience that the raw input does not state
- upgrade "familiar with" into "experienced in"

## Step 0 — Onboard the person (ask; don't make them edit YAML)

Most people setting this up are not comfortable hand-editing YAML, and they shouldn't have to. **You**
collect the identity and **you** write it into `system/config/profile.yml` — the user only talks.

1. If `system/config/profile.yml → candidate:` still has `{{TOKEN}}`s, **ask for them in one friendly batch**,
   in plain language — not as a form:

   > To set up your workspace I need a few basics. You can paste them however you like:
   > **name, email, phone, city (in the United States), LinkedIn/GitHub/portfolio links, your current status**
   > (e.g. "final-year MSc student" or "employed at X"), and your **right to work in the United States**
   > (US citizen / green card / F-1 OPT / STEM OPT / needs H-1B sponsorship / …). Then paste or describe your background —
   > education, projects, jobs, skills — as much as you've got.

2. Take whatever they give (typed answers, an old CV, a LinkedIn export — any format) and **write the
   `candidate:` block yourself** with the substitution helper — no manual file editing by the user:

   ```bash
   python3 system/scripts/init_profile.py --set FULL_NAME="Jane Doe" --set EMAIL="jane@example.com" \
       --set PHONE="(XXX) XXX-XXXX" --set CITY="Fayetteville" --set COUNTRY="United States" --set ...
   ```

   (Or edit `system/config/profile.yml` on their behalf.) Only fill what they actually gave you; leave the
   rest as tokens for the gaps report. Never guess an email, phone, or link.

3. Save the free-form background they gave you into the right `context/` files verbatim before you
   structure it — basics into `01-basics.md`, projects into `04-projects.md`, and anything that
   doesn't obviously belong somewhere into `09-anything-else.md`. **You write these files for them.**
   `context/` is the archive and the source of truth; never make the user edit it themselves.

Then continue with Step 1. The whole point: a friend types answers in chat and gets a working
workspace; they never open a YAML file.

## Step 1 — Read

1. **`context/` — every file in it, in order, plus everything in `context/files/`.** Read the
   documents too: CVs, transcripts, LinkedIn exports, certificates. A transcript is usually the
   fastest source of the full module list, and old CVs routinely hold facts the user has forgotten.
   Note which files still say `Status: EMPTY` — those drive the gaps report.
2. `system/config/profile.yml` — whatever identity the user already filled
3. `PLACEHOLDERS.md` — the token vocabulary you are filling
4. `system/modes/_shared.md` — the honesty and ATS rules that govern the output

If every `context/` file is still `Status: EMPTY` **and** the user has given you nothing to work
with, do Step 0 first — interview them and write `context/` yourself. Never answer with "go and fill
in the files".

## Step 2 — Classify what you were given

Sort everything in `context/` into buckets, and note which buckets are empty — empty buckets drive
the gaps report:

| Bucket | Signals |
|--------|---------|
| Education | degrees, institutions, coursework lists, grades, thesis |
| Employment | employer names with dates and a role title |
| Internships / assistantships | labelled as intern, trainee, assistant, placement |
| Projects | built/designed/developed something, named or unnamed |
| Publications & research | papers, venues, patents, research groups |
| Awards & competitions | placed, won, shortlisted, ranked |
| Certifications | issuer + credential |
| Skills | tools, languages, platforms, domains |
| Constraints | visa, location, availability, compensation |
| Voice | how the person describes themselves in their own words |

**Confidence-tag every skill** as `core` (led real work with it), `working` (used it in a real
project) or `exposure` (coursework or self-study only). Long profiles that are mostly coursework
produce mostly `exposure` — that is the honest answer, and the tailor depends on it.

## Step 3 — Decide the two tracks

Propose Track A and Track B (see `system/profile/positioning.md`) from what the evidence supports, not
from ambition. Two useful patterns:

- **Experienced person:** their strongest lane, plus an adjacent lane where their combination is
  rarer and competition is lower.
- **Graduate / career changer:** the lane their degree and projects support, plus an operations- or
  domain-adjacent lane that hires on aptitude and coursework rather than years.

State the competition read honestly for each, and say which one you expect to convert faster.
Ask the user to confirm the two names before writing them everywhere.

## Step 4 — Write the knowledge base

Fill these files, replacing every `{{TOKEN}}` you have evidence for and **leaving the rest as
tokens**:

| File | What goes in |
|------|--------------|
| `system/profile/master-profile.md` | Contact; education with the **full module list** and coursework projects; every role with type labels; the **Projects & Build Bank** (one block per project, each with `Track:` and `Tags:`, no cap); training/bootcamp projects; hackathons; publications; awards; certifications; the signature-metrics table (empty if there are no real numbers); the confidence-tagged skills inventory with a `Synonyms` column; constraints; and the do-not-claim list |
| `system/profile/positioning.md` | Headline, core narrative, the two tracks, adaptive framing per archetype, the project reframing map, honest gaps, voice notes |
| `system/profile/skills-matrix.md` | Skills grouped into 5–8 categories, per-archetype ordering, the ATS keyword bank with synonym pairs, the never-claim list |
| `system/profile/interview-stories.md` | One STAR+R story per significant project or role; leave `R:` blank where no outcome was stated and list it in the gaps |
| `system/config/profile.yml` | The `candidate:` identity block from `context/01-basics.md` (write it yourself — the user shouldn't edit YAML), plus tracks, archetypes with signal words, narrative, compensation, location, competition strategy; set `meta.filled: true` only when no `{{TOKEN}}` remains in the candidate block |

Write real Markdown tables, not prose blobs. Keep `system/profile/master-profile.md` under ~600 lines; detail that
does not earn a resume line stays in `context/`, which is the archive.

## Step 5 — Gaps report (always print this)

End with three lists:

1. **Blocking gaps** — needed before any resume can be generated (name, contact, at least one
   education or employment entry, at least two projects).
2. **Quality gaps** — outcomes with no number, projects with no stack, roles with no dates. For
   each, ask a specific question: not "any metrics?" but "the dustbin project — did you measure how
   much faster detection got, or how many bins it handled?"
3. **Positioning questions** — anything where you had to choose between two honest readings, with
   your recommendation and the reason.

Then ask the questions in chat and **write the answers into `context/` yourself** — say which file
each one went into. Re-run afterwards: this skill is idempotent and merges, never overwriting what
the user wrote by hand.

Also check `context/QUESTIONS-FOR-YOU.md` — anything still open there is a question a real job has
already asked. Raise the top few with the user while you have their attention.

## Step 6 — Verify

Run:

```bash
python3 system/scripts/init_profile.py --check
```

Report what it prints. Any `{{TOKEN}}` left in `system/profile/master-profile.md` is expected on a first
pass; any left in the `candidate:` block of `system/config/profile.yml` is blocking.

## Re-running

On a second run, read the existing files first and **merge**: keep hand edits, add new facts, and
list what changed. Never silently overwrite a file the user has edited.
