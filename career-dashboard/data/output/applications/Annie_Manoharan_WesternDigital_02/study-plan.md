# Study plan for Western Digital - Software Engineer

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| Python, C, C++, Java, SQL | Have | "one or more programming languages such as C, C++, Python, Java... SQL" |
| Git, Linux, IDEs | Have | "common software development tools (such as Git, Linux, or IDEs)" |
| Data structures, algorithms, debugging, OS concepts | Have | "software development fundamentals, debugging, data structures, algorithms, operating systems" |
| Data pipelines, ETL, automation | Have (Spark, Kafka, Airflow, Flink, AWS Glue) | "Design and develop data pipelines... automation tools for collecting, processing, and analyzing data" |
| Embedded/firmware (C, FreeRTOS, SPI/I2C/UART) | Have | "Write software using C, C++... low-level programming languages" |
| Dashboards, reports, visualizations | Missing, learnable (she has Streamlit + Grafana as base; Tableau/Power BI/Looker are never-claim) | "Create dashboards, reports, and visualizations that support decision-making" |
| Stakeholder translation | Missing, learnable | "Partner with stakeholders to understand business needs and translate them into technical solutions" |
| Storage / semiconductor domain knowledge | Missing, learnable | "Interest in storage technologies, semiconductors... emerging technologies" |
| Data warehouse / dimensional modeling | Missing, learnable (Delta Lake/Databricks base) | "data pipelines, databases, and data warehouses" |
| Compilers / networking tools / "operating systems" internals | Missing, learnable (fundamentals only) | "Build or enhance operating systems, compilers, networking tools" |
| 0–2+ years professional experience | Structural — but the JD targets exactly this band | "aligned with candidates who have approximately 0–2+ years" |
| Degree requirement | Have (BE + MS; a held degree is never a gap) | "Bachelor's or Master's degree in CS... or a related technical field" |
| Go, Tableau, Power BI | Never-claim (Go appears in JD's language list; BI tools implied by "dashboards") — may be learned, never claimed | JD language list; visualization expectations |

## Tier 1 - before the screening call (week 1-2)

1. **WD domain vocabulary: NAND flash and SSDs.** Learn: how flash pages/blocks work, why writes erase-before-write, what an FTL (flash translation layer) does, HDD vs SSD product lines. Resource: WD's own "What is NAND flash" explainers and the SNIA education library (free). Self-check (30 min): explain out loud, unaided, why an SSD slows down as it fills, in 3 minutes.
2. **Dashboard thinking (never-claim tools stay out of mouth).** Learn: what a good operational dashboard contains — KPI choice, refresh cadence, drill-down. Resource: free chapters/articles at storytellingwithdata.com. Self-check: sketch on paper a 4-panel dashboard for monitoring a data pipeline and justify each panel.
3. **Stakeholder translation script.** Learn: the "business need → metric → technical spec" framing for her Medical IoT and expense-tracker projects. Resource: free Google Data Analytics capstone readings on stakeholder questions (Coursera audit). Self-check: write three STAR stories ending in a measurable outcome.
4. **OS internals refresh (system-tools track).** Learn: processes vs threads, virtual memory, syscall path — she has Multithreading, this is depth for questions. Resource: OSTEP (free, ostep.org), chapters on concurrency and memory. Self-check: answer "what happens on a context switch?" in writing, no notes.
5. **Data warehouse basics.** Learn: star schema, fact vs dimension, slowly changing dimensions — she has Delta Lake, this is modeling vocabulary. Resource: Kimball Group's free dimensional modeling design tips. Self-check: model "expense tracker" as one fact table + three dimensions on paper.

## Tier 2 - before the technical round (week 2-5)

1. **SSD write-path walkthrough.** Deep-dive FTL, garbage collection, wear leveling. Artefact: a two-page written walkthrough with a diagram, "What happens when you write 4 KB to an SSD," publishable as a repo README.
2. **C++ systems debugging at depth.** JD: "Troubleshoot, debug, and optimize software performance." Practice gdb, valgrind, perf on deliberately buggy C/C++. Artefact: small repo with a race-condition bug, its perf trace, and the fix, documented.
3. **End-to-end pipeline with a dashboard.** Extend her existing stack (Kafka/Spark → Delta Lake) with a Streamlit or Grafana front end — closes the "dashboards" gap using tools she may claim. Artefact: public repo, sample dataset, screenshot of a live dashboard with 4 KPIs.
4. **Dimensional warehouse mini-build.** Implement the Tier-1 star schema in SQL on Databricks Community Edition (free). Artefact: notebook showing schema, three analytical queries, and a one-paragraph design rationale.
5. **Mock screen rehearsal.** Record herself answering "Tell me about yourself," "Why Western Digital / why storage," and one project deep-dive. Artefact: one 5-minute recording reviewed against a checklist (JD keywords used, honest skill levels stated).

## Build-now project (only if the JD needs a project type she has none of)

Not required. The JD asks for pipelines, applications, embedded systems, and tools — her project list already covers IoT analytics streaming, an LLM application, FPGA/embedded work, and full-stack apps. The Tier-2 pipeline-plus-dashboard extension fills the only thin spot (business-facing visualization) without a new build.

## Honest answers for the structural gaps

- **0–2+ years experience:** "I'm at the very start of the band this role targets — my experience is graduate research and a dozen shipped projects, not production systems at a company yet. That's exactly why an early-career program with structured onboarding appeals to me."
- **No storage-industry background:** "I haven't worked in storage before, but my embedded and FPGA work taught me to think at the hardware-software boundary, and I've spent the last few weeks learning how NAND and SSD firmware actually work — happy to walk you through what I've learned."
- **Dashboards:** "My dashboarding so far is in Streamlit and Grafana rather than enterprise BI tools; the design thinking transfers and I'd ramp on your stack quickly."

## When this may go on the resume

Only after the skill is genuinely learned AND written into data/context/, then re-registered — never before.
