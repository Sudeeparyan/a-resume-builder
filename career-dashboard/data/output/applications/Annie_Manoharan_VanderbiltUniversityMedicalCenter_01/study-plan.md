# Study plan for Vanderbilt University Medical Center - Data Engineer / Platform Administrator (Azure Databricks)

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Databricks | Have | "1+ year of experience with Databricks" - registered |
| Python (OOP) | Have | "2+ years of Python in an object-oriented paradigm" - registered |
| SQL | Have | "1+ year of SQL experience" - registered |
| Cloud (Azure/AWS/GCP) | Have | "2+ years implementing cloud solutions" - AWS + Azure SQL registered |
| Docker | Have | "containerization using Docker or Podman" - Docker registered |
| CI/CD (GitLab/GitHub/Azure DevOps) | Have (registered: SKILL-TOUCHED-001) | "CI/CD automation in GitLab, GitHub, or Azure DevOps" - CI/CD + Bitbucket registered; GitHub Actions YAML depth is new |
| REST APIs / microservices | Have | "REST data services, APIs, and microservices" - Flask registered |
| Databricks platform administration (compute policies, access controls, governance, cost monitoring) | Missing, learnable | 80% of the role: "Administer our Azure Databricks environment of 100+ workspaces" |
| Terraform / IaC | Missing, learnable (never-claim on resume) | "Infrastructure as Code solutions such as Terraform" |
| PowerShell / Bash | Bash Have via Linux; PowerShell missing, learnable | Bonus: "Experience with PowerShell and/or Bash" |
| Unity Catalog / data governance | Missing, learnable | "access controls, and governance" across 100+ workspaces |
| Cost/performance monitoring tooling | Missing, learnable (Grafana base is Have) | "proactive monitoring of platform health, performance, and costs" |
| Production admin at 100+ workspace scale | Structural | Years of operating a large shared platform; cannot be faked |
| Healthcare / HIPAA data context | Structural | Academic health system; regulated-data habits come from the job |

## Tier 1 - before the screening call (week 1-2)

1. **Databricks workspace administration vocabulary** (JD: "compute policies, access controls, and governance"). Learn: workspaces vs. clusters, cluster policies, instance pools, PATs vs. service principals, Unity Catalog basics. Resource: Microsoft Learn "Azure Databricks administration" learning path (free). Self-check: explain to a friend, without notes, how you'd stop a team from launching oversized clusters.
2. **Terraform fundamentals** (JD: "Infrastructure as Code solutions such as Terraform"). Learn: providers, plan/apply, state, modules. Resource: HashiCorp's free "Terraform: Get Started - Azure" tutorial. Self-check: write and `terraform plan` a config that creates one Azure resource group; say honestly: "learning it now, never run it in production."
3. **PowerShell basics** (JD bonus). Learn: cmdlets, pipes, scripting loops, Az module. Resource: Microsoft Learn "Automate administrative tasks with PowerShell" (free). Self-check: write a 20-line script that lists files over 100MB and logs them.
4. **GitHub Actions CI/CD mechanics** (JD: "CI/CD automation in GitLab, GitHub, or Azure DevOps"). Learn: workflows, jobs, runners, secrets, environments. Resource: GitHub's official "Understanding GitHub Actions" docs. Self-check: sketch a workflow that lints and tests on push, deploys on tag.
5. **Azure Databricks cost model** (JD: "monitoring performance and costs"). Learn: DBUs, cluster autoscaling vs. pools, serverless vs. classic compute, budget alerts. Resource: Databricks free edition + "cost management" docs. Self-check: answer "why did our bill double?" with three plausible causes and how you'd prove each.

## Tier 2 - before the technical round (week 2-5)

1. **Cluster policies and access control in practice.** Build policies restricting instance types and spot usage; map groups to entitlements. Artefact: a small repo with JSON cluster policy definitions plus a README explaining the guardrails and why.
2. **Terraform with the Databricks provider.** Provision a workspace-level setup: cluster policy, job, service principal. Artefact: GitHub repo `databricks-terraform-lab` with `main.tf`, variables, and a recorded `plan` output walkthrough.
3. **CI/CD pipeline for a Databricks job.** GitHub Actions workflow that runs pytest, validates notebooks with `databricks bundle validate`, and deploys on merge. Artefact: the repo's Actions tab showing green runs plus a short written walkthrough of the YAML.
4. **Platform health and cost monitoring.** System tables (`system.billing.usage`, `system.access.audit`) queried in a notebook; cost-per-workspace dashboard. Artefact: a notebook + one-page write-up of findings on her own free-tier workspace.
5. **REST ingestion pipeline, hardened** (JD: "variety of source systems - flat files, APIs, databases"). Python OOP pipeline pulling a public API into Delta Lake with retries, schema checks, and logging. Artefact: repo with tests and a run log.

## Build-now project (only if the JD needs a project type she has none of)

**"Mini platform admin kit" - not built yet.** The JD's center of gravity (IaC + CI/CD for Databricks, self-built) matches no project she has. Goal: automate provisioning and monitoring of a small Databricks environment the way VUMC runs its 100+. Data: NYC taxi open dataset as the payload. Stack: Terraform (Databricks + Azure providers), GitHub Actions, Databricks free edition, system tables, Python/pytest. Evaluation: `terraform apply` from clean state in under 15 min; CI pipeline blocks a deploy when a cluster policy is violated; cost notebook shows per-job DBU spend. Deliverable: public GitHub repo with README architecture diagram, Actions history, and a 2-page ops runbook. Hours: 30-40 across weeks 2-5. This satisfies the JD's "link to your GitHub profile" bonus directly.

## Honest answers for the structural gaps

- **100+ workspace scale:** "I've built pipelines on Databricks and I'm now deep into its admin surface - policies, governance, cost controls. I haven't operated a platform at your scale yet, which is exactly why this role appeals to me; I'd want to earn that under your senior engineers."
- **Healthcare domain:** "I haven't worked with clinical data or under HIPAA, but my medical IoT project taught me to treat sensitive telemetry carefully, and I'd complete VUMC's compliance training before touching anything."

## When this may go on the resume

Only after it is learned AND written into data/context/, then re-registered.

## Registry corrections
- CI/CD (GitLab/GitHub/Azure DevOps): the plan called this "Have (generic) / learn specifics"; it is a registered skill (SKILL-TOUCHED-001), so it is Have and needs no study.
