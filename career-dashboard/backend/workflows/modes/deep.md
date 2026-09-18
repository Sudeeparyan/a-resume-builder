# Mode: Deep — Company and Team Research

Run this for **every** role that passes the gates and proceeds to a resume, not only for high scorers. `company-research.md` is a required artifact. It decides which real skills get promoted, which projects lead, and what goes into the study plan. A shorter version is fine for a low-priority role; it is never skipped. If the web is unreachable, produce the JD-only version and label it; never fill gaps with invention.

## 0. Read `data/context/` before you browse

Research is a comparison: what this company needs versus what Annie actually has.

| From | What it changes |
|------|-----------------|
| `04-projects.md`, `05-skills.md`, `evidence.yml` | The demand map in §6 |
| `02-education.md` | Which named requirements a module already covers |
| `01-basics.md` | Sponsorship matters: confirm the posting's wording and the employer type (university, academic medical center, national lab, nonprofit research institute = cap-exempt, tier S) |
| `07-preferences.md` | Whether the role is worth the effort at all; say so early if not |
| `08-voice.md` | The vocabulary for the fit narrative and any cover letter |

Anything the company wants that is nowhere in `data/context/` is first a "did you forget to add it?" prompt, logged in `QUESTIONS-FOR-YOU.md`, and only a gap once she confirms.

## 1. What they do

Product, customers, business model, stage, ownership, headcount and trend.

## 2. Sponsorship and hiring reality

- The posting's exact authorization/sponsorship wording, quoted.
- Cap-exempt status (a `.edu` domain, a university hospital, a national lab, a nonprofit research institute) and why.
- H-1B history from the dashboard's tier evidence (approvals and years); E-Verify if stated (matters for STEM OPT).
- If anything suggests they cannot hire her (citizenship, clearance, ITAR/EAR), stop: the posting belongs in Excluded roles.

## 3. Engineering and tooling reality

Public stack signals: engineering blog, GitHub org, adjacent job ads, talks, docs. What the team runs beats what a recruiter listed; note where they disagree.

## 4. The team and current pressures

Who the role reports to if discoverable, team size, new or backfill headcount, recent launches, funding, layoffs, regulation, competitors.

## 4b. Where they are going next

Stated roadmap, the pattern of their other open roles, investment signals, migrations in progress, public commitments. Mark each as confirmed or inferred.

## 5. What they will expect from this hire

Three to five sentences on months 1–3 and where the role goes by month 12, implied by stage, stack, pressures and roadmap.

For every problem signal record:

| Field | Required value |
|---|---|
| Problem/initiative | Short factual paraphrase |
| Source | Verified JD or authoritative employer URL |
| Published/accessed | Exact date |
| Evidence class | Explicit / inferred |
| Confidence | High / medium / low |
| Relevant JD requirement | Requirement ID |

Prefer the JD and first-party sources; a third-party article may add context but is never the sole basis for what the team is solving.

## 6. Skills demand map (drives the resume and the study plan)

| Skill / tool | Named by | How central | Annie's real level | Where it goes |
|--------------|----------|-------------|--------------------|---------------|
| e.g. Apache Flink | JD must-have + eng blog | Core | Strong (`SKILL-STREAMING-001`) | Resume — lead the skills line |
| e.g. dbt | Adjacent job ads | Likely within 6 months | Not in the bank (`SKILL-NEVER-001`) | Study plan, Tier 2 |

Levels come from `05-skills.md` (Strong / Used it / Touched it) as registered in `evidence.yml`. The last column has exactly three destinations: **Resume** (she has it; promote it in their vocabulary), **Study plan** (learnable before the interview; never on the resume), **Honest gap** (structural; named in the match assessment with an honest answer). Research changes which true facts lead; it never adds a skill she does not have.

## 7. Evidence-backed angle

- Rank every resume-ready project; name the **signature** project (unused by other companies, not supporting-only) and the supporting project, with scores.
- One interview story from `data/interview-prep/story-bank.md`.
- Material gaps and the honest mitigation.
- If no credible analogue exists, record `NO_STRONG_PROJECT_MATCH` and hand a build-now spec to the study plan. Never describe a project as built for the target employer.

## 8. Questions to ask them

Four questions that could only come from this research, at least one from §4b.

## Output

Save `company-research.md` in the application folder once the role is verified active and eligible: sponsorship notes, the demand map, the ranked projects and the chosen signature, current source URLs and dates, and explicit-versus-inferred labels.
