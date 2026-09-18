# Mode: Resume — Evidence-Grounded One-Page Tailoring

Use this only after the job has passed the sponsorship gate, the never-re-apply check and the evaluation.

## Required inputs

- Saved JD snapshot: `data/output/applications/Annie_Manoharan_<Company>_<NN>/job-description.md`
- Evaluation with normalized requirement IDs: `.../evaluation.md`
- Company research: `.../company-research.md`
- Candidate revision from `data/config/profile.yml`
- Claim/project registry: `data/context/evidence.yml`
- Fixed renderer: `data/templates/resume-base.tex`
- Signature ownership: `data/signature-projects.md`

Do not generate a company-tailored resume from only a title and employer name.

## Content plan

Write `evidence-map.yml` in the application folder before editing LaTeX:

```yaml
candidate_revision: "2026-09-18.1"
job_id: "..."
role_eligible: true
job_snapshot_sha256: "..."
supported_requirement_coverage: 0
sponsor_tier: "S|A|B|C"
requirements:
  - id: "R01"
    priority: "required"
    text: "..."
    evidence_ids: ["..."]
    strength: "strong|partial|gap"
company_problem:
  statement: "..."
  source_url: "..."
  published_or_accessed: "YYYY-MM-DD"
  evidence_class: "explicit|inferred"
  confidence: "high|medium|low"
selected_project_id: "PROJ-..."       # the signature project
selected_project_reason: "..."
resume_claim_ids: ["..."]
held_claims_used: []
```

Every candidate claim needs an evidence ID. Company facts are not candidate evidence and may never be copied into skills or experience. A requirement with strength `gap` goes to `study-plan.md`, never onto the page.

## Conditional skills

Some registry skills are usable only alongside the evidence that proves them (`approved_external_use`):

- `SKILL-GENAI-001` (LangChain, FAISS, Ollama, RAG …): only with `PROJ-P04-NEWS-RAG`.
- `SKILL-CV-TOOLS-001` (YOLO11n-Pose, OC-SORT, LSTM, Res-UNet): only with `PROJ-P02-MIGA` or `PROJ-P03-DUALFIT`.
- `SKILL-DATA-TOOLS-001` (Pandas, NumPy, Flask, PostgreSQL …): only with `EXP-INSOPS-001`, `PROJ-P05-RESUME` or `PROJ-P06-EXPENSE`.
- `SKILL-DESKTOP-001` (WPF, .NET, Git, Jira): only with `EXP-SOLITON-PE-001`.
- `SKILL-EMBEDDED-TOOLS-001` (Proteus, MPLAB, Verilog): only with `PROJ-P07-FPGA`, `PROJ-P08-ELEVATOR` or `EXP-CRYSTAL-001`.
- `SKILL-LAKEHOUSE-001` (Databricks, Spark, Delta Lake): skills list only, with InsOps on the page; never a bullet.
- `SKILL-TOUCHED-001` (Docker, CI/CD, Java, Linux …): skills list only, never a bullet that implies it produced something.
- `SKILL-NEVER-001` (Kubernetes, Terraform, dbt, Snowflake …): never. Study-plan material only.

Label candidate projects and lab research so the reader can tell them from employment.

## Signature and supporting project

1. Rank the resume-ready projects in `data/context/evidence.yml` with `profile.yml > project_selection > ranking_weights`.
2. The **signature** project is the best-ranked project that no other company owns (`data/signature-projects.md`) and that is not registered `signature_eligible: false`. It goes first in Projects.
3. The **supporting** project is the next best; it may repeat across companies.
4. Use the registry's `resume_content` title/context/bullets exactly; automated QA binds the visible text to the ID. A supporting project may show its first two bullets only.
5. Never create a third project block, turn coursework into a signature, or imply work for the target employer.
6. If nothing unused fits, say so in the evidence map, ship the strongest real project and write a build-now spec into `study-plan.md`.

## One page, fixed typography

Keep the template layout. Body text is 10–11pt; margins and line spacing are fixed and validated.

| Slot | Budget |
|---|---|
| Education | MS line, one coursework line (JD modules first), BE line |
| Technical Skills | four compact categories: Languages, Data Engineering, Machine Learning and AI, Cloud and Tools |
| InsOps (Data Engineering Intern) | 2–3 bullets from `EXP-INSOPS-001` |
| Teaching / Research Assistant | 1–2 bullets each |
| Soliton (Project Engineer) | 2 bullets, including the Dräger bullet when relevant |
| Signature project | title/context and 3 bullets |
| Supporting project | title/context and 2 bullets |

Tracks A and C put Professional Experience before Projects; B and D put Projects first. Each bullet: action, scope, method, supported result. A number is optional; never invent one.

## Rendering loop

1. Copy the template into the application folder's `resume.tex`, or use Resume Studio (**Fit to one page** does steps 2–5 automatically).
2. Change only content slots and project fields.
3. Run `backend/.venv/bin/python backend/scripts/validate_resume.py <folder>/resume.tex --compile --output <folder>/resume.pdf --render-dir <folder>/resume-preview --qa-json <folder>/qa.json`.
4. Too long: cut in order — supporting project's third bullet, last bullet of the oldest role, coursework line, second degree. Too sparse: add the highest-relevance unused registered bullet.
5. Never shrink the font below 10pt, the margins or the line spacing.
6. Confirm `resume-preview/page-01.png` is the only preview image.
7. Release only when every hard gate passes and a visual review is recorded.

## Output report

Return, in the chat:

- sponsorship tier and why; eligibility decision and job-fit score;
- supported requirement coverage with required gaps;
- the signature project and why it matches the sourced company problem;
- paths to all nine artifacts: `job-description.md`, `evaluation.md`, `company-research.md`, `study-plan.md`, `evidence-map.yml`, `resume.tex`, `resume.pdf`, `resume-preview/page-01.png`, `qa.json`;
- any missing fact Annie should confirm (also appended to `QUESTIONS-FOR-YOU.md`);
- the wall: the study-plan skills are not on the resume and will not be until learned.

Never promise an interview or shortlist.
