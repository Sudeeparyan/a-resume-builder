# Study plan for Color Health - Software Engineer, New Grad 2026

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python | Have | Named in the modern web stack. |
| AWS | Have | Named as a platform for services and infrastructure. |
| SQL | Have | Named for application data. |
| HTML5, CSS3 | Have | Named web foundations for patient experiences. |
| ML/AI applied to real-world problems | Have | The role supports AI-enabled care workflows. |
| LLM-powered feature integration | Have | Helpful, not required; the profile lists a related project. |
| Automated testing | Have | The JD stresses testing best practices and rigor. |
| Team collaboration (Agile/Scrum) | Have | The role involves product and engineering peers. |
| Django | Never-claim — learn only | Named as a modern web-stack option. |
| React | Never-claim — learn only | Named for patient-facing experiences. |
| REST APIs | Missing, learnable in 3–6 weeks | Connect services and user experiences. |
| ES6+ | Missing, learnable in 3–6 weeks | Named for modern web development. |
| Web development fundamentals | Missing, learnable in 3–6 weeks | Core context for onboarding and patient experiences. |
| AI tools in development workflows | Missing, learnable in 3–6 weeks | The JD explicitly calls out code-generation tools/Copilot. |
| Engineering design, code quality/DRY, code review | Missing, learnable in 3–6 weeks | The JD values high-quality code, design, and review. |
| Logging, monitoring, alerting | Missing, learnable in 3–6 weeks | Explicit examples of rigorous engineering practice. |
| Patient onboarding, risk assessment, screening workflow | Missing, learnable in 3–6 weeks | These are central product journeys at Color. |
| Four-year CS degree; 2025/2026 graduation | Not classified as a skill gap | An eligibility criterion, not a skill; titles provided do not establish major or graduation year. |

## Tier 1 - before the screening call (week 1-2)

1. **REST/HTTP basics** (“services and experiences”; “REST APIs”): learn methods, status codes, JSON, request/response, and idempotency. Free resource: [MDN HTTP overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview). **30-minute check:** sketch a patient-enrollment endpoint, its request/response, and four error cases.
2. **ES6+ and React orientation** (“React…ES6+”; React is learn-only): learn modules, async/await, components, props/state, and forms. Free resource: [React Quick Start](https://react.dev/learn). **30-minute check:** make a small form component and explain its state and validation; label it practice, not experience.
3. **AI-assisted development** (“Experience using AI tools…code generation, copilot”): practice asking for a small code change, reviewing every suggestion, and checking tests/security instead of trusting output. Free resource: [GitHub Copilot documentation](https://docs.github.com/en/copilot). **30-minute check:** use an available assistant (or inspect a documented example) to propose a change, then write down two defects or risks you would verify.
4. **Django foundations** (“Django”; learn-only): study request routing, views, models, migrations, and built-in tests. Free resource: [Django tutorial](https://docs.djangoproject.com/en/stable/intro/tutorial01/). **30-minute check:** explain the request-to-response path and outline a test for an invalid enrollment form.

## Tier 2 - before the technical round (week 2-5)

1. Build the new web workflow below to practice React/Django together. **Proof artefact:** a small public repo with README, architecture sketch, setup steps, and tests; clearly label it as a learning project.
2. Practice API contracts for enrollment and screening status (“onboard, assess risk…appropriate screenings”). **Proof artefact:** a written walkthrough with two endpoint schemas, validation rules, status/error responses, and automated test cases.
3. Learn healthcare workflow boundaries (“guideline-based,” “physician-led”): separate data capture and routing from clinical decisions; use synthetic data only. **Proof artefact:** a one-page workflow diagram plus a short note on safe failure/escalation paths.
4. Learn basic operational signals (“logging, monitoring, alerting”). **Proof artefact:** a runbook for the demo app naming three useful events/metrics, one alert threshold, and a sample incident investigation.

## Build-now project

**Not built yet — small full-stack patient-onboarding demo.**
- Goal: demonstrate enrollment and screening-status steps, not diagnose or recommend care.
- Data: fabricated patient records and fictional screening options; no real patient data.
- Stack: React, Django, REST endpoints, SQLite; learn-only React/Django.
- Include form validation, consent acknowledgement, and status history.
- Add API tests for valid, invalid, and duplicate submissions.
- Add a README, setup instructions, architecture sketch, and explicit clinical-safety limits.
- Evaluation: tests pass; invalid inputs are rejected; workflow states are traceable.
- Deliverable: a small repository with a short demo walkthrough and test output.
- Scope: 20–30 hours over 2–3 weeks.

## Honest answers for the structural gaps

No years-of-production-experience or clearance requirement appears in this JD, so no such structural gap is identified. The education titles supplied do not verify the requested CS major or graduation year; I would state my actual degree and graduation date plainly, without implying either criterion unless accurate.

## When this may go on the resume

Only after a skill is learned AND written into `data/context/`, then re-registered.
