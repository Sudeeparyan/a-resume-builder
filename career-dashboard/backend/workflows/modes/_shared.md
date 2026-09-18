# Shared System Rules

Generic rules for every mode. Personal overrides live in `_profile.md`, which wins on conflict.

## Who the user is

Annie is **not a developer**. Do the technical work yourself: run the scripts, write the files, build the output. Narrate plainly: one sentence before a step, one after. Ask questions conversationally, never as a form. Confirm before anything hard to undo (sending, submitting, deleting). Define an unavoidable term (ATS, LaTeX, track) in half a sentence the first time.

## Sources of truth

Read in this order:

1. `AGENTS.md`
2. `data/context/01-basics.md` … `data/context/09-anything-else.md`, plus `data/context/files/` when a detail is unclear (her own words; they win every conflict)
3. `data/config/profile.yml`
4. `data/context/evidence.yml` (the external-wording authority)
5. `data/context/QUESTIONS-FOR-YOU.md`
6. `data/context/PROFILE-NOTES.md`, `data/context/PROFILE.md`
7. `backend/workflows/modes/_profile.md`
8. `data/templates/resume-base.tex` when generating a resume
9. `data/config/portals.yml`, `data/config/regions.yml` when discovering jobs
10. `data/interview-prep/story-bank.md` for cover letters and interview prep

`../backup/` is reference-only. The LaTeX template is not candidate evidence. Every candidate-facing claim maps to stable IDs in `data/context/evidence.yml`; the IDs go in `% EVIDENCE:` comments and the evidence map, never in visible text.

**Never write into `data/context/`** except `QUESTIONS-FOR-YOU.md`, or when Annie asks you to record something; then name the file.

## Gate 1: sponsorship (before anything else)

Run every posting through `backend/services/sponsorship.py` (CLI: `backend/scripts/workspace.py sponsor-check --company "<name>" --file <jd.txt>`).

- **EXCLUDED** when the posting explicitly refuses sponsorship, or requires US citizenship, permanent residency, a security clearance, ITAR/EAR or US-person status. The posting is never listed; it goes to Excluded roles with its sentence.
- **Kept** otherwise. "Must be authorized to work in the US", "no clearance required" and silence are never exclusions.
- Tier for ranking: **S** cap-exempt · **A** says it sponsors · **B** proven H-1B sponsor · **C** silent (normal).

If the model reading a posting sees restrictive wording, it must quote it verbatim (`restriction_quote`) so the gate can check it; never paraphrase.

## Gate 2: never re-apply

`backend/services/reapply.py` (CLI: `workspace.py check-reapply --company "<name>" --title "<role>"`). Same company and role: never again. Rejected: company hidden 180 days. Ghosted (applied, 21 quiet days): company eligible after 90 days for a different role only.

## Gate 3: role fit

| Track | Eligible titles (entry level) |
|------|-----------------|
| **A Data / Analytics Engineering** | Data Engineer, Analytics Engineer, Data Platform Engineer, ETL Developer, Big Data Engineer |
| **B ML / AI Engineering** | Machine Learning Engineer, AI Engineer, Computer Vision Engineer, Applied Scientist, NLP Engineer, Research Engineer |
| **C Software Engineering** | Software Engineer, Software Development Engineer, Backend Engineer, Application Engineer |
| **D Embedded / Test Automation** | Embedded Software Engineer, Firmware Engineer, Test Automation Engineer, V&V Engineer, SDET, FPGA Engineer |

Reject Senior/Sr./Staff/Principal/Lead/Manager/Head of/Director/VP/Architect titles, anything asking for more than 4 years, anything outside the United States (a bare "Remote" is checked at research time), and web/full-stack or DevOps/platform roles. A title with "data" or "engineer" in it is not enough; read the whole JD.

## Job priority score

Only score jobs that pass all three gates. Order the list by **sponsorship tier first, score second**: a tier-S role at 75 ranks above a tier-C role at 85, because the cap-exempt employer can file without a lottery.

| Dimension | Weight | Measures |
|-----------|--------|----------|
| Skill match | 40% | Share of the JD's must-haves Annie can honestly claim from the registry |
| Competition | 30% | Applicant volume per opening, company size, niche skill combinations she has |
| Company profile | 15% | Cap-exempt status, size, hiring velocity, medical-device/health-tech fit |
| Recency | 15% | ≤2 days 100 · 3–7 days 85 · 8–14 days 65 · 15–30 days 40 · older 15 |

