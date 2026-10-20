# Study plan for Chime Financial, Inc - AI/ML Engineer

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, SQL | Have | "Strong proficiency in Python and SQL" |
| PyTorch, deep learning | Have | "deep learning frameworks such as PyTorch" |
| Spark / PySpark | Have | "distributed compute such as Spark or PySpark" |
| Airflow, Kafka | Have | named under "modern ML infrastructure" |
| AWS (EC2, S3, Lambda, Glue, EMR) | Have | "AWS and tools such as…" |
| Docker, CI/CD, Flask | Have | supports "deployment… and an MLOps mindset" |
| Leakage, class imbalance, train/serve skew, label definition | Learnable (this plan) | "Comfort with messy real-world data, including label definition, leakage, class imbalance, and train/serve skew" |
| Monitoring, retraining, drift | Learnable (this plan) | "deployment, monitoring, and retraining" |
| Evaluation design / metric selection | Learnable (this plan) | "knowing which metric actually answers the question" |
| Experimentation / A/B testing | Learnable (this plan) | "use experimentation to prove impact" |
| Fraud/credit domain basics, explainability & fairness | Learnable (this plan) | Trust & Safety and Lending nice-to-haves |
| Snowflake | Never-claim (learn only) | named in JD infrastructure list |
| SageMaker | Never-claim (learn only) | named in JD infrastructure list |
| Redis | Never-claim (learn only) | named in JD infrastructure list |
| Years of production DL at millions-of-users scale | Structural | "Experience building and deploying deep learning models in production" |
| Publication record (Foundation Models) | Structural | "applied research with a publication record" |

## Tier 1 - before the screening call (week 1-2)

1. **Train/serve skew and leakage vocabulary.** Learn the canonical failure modes and how features pipelines prevent them. Resource: Google ML Crash Course, "Production ML Systems" section. Self-check: explain, in 5 minutes, three ways leakage enters a fraud model and how you'd detect each.
2. **Class imbalance and metric choice.** Precision/recall tradeoffs, PR-AUC vs ROC-AUC, thresholding. Resource: scikit-learn imbalanced-learn user guide. Self-check: given 0.1% fraud rate, argue in writing why accuracy is useless and pick a metric.
3. **Monitoring and retraining fundamentals.** Data drift, concept drift, retraining triggers. Resource: Evidently AI docs (open-source drift monitoring). Self-check: sketch a monitoring dashboard for a deployed model — 5 metrics, one alert rule each.
4. **Experimentation basics.** A/B test design, novelty effects, guardrail metrics. Resource: Trustworthy Online Controlled Experiments (chapter summaries via exp-platform.com notes). Self-check: design an A/B test for a new credit-limit model in 10 bullet points.
5. **Snowflake/SageMaker/Redis concepts — learn, never claim.** Read Snowflake's architecture overview, SageMaker's pipeline concepts, and Redis's caching role in real-time inference, so you can discuss them as "I've studied these; my hands-on work is on AWS core, Airflow, and Kafka." Self-check: explain where each sits in Chime's stack in one sentence.

## Tier 2 - before the technical round (week 2-5)

1. **Feature pipeline with leakage-safe design.** Build a batch feature pipeline in PySpark with point-in-time joins. Artefact: GitHub repo with a README walkthrough of one leakage bug you deliberately created and caught.
2. **End-to-end model monitoring demo.** Train a classifier, simulate drift, detect it. Artefact: Jupyter notebook with Evidently reports before/after drift, plus a written retraining policy.
3. **Class imbalance on a fraud-like dataset.** IEEE-CIS fraud data; compare PR-AUC across sampling strategies. Artefact: notebook with a metric-selection argument written for a non-technical PM.
4. **Real-time inference path.** Extend her Kafka/Flink experience into model serving: Flink SQL feature computation feeding a PyTorch model. Artefact: small repo, docker-compose, latency numbers documented.
5. **Lending explainability & fairness.** SHAP on a credit dataset, plus a fairness check (demographic parity gap). Artefact: written walkthrough titled "How I'd explain and audit a credit model" — directly answers the Lending nice-to-have.

## Build-now project (only if the JD needs a project type she has none of)

She has no end-to-end *production-style* ML project with monitoring and retraining; the JD demands exactly that. **Fraud detection system, "not built yet":** Goal — end-to-end fraud classifier on IEEE-CIS data, framed like Chime Trust & Safety. Data — IEEE-CIS Fraud Detection (Kaggle). Stack — PyTorch + scikit-learn models, PySpark feature pipeline, Flask serving, Kafka for event stream, Airflow for scheduled retraining, Docker, Evidently for drift monitoring. Evaluation — PR-AUC at fixed false-positive rate, documented leakage audit, drift-detection demo. Deliverable — public repo with architecture diagram, README, and a 2-page writeup connecting model metrics to business outcomes (false-decline cost vs fraud loss). Hours — ~40 over weeks 2-5.

## Honest answers for the structural gaps

- Production DL at scale: "I've built and deployed deep learning models in research and personal projects, and I've studied how production ML systems fail and recover. I haven't yet owned a model serving millions of users — that's exactly what I want to learn here, and I've spent the last month building a monitored, retraining-capable system to close that gap deliberately."
- Publication record: "I don't have publications; my research work in the AICV lab was applied. I'm strongest on the applied engineering side, so Trust & Safety or Lending is likely a better match than Foundation Models."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
