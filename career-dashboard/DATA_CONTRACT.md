# Data Contract

This contract keeps generated job and company content from contaminating Annie's profile.

## Candidate-owned truth layer

These files change only when Annie supplies evidence or explicitly approves a correction:

- `data/context/01-basics.md` … `data/context/09-anything-else.md` and `data/context/files/` (her own words and her 14 real resumes)
- `data/context/evidence.yml`
- `data/context/PROFILE.md`
- `data/context/PROFILE-NOTES.md`
- `data/config/profile.yml`
- `data/interview-prep/story-bank.md`

`data/context/QUESTIONS-FOR-YOU.md` is the one file in `data/context/` agents may write to without being asked: they add questions; Annie answers.

Agents may identify gaps but must not promote target-JD terms, company technologies, study-plan skills, proposed work or inferred results into this layer.

### Evidence registry schema

Every entry under `claims` and `projects` in `data/context/evidence.yml` needs a non-empty `source_refs` list, a `status` (`confirmed`, `user_reported`, `conditional`, `hold`, `missing`) and an `approved_external_use`. `hold` and `missing` entries never reach a resume; the validator rejects a held evidence ID anywhere in a resume source.

Every resume-ready project has a `resume_content` mapping with exactly these keys:

```yaml
resume_content:
  title: "Non-empty text"
  context: "Non-empty text"
  bullets:
    - "Non-empty bullet"
    - "Non-empty bullet"
```

`bullets` holds two or three non-empty strings. The registered title, context and bullets are the exact visible project block; tailoring may select it but may not paraphrase it. `signature_eligible: false` marks a project that may only be the supporting project.

## Sponsorship and application memory

`data/config/sponsorship.yml` (refusal and citizenship/clearance patterns, negation guards, cap-exempt signals, tiers) and `data/sponsors/sponsors-uscis.csv` (public USCIS employer history) are policy and public data, not candidate claims. The gate's decisions live in `data/career.db`: `jobs.sponsor_tier`/`sponsor_evidence`, `excluded_postings` (with the triggering sentence), `reapply_history` and `signature_assignments`.

## System logic layer

Reusable behavior; may be improved without changing candidate facts:

- `AGENTS.md`, `CLAUDE.md`
- `.github/agents/*.agent.md`
- `backend/workflows/*.md`, `backend/workflows/modes/*.md`, `backend/workflows/agents/*.md`
- `backend/**/*.py`
- `data/templates/*`
- `README.md`, `docs/*.md`

## Renderer

`data/templates/resume-base.tex` is a fixed one-page US Letter renderer populated only from approved evidence. It is not a factual source. `backend/resume_contract.py` derives the page count, paper, font bounds, section orders, header and stable facts from `profile.yml` and `evidence.yml`.

## Generated job layer

Every application has one isolated folder, `data/output/applications/Annie_Manoharan_<Company>_<NN>/`, with exactly these required artifact paths:

```text
job-description.md
evaluation.md
company-research.md
study-plan.md
evidence-map.yml
resume.tex
resume.pdf
resume-preview/page-01.png
qa.json
```

They may cite candidate evidence IDs; they never update the truth layer. `study-plan.md` lists skills Annie does not have yet; none of them may appear on any resume until learned and recorded in `data/context/`.

`data/output/SUMMARY.md`, `data/signature-projects.md`, `data/pipeline.md`, `data/application-tracker.md`, `data/applied-companies.md`, `data/jobs.json` and `data/activity.json` are generated projections of `data/career.db`. Never hand-edit them.

## Rule

Company research can decide which real evidence is relevant. It can never create candidate evidence.