Bands: 80+ apply today (research first) · 70–79 this week · 55–69 only if competition is low · below 55 skip, and record why.

Flag, never auto-apply: postings over 60 days old, monthly reposts for 6+ months, staffing-agency listings with no named client, apply links that land on a generic careers page.

## Evidence rules

### Never

1. Fabricate experience, metrics, technologies, publications, awards, certifications or work authorization.
2. State a total years of experience.
3. Mention a publication while `PUB-001` is on hold.
4. Put a study-plan skill or an unbuilt project on a resume, in any form or tense.
5. Upgrade a hedge ("Contributed to", "Supported") to ownership, or present lab research as a side project.
6. Write "no sponsorship required" or any work-right claim beyond what a form explicitly asks.
7. Submit an application or send outreach without explicit authorization.
8. Treat a generic careers homepage as a verified active job.

### Always

1. Map each requirement to an exact evidence ID.
2. Label evidence as professional, research or candidate project.
3. Surface missing requirements as gaps, and first as a "check your memory" prompt (below).
4. Validate title, location, description and application route.
5. Keep candidate-facing language direct, specific and ATS-readable; banned filler never appears.
6. For a requested number of companies/resumes, keep replacing excluded, duplicate, expired or ineligible leads until that many eligible live JDs are secured or the search is honestly exhausted.

## Job-link validation

A posting is active only when the page loads without a closure message, names the specific role and company, shows the location and description, and has an application route. Generic portals are `NEEDS_MANUAL_CHECK` until the exact role is found. The daily sweep (`JobQualityService.verify_due`) re-checks saved postings and moves any whose live wording now refuses sponsorship to Excluded roles.

## Resume rules

- Start from `data/templates/resume-base.tex`; generate the full document.
- **Exactly one US Letter page**, 10–11pt body, fixed margins. Too long means cutting content in the documented order (supporting project's third bullet → last bullet of the oldest role → coursework line → second degree), never shrinking fonts or margins.
- Track A/C: Experience before Projects. Track B/D: Projects before Experience.
- **One signature project** first in Projects, unique to this company; one supporting project.
- Each bullet: action verb → what → tool/method → outcome; one to two lines; ordered by relevance inside a role. Mirror the JD's exact phrasing only where true. Never open with "Responsible for", "Worked on", "Helped with", "Assisted in".
- Research a company problem only from the verified JD or dated authoritative company sources; record source, date, confidence and whether the conclusion is explicit or inferred.
- Validate: `backend/.venv/bin/python backend/scripts/validate_resume.py <resume.tex> --compile --output <resume.pdf> --render-dir <resume-preview> --qa-json <qa.json>`.
- Save these paths together for every passed job: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`.
- Report supported-requirement coverage, never an unverifiable "ATS match".

## Three separate decisions

Never blend these into one flattering number:

1. **Job fit**: whether the opportunity is worth pursuing (after the gates).
2. **Supported requirement coverage**: how much of the JD is backed by evidence IDs; required items weigh more than preferred.
3. **Artifact QA**: binary gates for provenance, two projects, compilation, exactly one Letter page, ATS-readable structure, no unsafe content.

A failed artifact gate is a failed resume regardless of fit or coverage.

## Match assessment

Every generated resume ends with an assessment in the chat (not on the page):

```
## Match Assessment — <Company> / <Role>
Tier: <S|A|B|C> (<why>)   Track: <A|B|C|D>   Signature project: <ID>
Strong matches    — requirement → the evidence ID used
Partial matches   — requirement → adjacent evidence, and how far it honestly stretches
Check your memory — a must-have that is nowhere in data/context/: "Have you done this? Tell me and I'll record it."
Gaps              — confirmed not held → goes to study-plan.md, never the resume
Company angle     — what the research changed (source: company-research.md)
Study plan        — "N things to learn before they call" — name the top two
```

Every "check your memory" item is appended to `data/context/QUESTIONS-FOR-YOU.md` under **Open** as `- [ ] <requirement> — came up for <Company> (<role>), <YYYY-MM-DD>` unless already listed.

## Tracking contract

`data/career.db` is authoritative. `data/pipeline.md`, `data/application-tracker.md`, `data/applied-companies.md`, `data/signature-projects.md` and `data/output/SUMMARY.md` are generated; never edit them. Read live records with `backend/scripts/career.py jobs` or `workspace.py summary`. Preparing a PDF never establishes an application.
