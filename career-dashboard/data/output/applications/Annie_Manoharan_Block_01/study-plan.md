# Study plan for Block - Software Engineer, Reconciliation & Reporting

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, Java, SQL | Have | "Proficiency in at least one major programming language (e.g., Java, Python, Go) and solid SQL" |
| Airflow, Spark/PySpark, Kafka, ETL | Have | "batch- or event-driven data pipelines... workflow-orchestration (e.g., Airflow, Temporal, Spark)" |
| Delta Lake, AWS, CI/CD, testing, observability | Have | "cloud data warehouses... Delta Lake, Kafka"; "CI/CD, and observability" |
| Bachelor's degree | Have | JD requires a technical degree or equivalent; she holds degrees |
| Payments lifecycle: authorization, clearing, settlement, ISO-8583, card-network file formats | Missing, learnable | "Familiarity with the payments ecosystem... card-network settlement file formats, or ISO-8583" |
| Double-entry bookkeeping, reconciliation concepts | Missing, learnable | "Understanding of accounting principles, double-entry bookkeeping, and financial reconciliation processes" |
| Tax/regulatory reporting vocabulary: 1099 family, CESOP, AML/KYC, TIN validation | Missing, learnable | "US IRS information returns (the 1099 family...) and international regimes such as EU-wide CESOP" |
| Temporal | Missing, learnable | Listed beside Airflow, which she has; concepts transfer |
| 3+ years professional experience | Structural | "3+ years of professional software or data engineering experience" |
| Production payments/financial-systems experience | Structural | "Exposure to financial, tax, regulatory, or payments reporting" (nice-to-have, but probed) |
| Snowflake, BigQuery, Hadoop | Never-claim | Nice-to-have list; on her never-claim list — may be learned later, never asserted now |
| Kubernetes, Terraform | Never-claim | "Exposure to cloud platforms (AWS, Kubernetes) and infrastructure-as-code (Terraform)" — never-claim list |

## Tier 1 - before the screening call (week 1-2)

1. **Payments lifecycle vocabulary** — Learn the money path the JD describes: merchant, acquirer, card network, issuer; authorization vs. clearing vs. settlement. Resource: Stripe's free "Payment lifecycle" and card-payments documentation. Self-check (30 min): on one blank page, draw and narrate the path of a $50 card payment from tap to merchant payout, naming each party and file handoff.
2. **Card-network settlement files and ISO-8583 basics** — Learn what a Visa/Mastercard settlement/report file contains (record types, amounts, fees, reconciliation totals) and what ISO-8583 messages look like (MTI, data elements). Resource: the open-source jPOS documentation and its ISO-8583 tutorial. Self-check: explain fields 2, 4, and 39 and why a settlement file's control totals matter.
3. **Double-entry bookkeeping and reconciliation** — Learn debits/credits, journals, ledgers, and what "reconciling two data sources" means operationally (matching, exceptions, breaks, aging). Resource: AccountingCoach's free double-entry and bank-reconciliation modules. Self-check: write the journal entries for a merchant sale minus processing fee, then define three ways two ledgers can disagree.
4. **Regulatory reporting vocabulary** — Learn what a 1099-K is, who receives it and why, what CESOP requires of payment processors in the EU, and where AML/KYC and TIN validation fit. Resource: IRS.gov pages on Form 1099-K and TIN matching; the EU Commission's CESOP overview. Self-check: in five sentences each, explain 1099-K and CESOP to a hypothetical finance partner.

## Tier 2 - before the technical round (week 2-5)

1. **Reconciliation matching engine design** — Go deep on matching algorithms: one-to-one, many-to-one, tolerance windows, exception queues. Artefact: a notebook reconciling two synthetic CSV "ledgers" (internal transactions vs. a mock network settlement file), producing a breaks report with aging. Public repo, README explaining design choices.
2. **Exactly-once semantics and idempotency in pipelines** — The JD stresses "accurate, reliable, timely" at payments scale; learn idempotent writes, dedup keys, replay strategies in Kafka/Spark (she has both; this is depth, not breadth). Artefact: a short written walkthrough in the repo showing how the pipeline survives a double-delivered file without double-counting money.
3. **Temporal vs. Airflow mental model** — JD names Temporal; she knows Airflow. Resource: Temporal's official docs and free "Temporal 101" course. Artefact: a one-page comparison doc plus a tiny Temporal workflow (hello-reconciliation) in the repo.
4. **Observability and auditability for financial data** — Learn lineage, data-quality checks, and what "end-to-end traceability of money" demands (immutable logs, reconciliation dashboards). Artefact: extend the project with a small Grafana/streamlit-style metrics page or markdown dashboard showing match rates, exception counts, and pipeline run history.
5. **AI-assisted development judgment** — The JD explicitly asks for "Proficiency in using AI tools... with the judgment to recognize where output needs additional validation." Artefact: a short repo note documenting where AI was used in the project and how each suggestion was validated (tests, review, experiments).

## Build-now project (only if the JD needs a project type she has none of)

**Not built yet.** Mini reconciliation and reporting pipeline (she has no reconciliation/financial-reporting project type).
- Goal: reconcile mock card-network settlement files against internal transaction records and emit standardized journals.
- Data: self-generated synthetic CSVs — internal payments table plus a Visa-style settlement file with deliberate mismatches (missing, duplicated, amount-drifted rows).
- Stack: Python, PostgreSQL, Airflow for orchestration, PySpark optional for scale demo; plain CI via GitHub Actions.
- Evaluation: match rate, exception count, break aging; journals must tie to control totals to the cent.
- Deliverable: public repo with README, architecture diagram, tests, sample outputs, and a 5-minute walkthrough write-up.
- Hours: ~35-45 over weeks 2-5.

## Honest answers for the structural gaps

- On experience: "I meet the technical bar through my project and research work, and I'm upfront that my professional tenure is shorter than three years — I've compensated by owning pipelines end-to-end, from design to operation, and I'd bring that same ownership here."
- On payments domain: "I haven't worked in payments production systems yet. I've studied the settlement lifecycle and reconciliation mechanics specifically for this team, and I learn domain context fast — my data-engineering fundamentals transfer directly."

## When this may go on the resume

Only after a skill above is genuinely learned AND written into data/context/, then re-registered — never before.
