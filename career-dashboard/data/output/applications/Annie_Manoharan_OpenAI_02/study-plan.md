# Study plan for OpenAI - Software Engineer, Workload Enablement

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| PyTorch, Python | Have | "Strong hands-on experience with PyTorch and modern LLM training/inference stacks" |
| C++, Linux, Git | Have | "comfort reading/writing performance-critical code (C++/CUDA/HIP is a plus)" |
| Docker, CI/CD, test automation, Grafana | Have | "repeatable test harnesses that run in CI", "telemetry hooks" |
| Distributed training (data/model/pipeline parallel, collectives) | Learnable | "Large-scale distributed training concepts (data/model/pipeline parallel, collective comms)" |
| NCCL/RCCL concepts + tuning | Learnable (conceptual) | "Collective performance and tuning (across NCCL/RCCL and internal libraries)" |
| GPU profiling: Nsight, perf, flamegraphs, PyTorch profiler | Learnable | "Strong profiling/debugging skills ... ability to reason from traces/counters" |
| CUDA basics | Learnable (reading level) | "C++/CUDA/HIP is a plus"; kernel-level bottleneck analysis |
| RDMA / RoCE / NVLink concepts | Learnable (conceptual) | "Familiarity with RDMA networking and transport tuning" |
| Benchmark/stress-harness design | Learnable | "workload-shaped benchmarks and stress/fault tests that correlate to production behavior" |
| Kubernetes | Never-claim (learn basics only) | "running and validating workloads in Kubernetes" — never say she has it |
| 5+ yrs ML systems / HPC production | Structural | "5+ years in ... ML systems, performance engineering, distributed systems, or HPC" |
| Early-hardware lab bring-up (new NICs/GPUs/racks) | Structural | "Hands-on lab experience with early hardware" |
| BS in CS/EE | Have (education) | Degree held; not a gap |

## Tier 1 - before the screening call (week 1-2)

1. **Distributed training vocabulary**: data vs tensor vs pipeline parallelism, AllReduce/AllGather, gradient bucketing. Resource: PyTorch DDP tutorial (pytorch.org/tutorials). Self-check: explain in 5 minutes why AllReduce bandwidth, not FLOPs, bounds large-model scaling.
2. **NCCL fundamentals**: what collectives are, ring vs tree algorithms, what NCCL_DEBUG shows. Resource: NCCL documentation (docs.nvidia.com). Self-check: sketch how ring AllReduce moves data across 8 GPUs and name one topology factor that changes it.
3. **GPU profiling literacy**: Nsight Systems timeline vs Nsight Compute kernel metrics, what a flamegraph shows. Resource: PyTorch Profiler tutorial + Nsight Systems user guide. Self-check: profile a toy PyTorch training loop and identify the top kernel and one CPU-GPU sync stall.
4. **RDMA at concept level**: verbs, queue pairs, RoCE vs InfiniBand, why RDMA matters for collectives. Resource: "RDMA Aware Networks" intro posts + NVIDIA RoCE docs. Self-check: explain to a friend why TCP is too slow for NCCL and what congestion does to AllReduce.
5. **Honest self-positioning script**: one sentence per must-have stating what she has done vs only studied. Self-check: say each aloud without overstating.

## Tier 2 - before the technical round (week 2-5)

1. **Multi-GPU training run**: DDP and FSDP on 2+ GPUs (rented cloud instance OK), measure scaling efficiency. Artefact: small repo with training script + README table of throughput vs GPU count.
2. **NCCL micro-benchmarks**: run NVIDIA nccl-tests (all_reduce_perf), vary message size and transport. Artefact: notebook plotting bandwidth curves with commentary on where topology shows up.
3. **Profiling deep-dive**: take an open-source LLM training step, capture Nsight Systems trace, find one comm/compute overlap opportunity. Artefact: written walkthrough with annotated timeline screenshots.
4. **Workload-shaped benchmark design**: study how MLPerf Training and nvbandwidth structure tests; write a design doc for a stress test that exercises compute + memory + network together, mirroring the JD's "capture real E2E behavior". Artefact: the design doc in the repo.
5. **Regression-detecting harness in CI**: extend item 1 so benchmark results run in CI and flag regressions (she has CI/CD and test automation — combine them). Artefact: repo with workflow file, pass/fail thresholds and a sample regression caught on purpose.

## Build-now project (not built yet)

JD needs a self-built benchmark/CI harness; her projects have none. Spec: Goal — repeatable GPU benchmark + regression harness for a small PyTorch training workload. Data — synthetic tokens + a public tiny model (e.g., GPT-2-small config). Stack — PyTorch DDP, NCCL, Docker, GitHub Actions (no Kubernetes: never-claim). Evaluation — tokens/sec, AllReduce bandwidth, memory bandwidth; fail on >3% regression vs baseline. Deliverable — public repo: harness code, CI workflow, results notebook, one-page writeup of a found bottleneck. Hours — ~40 over weeks 2-5. This is also Tier 2 items 1+5 merged; label it "not built yet".

## Honest answers for the structural gaps

**5+ years ML systems/HPC:** "My production depth is in data and CV pipelines plus embedded/FPGA work, not five years of ML systems — but that hardware-plus-software background is exactly why porting workloads and reading traces across the stack is how I already think."

**Early-hardware lab work:** "I haven't brought up unreleased racks, but I've debugged against bare hardware — FPGA boards, microcontrollers, AXI interfaces — where the datasheet is wrong and you bisect with counters. I know how to write a minimal repro and a bug report a vendor can act on."

**Kubernetes (never-claim):** "I haven't run production Kubernetes; I know the concepts and have containerized workloads with Docker — I'd ramp on your K8s integration fast, but I won't pretend it's deep today."

## When this may go on the resume

Only after a skill is learned AND written into data/context/, then re-registered — never before.
