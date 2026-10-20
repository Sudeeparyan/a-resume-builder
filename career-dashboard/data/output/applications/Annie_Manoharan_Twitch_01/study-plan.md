# Study plan for Twitch - Applied Scientist

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, SQL | Have | "Expertise with: Python and SQL" |
| PyTorch / modern ML libraries | Have | "modern open source ML libraries (Pytorch, Tensorflow, etc.)" |
| AWS (EC2, S3, Lambda, Glue) | Have | "Developing software in AWS or similar cloud-computing services" |
| Computer vision, content understanding | Have | "experimenting with new techniques in LLM, computer vision, inference and model evaluation" |
| LLM model evaluation | Missing, learnable (3-6 wks) | "Experience with LLM model evaluations" — a hard requirement |
| LLM inference | Missing, learnable | Bonus: "Experience with computer vision, LLM inference, content understanding" |
| Statistics / experimentation | Missing, learnable | Implied by "model evaluation" and GTM Science's ads work |
| GTM domain: Ads, Brand Safety, Creator Sponsorship | Missing, learnable (vocabulary) | "ambiguous business problems across… Ads, Brand Safety, Creator Sponsorship" |
| Stakeholder communication | Missing, learnable | "working with both technical and non-technical partners and stakeholders" |
| 3+ years industry applied ML (Master's track) | Missing, structural | "3+ years of applied ML experience (Master's)" |
| Owning projects with numerous scientists/engineers | Missing, structural | "Experience owning projects that involve numerous scientists and engineers" |
| PhD specialization | Structural, bonus only | "Bonus Points: PhD" — her MS already satisfies the degree line |

No JD requirement touches her never-claim list (no SageMaker, MLflow, Kubeflow, dbt, etc. named).

## Tier 1 - before the screening call (week 1-2)

1. **LLM evaluation fundamentals** — the JD's "Experience with LLM model evaluations." Learn: task metrics (accuracy, F1, ROUGE, BERTScore), LLM-as-judge, human eval, golden datasets. Resource: Hugging Face Cookbook evaluation guide (huggingface.co/learn/cookbook, free). Self-check (30 min): explain in writing how she'd evaluate a stream-title classifier three ways, and when each fails.
2. **Statistics refresh: hypothesis testing & A/B tests** — the "statistics" gap. Learn: p-values, confidence intervals, power, novelty effects. Resource: StatQuest's "Statistics Fundamentals" playlist (free, YouTube). Self-check: design an A/B test for a new ad format on paper in 30 minutes, including sample-size reasoning.
3. **GTM vocabulary** — "Ads, Brand Safety, Creator Sponsorship and Content Understanding." Learn: CPM/CPC, viewability, brand-safety tiers, sponsorship measurement. Resource: Twitch Advertising's public product pages and the Twitch Blog (free). Self-check: explain to a friend in 30 minutes how Twitch makes money and where ML enters each revenue line.
4. **Stakeholder communication** — the "stakeholders" gap. Learn: framing results for non-technical partners (decision-first memos, uncertainty statements). Resource: Google's People + AI Guidebook, chapter on communicating ML (free). Self-check: write a one-page project brief for a brand-safety model, jargon-free, in 30 minutes.
5. **Twitch product fluency** — bonus: "Familiarity with Twitch, its business, and its community." Resource: Twitch Creator Camp + 3 recent engineering blog posts (free). Self-check: name five content-signal problems Twitch likely has, from the product itself, in 30 minutes.

## Tier 2 - before the technical round (week 2-5)

1. **Build an LLM eval harness.** Learn promptfoo's config, assertions, and model-graded evals (promptfoo.dev docs, free). Artefact: a public repo evaluating three prompt variants for a "brand-safe vs unsafe stream title" classifier, with a results table and a written failure analysis.
2. **Classical vs SOTA judgment** — "Know when to use a classical ML model versus a state-of-the-art one." Train logistic regression, then fine-tune a small transformer on the same text-classification set. Artefact: notebook comparing accuracy, latency, cost per 1k inferences, with a one-paragraph decision memo.
3. **LLM inference basics** — bonus "LLM inference." Learn batching, quantization, KV-cache, token-cost math via her existing Ollama/Llama 3.2 setup. Artefact: a benchmark notebook measuring latency/throughput at 3 quantization levels, with a cost extrapolation to Twitch-scale volumes.
4. **Experimentation depth.** Learn CUPED, multiple comparisons, guardrail metrics. Resource: "Trustworthy Online Controlled Experiments" summary notes + Khan Academy stats (free). Artefact: notebook simulating an A/A and A/B test on synthetic ad-click data, showing false-positive control.
5. **Multimodal content understanding.** Combine her CV strengths (YOLO, Res-UNet) with text: classify clips using thumbnail + title + transcript embeddings (FAISS, nomic-embed-text). Artefact: Streamlit demo repo classifying Twitch-category thumbnails with an embedding-similarity explainer.

## Build-now project (only if the JD needs a project type she has none of)

**Status: not built yet.** The JD wants "prototype and put them into production" applied to content signals — she has no LLM-evaluation/content-understanding project.
- Goal: brand-safety scoring service for live-stream metadata.
- Data: public Twitch category/thumbnail samples + self-written titles labeled by rubric.
- Stack: Python, PyTorch, Ollama (Llama 3.2), FAISS, Flask, promptfoo.
- Evaluation: golden set of 200 labeled titles; precision/recall per brand-safety tier; LLM-as-judge agreement score.
- Deliverable: repo with eval harness, API endpoint, README decision memo (classical vs LLM trade-offs).
- Hours: ~25 across weeks 3-5.

## Honest answers for the structural gaps

- **Years of industry applied ML:** "My applied ML work has been in research labs and personal production-style projects — gait assessment and virtual try-on in the AICV Lab — not three years in industry. What I can show is end-to-end ownership: data, modeling, evaluation, and deployment on each."
- **Owning multi-scientist projects:** "I haven't yet led a project staffed by multiple scientists. I have owned projects solo end-to-end and collaborated across hardware and software teams, and I'd be transparent that team-scale science leadership is the growth I want from this role."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
