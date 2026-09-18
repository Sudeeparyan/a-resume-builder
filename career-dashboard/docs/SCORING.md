# Scoring and evidence definitions

The UI presents three independent results.

## ATS readiness (0–100)

- PDF text extraction: 30
- Recognizable sections: 25
- Simple single-column structure: 20
- Contact parsing: 15
- Encoding and link cleanliness: 10

This is machine readability, not an interview probability.

## Resume coverage (0–100)

Grounded JD requirements are persisted by JD hash. Every requirement retains an exact JD excerpt. Numerical coverage is deterministic: required 60%, responsibilities 25%, preferred 15%. AI may extract structured candidates but cannot choose the score.

Each requirement is labeled `found_in_pdf`, `supported_missing_from_pdf`, `partially_supported`, or `unsupported_or_unknown`. Only the second category is a safe tailoring candidate; unsupported requirements must not be keyword-stuffed.

## Opportunity fit

`Strong`, `Partial`, `Weak`, or `Blocked`, with evidence IDs and hard blockers. It is never averaged into either document score. Evidence/claim review, one-page layout checks, and visual release approval remain separate gates.

## Sponsorship tier (ranking, never a score)

The gate runs before any score. A posting that refuses sponsorship or requires US citizenship, permanent residency, a security clearance, ITAR/EAR or US-person status is **excluded**, never scored. Everything else gets a tier:

| Tier | Meaning | Source |
|---|---|---|
| S | Cap-exempt employer: files H-1B year-round, no lottery | `.edu` domain, known list, name signals, or the discovery agent's `employer_type` |
| A | The posting says it sponsors | The first positive sentence |
| B | Proven H-1B sponsor; the posting is silent | USCIS employer history (approvals and years) |
| C | Silent, no record: the normal case, still worth applying | — |

Lists sort by tier first, then date. The Balanced five mix needs tier S, A or B for its mid-size and large slots.

## Relevance blockers

A saved posting's relevance carries hard blockers: outside the United States (a bare "Remote" is checked at research time), a Senior/Staff/Lead/Principal/Manager title, more than 4 years required, a title outside the four target families, a too-short description, or a sponsorship refusal (quoted).

## Project ranking

Two distinct registered resume-ready projects are ranked by problem similarity 35, required-skill evidence 30, evidence strength 20, domain/stakeholder similarity 10, and recency 5. The best-ranked project that no other company owns becomes the **signature** project; the next becomes the supporting project. Projects registered `signature_eligible: false` only support. Manual choices remain until automatic reranking is explicitly requested.
