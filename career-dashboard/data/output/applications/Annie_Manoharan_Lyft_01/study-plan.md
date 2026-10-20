# Study plan for Lyft - Machine Learning Engineer

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| "Proficiency in Python" | Have | Production code for models |
| "TensorFlow, PyTorch, or similar" | Have (PyTorch registered) | Deep learning for recommenders |
| "BS/MS in Computer Science" | Have (MS, University of Arkansas) | Baseline credential |
| Kafka/Spark/Flink-style data pipelines | Have (registered) | Adjacent to "feature pipelines" |
| "statistical concepts such as hypothesis testing, regression analysis, and performance evaluation metrics" | Missing, learnable | Model evaluation vs KPIs |
| "deep learning technologies for recommendation systems" | Missing, learnable | Core Fulfillment matching work |
| "run experiments… against business KPIs" | Missing, learnable | A/B testing culture |
| "feature pipelines, model training workflows, and serving infrastructure" | Missing, learnable (conceptually) | Day-one architecture literacy |
| "translating state-of-the-art ML research into production systems" | Missing, structural | Needs production tenure |
| "2+ years of experience in machine learning" | Missing, structural | Cannot be compressed |
| "Golang" | Never-claim (on her list) | JD says "Python, Golang, **or** other" — Python satisfies it |

## Tier 1 - before the screening call (week 1-2)

1. **Statistics fundamentals** (JD: "hypothesis testing, regression analysis, performance evaluation metrics"). Learn: p-values, confidence intervals, Type I/II error, precision/recall/AUC, calibration. Resource: StatQuest video series (free, YouTube). Self-check: explain in 30 min, on paper, when precision beats recall for driver-rider matching, and what a p-value does *not* tell you.
2. **Recommender vocabulary** (JD: "deep learning technologies for recommendation systems"). Learn: candidate generation vs ranking, two-tower models, embeddings, negative sampling, NDCG/Recall@K. Resource: Google's free Recommendation Systems crash course (developers.google.com/machine-learning/recommendation). Self-check: whiteboard a two-tower architecture for matching riders to drivers in 30 min, including loss choice.
3. **A/B testing literacy** (JD: "run experiments, and drive continuous model improvement"). Learn: randomization, sample size, MDE, novelty effects, guardrail metrics. Resource: "Trustworthy Online Controlled Experiments" summary chapters / exp-platform.com free notes. Self-check: design an experiment for a new matching model — hypothesis, primary metric, guardrails, runtime — in 30 min.
4. **Fulfillment domain fluency** (JD: "generate feasible offers… match rider requests with drivers… distributed state machine"). Learn: marketplace dynamics, ETA/pricing/matching interplay, batching vs instant matching. Resource: Lyft Engineering blog (eng.lyft.com), matching and marketplace posts. Self-check: explain in 30 min why matching is a bipartite optimization and where ML enters.
5. **Production ML lifecycle vocabulary** (JD: "feature pipelines, model training workflows, and serving infrastructure"). Learn: offline/online feature skew, training-serving consistency, model monitoring. Resource: "Designing Machine Learning Systems" (Chip Huyen) — early chapters via O'Reilly trial or library. Self-check: draw the lifecycle of one model from feature to retraining in 30 min.

## Tier 2 - before the technical round (week 2-5)

1. **Recommender depth in PyTorch.** Build a two-tower retrieval model on MovieLens-25M with embeddings, sampled softmax, and ANN retrieval via FAISS (already registered). Artefact: public repo with training notebook and a README comparing Recall@10 across two architectures.
2. **Real-time serving design.** Study latency budgets, feature stores, online inference, fallbacks. Artefact: a written design doc (2-3 pages) for serving the matching model under 100 ms, with a Flask prototype endpoint (Flask is registered).
3. **Lyft's actual stack.** Lyft open-sourced its ML workflow platform Flyte; read its docs and Lyft eng posts on Fulfillment. Artefact: a one-page architecture summary of how Lyft trains and serves matching models, with citations — usable verbatim in "why Lyft" answers.
4. **Evaluation against KPIs.** Connect offline metrics (AUC, NDCG) to online KPIs (conversion, wait time, cancellation). Artefact: a notebook simulating an A/B readout on synthetic data — power calculation, uplift estimate, guardrail check.
5. **Streaming-adjacent refresh for the state machine question.** She has Kafka/Flink; map them to "distributed state machine to track rides." Artefact: a short walkthrough comparing event-sourced ride-state tracking with her Medical IoT streaming project (PROJ-P01) patterns.

## Build-now project (not built yet)

She has no recommendation-system project, so one is required.

- **Goal:** end-to-end two-sided recommender mimicking rider-driver matching.
- **Data:** MovieLens-25M (public) as proxy for user-item matching; optional synthetic ETA feature.
- **Stack:** PyTorch (registered), FAISS (registered), Flask for serving (registered), Docker (registered). No never-claim tools.
- **Model:** two-tower retrieval + lightweight ranking layer; sampled softmax loss.
- **Evaluation:** Recall@K, NDCG@10 offline; latency benchmark of the Flask endpoint.
- **Deliverable:** public repo, training notebook, 1-page evaluation writeup, architecture diagram.
- **Hours:** ~40-50 over weeks 2-5.

## Honest answers for the structural gaps

- **2+ years ML experience / research-to-production:** "My production experience so far is in data and streaming pipelines; my ML work is graduate research and project-based, which is why I built an end-to-end recommender before this call. I'm candid that this role would be my first production ML deployment, and I'd ramp with the team's platform rather than pretend otherwise."
- **Scale ("petabyte-scale data"):** "I've worked with streaming and distributed data systems, not petabyte-scale ML. I understand the patterns — partitioning, feature stores, online/offline skew — and I'd rather show you that understanding than claim scale I haven't run."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
