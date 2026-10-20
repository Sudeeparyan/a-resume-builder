# Study plan for Twilio - Software Engineer, Platform Engineering (L2)

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Kubernetes (deployments, pods, services) | Never-claim -> learn | "basic Kubernetes operations (deployments, pods, services) is expected" |
| Terraform / IaC | Never-claim -> learn | "contribute to Terraform-based infrastructure automation" |
| Go | Never-claim -> learn | "Working knowledge of at least one of Shell, Terraform, YAML, or Go" |
| Shell / YAML | Missing, learnable | Same language requirement; cheapest one to satisfy |
| AWS EC2 / S3 | Have | "basic exposure to AWS core services (such as EC2, S3, EKS)" |
| EKS / AKS | Missing, learnable | Dual-cloud clusters are the team's substrate |
| Azure basics (VM, Blob, VNet) | Missing, learnable | "dual-cloud infrastructure spanning AWS and Azure" |
| Docker | Have | "containerized infrastructure (Docker, Kubernetes)" |
| CI/CD | Have | "CI/CD pipelines (e.g., Harness or an equivalent)" |
| GitOps / ArgoCD | Missing, learnable | "Some exposure to GitOps workflows (e.g., ArgoCD)" |
| Kafka / event streaming | Have | "asynchronous event streaming (e.g., Kafka)" |
| Metrics/alerts (Grafana) | Have | "observability coverage, including metrics, alerts" |
| OpenTelemetry / distributed tracing | Missing, learnable | "basic distributed tracing" and desired "OpenTelemetry" |
| Canary / blue-green deploys | Missing, learnable | "Curiosity about advanced deployment strategies" |
| OPA/Gatekeeper | Missing, learnable (optional) | "Interest in policy-as-code tools" |
| AI-assisted dev tools (Claude Code) | Missing, learnable | "Practical experience with, or strong desire to learn, AI-assisted development tools" |
| Operating 12B-email-scale systems | Missing, structural | "process more than 12 billion emails during peak events" |
| 1-2+ yrs professional SWE experience | Structural (borderline) | Required qualification; answer with internships/projects honestly |

## Tier 1 - before the screening call (week 1-2)

1. **Kubernetes core objects** (deployments, pods, services, kubectl basics). Resource: the official Kubernetes Basics tutorial (kubernetes.io/docs/tutorials/kubernetes-basics). Self-check: in 30 min, from memory, explain what happens when a pod dies under a Deployment and sketch the YAML for one Deployment + one Service.
2. **Shell + YAML fluency** (she must satisfy "at least one of Shell, Terraform, YAML, or Go" with a non-never-claim answer first). Resource: linuxcommand.org "Learning the Shell" + YAML spec 1.2 cheat sheet. Self-check: write a 20-line bash script that parses a YAML file with yq and prints pod names; no notes allowed.
3. **Terraform mental model** (plan/apply, state, HCL blocks) — learn, never claim. Resource: HashiCorp's "Get Started - AWS" tutorial (developer.hashicorp.com). Self-check: explain in 5 minutes what `terraform plan` reads and writes, and why state files shouldn't be committed.
4. **GitOps vocabulary** (ArgoCD: desired state, sync, drift) reacting to "Some exposure to GitOps workflows". Resource: ArgoCD docs "Getting Started" (argo-cd.readthedocs.io). Self-check: whiteboard how a Git commit becomes a running pod via ArgoCD, naming each component.
5. **Observability words** (metrics vs logs vs traces; she has Grafana, add tracing). Resource: OpenTelemetry "Concepts" docs (opentelemetry.io/docs/concepts). Self-check: explain the three signal types and when a trace beats a metric, in under 10 minutes aloud.

## Tier 2 - before the technical round (week 2-5)

1. **EKS hands-on**: deploy a small containerized API (she knows Docker, Flask) to a free-tier EKS or local kind cluster. Artefact: a repo with Dockerfile, k8s manifests, and a README showing `kubectl get pods` output and a rolling update. Label it "learning project, not production experience."
2. **Terraform + AWS module**: write one Terraform module that provisions an S3 bucket and an EC2 instance (both registered skills, so the cloud side is honest) with remote state. Artefact: the repo plus a written walkthrough of a plan/apply/destroy cycle.
3. **CI/CD + GitOps mini-pipeline**: extend item 1 with a CI workflow (GitHub Actions — CI/CD is registered) that builds, tests, and pushes the image, plus a paragraph comparing push-based CI to ArgoCD pull-based GitOps. Artefact: the working workflow file and the comparison note.
4. **Distributed tracing demo**: instrument her existing Flask API with the OpenTelemetry Python SDK, export to Jaeger locally. Artefact: a notebook or README with screenshots of one trace spanning two services, explaining spans and context propagation.
5. **Go fundamentals** (never-claim -> learn; the team's likely code language). Resource: go.dev/tour. Artefact: a tiny CLI (e.g., a kubectl-style pod-lister against the kind cluster API) in ~150 lines, with tests.

## Build-now project (only if the JD needs a project type she has none of)

She has no Kubernetes/Terraform/self-built-CI-CD project; all existing projects are ML/embedded. **"Mini platform deploy" (not built yet).** Goal: a two-service app (Flask API + worker consuming from a Kafka topic — both registered skills) deployed to a kind cluster. Data: synthetic JSON events (simulated email-send events, nodding to Twilio's domain). Stack: Docker, kind, Terraform for an S3/EC2 sidecar resource, GitHub Actions CI, optional ArgoCD. Evaluation: rolling update with zero failed health checks; one Grafana dashboard; one Jaeger trace. Deliverable: public repo, architecture diagram, 1-page writeup. Hours: ~25-35 over weeks 3-5.

## Honest answers for the structural gaps

- "I haven't operated systems at billions-of-messages scale. What I bring is strong data-streaming fundamentals from Kafka and Spark projects, and I'm actively building hands-on Kubernetes skills — I'd expect to learn your scale practices from the senior engineers, exactly as this L2 role describes."
- "My professional experience is on the earlier side of the 1-2 year band, so I compensate with depth in fundamentals and a fast learning loop — including the AI-assisted tooling your team uses."

## When this may go on the resume

Only after each skill is genuinely learned AND written into data/context/, then re-registered — never before, and Kubernetes, Terraform, and Go stay off it until that bar is met.
