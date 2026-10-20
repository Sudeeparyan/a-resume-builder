# Study plan for Twitch - Software Engineer II, Fintech

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python | Have | "Proficiency in at least one modern language beyond ABAP — Python, TypeScript/JavaScript" |
| AWS Lambda, S3, EC2 | Have | "Build and operate AWS-native services (Lambda, Step Functions, API Gateway, S3...)" |
| CI/CD, Git, Docker | Have | "Deploy... including CI/CD pipelines, IAM roles" |
| Design patterns / SOLID | Have | "Strong understanding of object-oriented design patterns (Factory, Strategy, Observer, Template Method)" |
| REST APIs (Flask) | Have | "API-Based (REST, OData, SOAP) patterns" |
| LangChain, prompt engineering, LLM workflows | Have | "Demonstrated heavy use of AI tools... integrated into your daily engineering workflow" |
| ABAP, CDS views, AMDP, HANA SQL, RAP, OData/SEGW, BAPI/RFC, S/4HANA, BTP, Fiori | Missing — structural | Core of the role: "4+ years of hands-on SAP development experience" |
| Finance domain (FI/CO, AP, AR, GL) | Missing — learnable | "Finance domain knowledge — familiarity with FI/CO, FI/CA, AP, AR or GL" |
| OAuth 2.0 / OIDC | Missing — learnable | "Understanding of OAuth 2.0 authorization flows... and OpenID Connect" |
| Postman/Bruno API testing | Missing — learnable | "Testing and debugging APIs using tools like Bruno or Postman" |
| AWS CDK (TypeScript/Python), multi-env topology | Missing — learnable | "Deploy and manage the AWS infrastructure... using CDK" |
| Step Functions, DynamoDB, API Gateway, ECS/Fargate | Missing — learnable | Named AWS services she hasn't run in production |
| MCP servers, Bedrock agents, Claude workflows | Missing — learnable (extends her LangChain base) | "MCP servers, Bedrock-based agents, and Claude-powered workflows" |
| Redshift | Never-claim | "Data pipelines that move financial data between SAP, Redshift, and enterprise applications" |
| Terraform | Never-claim | JD accepts "CDK, Terraform, or CloudFormation" — learn CDK, never claim Terraform |
| Stakeholder collaboration with Finance/Accounting/Tax | Missing — learnable (soft) | "Collaborate with Finance, Accounting, and Tax stakeholders" |

## Tier 1 - before the screening call (week 1-2)

1. **SAP vocabulary, honestly framed.** Learn what ABAP, CDS views, RAP, OData, and S/4HANA actually are so she can discuss the role's SAP half intelligently without implying experience. Resource: openSAP's free "Modernization with SAP S/4HANA" / SAP Learning ABAP overview courses. Self-check: in 30 minutes, explain out loud what a CDS view and a RAP business object are, and where OData sits between SAP and AWS middleware.
2. **OAuth 2.0 and OIDC.** JD: "authorization code, client credentials." Resource: OAuth 2.0 Simplified (oauth.net) by Aaron Parecki. Self-check: whiteboard both flows, name where tokens live, and explain why client credentials fits SAP-to-AWS machine integrations.
3. **API contract testing with Postman or Bruno.** Resource: Postman Learning Center (free). Self-check: build a small collection against a public API with auth, environment variables, and response-assertion tests in 30 minutes.
4. **Finance vocabulary (AP, AR, GL, reconciliation, variance).** Resource: free "Financial Accounting" fundamentals on Coursera audit track or Corporate Finance Institute's free accounting guides. Self-check: define GL posting, three-way match, and month-end reconciliation, and tie each to an automation opportunity.
5. **AWS Step Functions + DynamoDB + API Gateway basics.** Resource: AWS free workshops (Step Functions workshop, serverless-workshops). Self-check: describe a state machine that calls a (mock) SAP OData endpoint, retries, and writes to DynamoDB.

## Tier 2 - before the technical round (week 2-5)

1. **AWS CDK in Python.** JD wants IaC "in a team setting"; Terraform is never-claim, so CDK is the compliant path. Artefact: a public GitHub repo deploying a Lambda + API Gateway + DynamoDB stack with beta/gamma/prod stages and a CI/CD pipeline (she has CI/CD), README explaining IAM roles and VPC choices.
2. **MCP server from scratch.** JD: "MCP (Model Context Protocol) servers." Artefact: a small MCP server (Python) exposing finance-reconciliation tools to a Claude client, with a written walkthrough of the protocol's tools/resources model.
3. **Bedrock agents / agentic workflow.** She has LangChain — port the mental model. Artefact: a notebook + repo where a Bedrock (or local-LLM fallback, she runs Ollama) agent automates a variance-analysis task over CSV ledgers, with tool-calling traces shown.
4. **Data pipeline design: SAP → Redshift shape, without claiming Redshift.** Learn Redshift concepts (distribution keys, COPY, Spectrum) to discuss the JD's pipeline requirement conceptually only. Artefact: a written architecture walkthrough (markdown, diagrams) of moving financial extracts from an OData endpoint through S3 into a columnar warehouse, explicitly framed as a design study.
5. **Stakeholder translation practice.** JD: "translate business requirements into technical solutions." Artefact: a one-page requirements-to-design memo for the reconciliation use case, written as if for a Finance stakeholder — doubles as interview prep material.

## Build-now project (only if the JD needs a project type she has none of)

**"SAP-meets-AWS" agentic finance integration — not built yet.** None of her projects is an ERP-to-cloud integration or a production-style agentic automation; the JD centers exactly that.
- Goal: simulate the role's core pattern end-to-end at hobby scale.
- Data: synthetic general-ledger/AP records (extend her Expense Tracker dataset with vendor invoices and PO numbers).
- Stack: Flask mock "SAP" OData API (she has Flask) → AWS Lambda + Step Functions + DynamoDB + S3, all deployed via CDK (Python) with CI/CD; MCP server exposing reconciliation tools to a Claude/Bedrock agent.
- Agent task: automated three-way-match reconciliation and variance flagging with a human-readable report.
- Evaluation: match rate on 200 seeded transactions, with injected mismatches caught; OAuth 2.0 client-credentials auth on the mock API.
- Deliverable: public repo, architecture diagram, 10-minute demo video, design memo.
- Hours: ~40-50 over weeks 2-5. Covers Tier 2 items 1-3 and 5 in one build.

## Honest answers for the structural gaps

- **SAP (4+ years ABAP/CDS/RAP/OData):** "I want to be upfront: I haven't worked inside SAP — my background is Python and AWS data and ML systems. I've been studying how CDS views, RAP, and OData fit together so I understand what I'd be building against, and my AWS and API experience maps directly onto the cloud half of this role, but the SAP-side depth would be a genuine ramp for me."
- **Finance domain:** "I'm not an accountant, but I've learned the AP/AR/GL vocabulary and built a reconciliation automation prototype, so I understand the workflows Finance teams care about and I know the questions to ask them."

## When this may go on the resume

Only after a skill is actually learned AND written into data/context/, then re-registered — never before.
