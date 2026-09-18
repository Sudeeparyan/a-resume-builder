# Mode: Batch Resumes — Up to Ten Isolated One-Page Applications

Use when Annie supplies several verified JDs or URLs, asks for the top eligible jobs in the pipeline, or says "give me 10 companies" (or `/hunt`). Maximum released batch size: 10.

## Ten-company trigger

Unless she explicitly asks for a list only, "give me 10 companies" means:

`discover -> sponsorship gate -> never-re-apply check -> verify 10 live JDs -> rank by tier then score -> research -> 10 one-page resumes -> compile -> visual QA -> study plans -> deliver`

Excluded (sponsorship), already-seen, rejected-within-180-days, duplicate, expired, inaccessible and out-of-scope leads do not count toward ten. Keep searching replacements across all four tracks and all US hubs plus Remote (US). `profile.yml ten_company_request.batch_mix` is the default spread (A 4, B 2, C 2, D 2), not a quota to fill with weak matches. If the honest search is exhausted below ten, release the valid subset and report the coverage and the exact shortage.

## Preflight

1. Read all of `data/context/` first. A batch against unread context produces ten near-identical resumes.
2. Create a stable run ID: `{YYYYMMDD-HHMM}-{short-hash}`.
3. Save a durable manifest at `data/output/batches/{run-id}/batch.yml` (copy `data/templates/batch.example.yml`); input identity and hash fields stay immutable while the runner replaces status atomically.
4. For each lead: run the gate (`workspace.py sponsor-check`) and the re-apply check (`workspace.py check-reapply`); save excluded leads with their sentence (`workspace.py` or the dashboard) so they show under Excluded roles.
5. Save a JD snapshot and its SHA-256 for every surviving lead; verify role, US location, seniority (≤4 years), liveness and application route.

A request for ten resumes never authorizes generic company documents without ten usable JDs.

## Signature projects across the batch

Ten companies need ten **different** signature projects. Solve it as an assignment across the whole batch, not greedily:

1. Score every resume-ready project against every company's requirements and researched problem.
2. Exclude projects already owned by another company in `data/signature-projects.md` and projects registered `signature_eligible: false`.
3. Assign so the **total** match is highest; a project may be worth spending where it is uniquely strong.
4. If the bank covers fewer companies well than the batch has, say so plainly ("your projects cover 7 of these 10 well"), ship the strongest real project in the weak slots and write a build-now spec into each of those `study-plan.md` files. Never put an unbuilt project on a resume.

## Per-job isolation

Each job gets its own directory, named like every other application:

```text
data/output/batches/{run-id}/Annie_Manoharan_<Company>_<NN>/
  job-description.md
  evaluation.md
  company-research.md
  study-plan.md
  evidence-map.yml
  resume.tex
  resume.pdf
  resume-preview/
    page-01.png
  qa.json
```

Do not reuse company research, requirement IDs or content plans across workers unless each job independently supports them. The runner also owns `worker.log`; it is an audit file, not one of the nine release artifacts.

## Worker contract

`snapshot -> gate -> eligibility -> evaluation -> research -> evidence map -> signature + supporting project -> write -> compile -> QA -> visual review -> study plan`

A worker is complete only when all nine artifact paths exist and `qa.json` reports every hard gate passed. An exit code alone is not completion. Use at most three evidence-safe render repairs (the documented cut order); never shrink fonts below 10pt or touch margins. Preserve failed artifacts and the failure reason.

## State and resumability

| Field | Meaning |
|---|---|
| job_id | Stable per-JD hash |
| status | pending / running / passed / rejected / failed |
| attempts | Render/QA attempts |
| selected_project_id | The signature project when passed |
| page_count | Must be 1 when passed |
| coverage | Diagnostic supported requirement coverage |
| error | Exact last failure |

Resume a run by skipping only `passed` and policy-`rejected` items whose snapshots and candidate revision are unchanged.

Use `backend/scripts/run_resume_batch.py` when workers are executable commands. `worker_command` is a shell-free YAML argument list; placeholders include `{job_id}`, `{artifact_dir}`, `{snapshot_path}` and `{attempt}`. A worker may write `worker-result.json` with `{"status":"rejected","reason":"..."}`.

`backend/.venv/bin/python backend/scripts/run_resume_batch.py data/output/batches/{run-id}/batch.yml --retry-limit 3`

## Cross-batch audit

1. Name, phone, email, portfolio, GitHub, employer titles/dates, degrees and ownership wording are identical across every resume.
2. Ten unique output paths and matching JD hashes.
3. Every passed resume is one Letter page with a signature project unique to its company and one supporting project.
4. Flag near-identical skill ordering or bullet selection; tailoring should follow real differences in requirements.
5. Report passed, rejected, failed and retryable counts.

`backend/.venv/bin/python backend/scripts/validate_batch.py data/output/batches/{run-id}/batch.yml --json data/output/batches/{run-id}/batch-qa.json`

## Report

One table, then the extras:

```
| # | Company | Role | Track | Tier | Posted | Score | Apply link (verified) | Folder | Signature project | Study plan |
```

- **Excluded** — each cut posting with the sentence that triggered it.
- **What to study first** — the skills that appear across the most of these applications (also in `data/output/SUMMARY.md`), so one week of study lifts several interviews.
- **Signature coverage** — strong matches, weak slots and the build-now specs proposed.
- **Check your memory** — de-duplicated must-haves missing from `data/context/` that she might actually have; append each to `QUESTIONS-FOR-YOU.md` once.

Annie reviews and submits each application herself. Eight valid resumes and an explicit two-role shortage is a correct result; two fabricated ones are not.
