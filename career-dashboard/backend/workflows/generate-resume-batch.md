---
description: "Resumable isolated generation and QA for 2-10 verified US jobs for Annie; a 10-company request includes discovery, the sponsorship gate and 10 complete one-page resumes."
---

# Generate Resume Batch

1. Read `AGENTS.md` and `backend/workflows/modes/batch-resumes.md`.
2. If Annie says "give me 10 companies" (or `/hunt`), run discovery first (tracked career pages, then AI discovery) and keep replacing excluded, already-seen, rejected, expired and duplicate leads until 10 distinct eligible live JDs are secured or the search is honestly exhausted.
3. Preflight 2–10 release JDs or verified URLs through the sponsorship gate and the never-re-apply check.
4. Save a batch manifest (from `data/templates/batch.example.yml`), unique job IDs, snapshots and hashes.
5. Assign signature projects across the whole batch so no two companies share one; run `backend/workflows/generate-tailored-resume.md` independently per job.
6. Require the nine per-job release artifacts: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`.
7. Treat missing artifacts or failed QA as a worker failure even when compilation succeeded.
8. Resume safely by skipping only passed jobs whose JD hash and candidate revision are unchanged.
9. Run the cross-batch invariant audit (`backend/scripts/validate_batch.py`).
10. Return a ranked table (tier first, then score) plus passed, rejected, failed and retryable jobs with direct PDF and folder paths, the excluded postings with their sentences, and what to study first.

If fewer than the requested count remain after a broad search, report the shortage; never fabricate replacement resumes.
