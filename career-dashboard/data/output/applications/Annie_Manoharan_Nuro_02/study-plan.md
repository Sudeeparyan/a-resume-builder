# Study plan for Nuro - Software Engineer, Onboard Platform

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill the JD names | Bucket | Why the JD wants it |
|---|---|---|
| Strong C++ | Have | "Must have strong C++ skills" — registered |
| Python / advanced algorithms | Have | "advanced algorithms using C++ and Python" — registered |
| Highly-concurrent, multi-threaded environments | Have | "highly-concurrent, multi-processor, and multi-threaded environments" — Multithreading registered |
| Operating systems / Linux, real-time | Have | "computer architecture and operating systems" — Linux, FreeRTOS registered |
| Robotics hardware, sensors, embedded platforms | Have | "robotics hardware components (including sensors, embedded platforms)" — Embedded C, ESP32, SPI/I2C/UART, PID control registered; FPGA Autonomous Vehicle and Elevator Control projects |
| FPGA / ARM / x86 compute modalities | Have (FPGA/ARM) | "different compute modalities (x86, ARM, GPU, FPGA)" — Xilinx Vivado, Verilog, MicroBlaze registered |
| Profiling & tracing tools (perf, eBPF, Perfetto, pprof, Nsight) | Missing, learnable | "profiling and tracing tools and infrastructure" — none registered |
| Software performance tuning & optimization | Missing, learnable | "software performance tuning and optimization" — core to the Performance team |
| Robotics software frameworks (ROS 2 / DDS) | Missing, learnable | "robotics software frameworks" — none registered |
| GPU compute (CUDA, Nsight profiling) | Missing, learnable | "compute modalities ... GPU"; "NVIDIA Nsight Systems/Compute" |
| Large-scale distributed systems | Concepts learnable; production scale structural | "large-scale distributed systems" — she has Kafka/Spark data systems but not onboard/vehicle-scale production work |
| 2+ years relevant industry experience | Missing, structural | "2+ years of relevant industry experience in addition to a Bachelor's Degree" |
| CS/EE/Robotics degree | Have | MS (University of Arkansas) — a degree is never a gap |
| React | Not demanded by this JD; also on never-claim list — ignore for this role | n/a |

## Tier 1 - before the screening call (week 1-2)

1. **Profiling vocabulary: perf and flame graphs.** The JD names perf and pprof explicitly. Learn what sampling profilers measure (on-CPU vs off-CPU time). Resource: Brendan Gregg's free perf examples page (brendangregg.com/perf.html). Self-check: in 30 minutes, explain aloud what a flame graph's width and stack depth mean and where perf's overhead comes from.
2. **Tracing basics: Perfetto and eBPF.** The JD lists both. Learn trace events vs sampling, and what eBPF programs can hook (syscalls, uprobes). Resource: perfetto.dev "Quickstart: record traces on Linux". Self-check: describe in 30 minutes how you'd trace a latency spike in a sensor pipeline and which tool you'd pick first.
3. **ROS 2 core model.** "Robotics software frameworks" almost certainly means ROS 2 with DDS under it. Learn nodes, topics, pub/sub, QoS, launch. Resource: docs.ros.org Humble "Beginner: CLI tools" tutorials. Self-check: whiteboard a camera-driver -> perception -> planning topic graph in 30 minutes, naming message types.
4. **GPU execution model.** Learn threads/blocks/warps, memory hierarchy, occupancy — enough to discuss "GPU" as a compute modality. Resource: NVIDIA's free "CUDA C++ Programming Guide", chapters 1-3. Self-check: explain in 30 minutes why a naive matrix multiply is memory-bound and what tiling fixes.
5. **Real-time latency vocabulary.** The Performance team owns "latency reduction". Learn priority inversion, preemption, deadline vs throughput thinking. Resource: the Linux Foundation's free "Intro to Real-Time Linux" reading (wiki.linuxfoundation.org/realtime). Self-check: in 30 minutes, give three concrete causes of jitter in an onboard pipeline and one mitigation each.

## Tier 2 - before the technical round (week 2-5)

1. **Perf + flame-graph lab on her own C++ code.** Take an existing C++ project, find one hot loop, fix it, measure again. Artefact: a small repo with before/after flame-graph SVGs and a README walkthrough of the diagnosis.
2. **Perfetto-instrumented pipeline.** Instrument a multi-threaded producer/consumer pipeline with trace events. Artefact: repo plus two trace screenshots with a one-page written analysis of where latency hides.
3. **ROS 2 mini onboard pipeline.** Two C++ nodes (simulated sensor publisher, consumer with processing), measured end-to-end latency under load. Artefact: repo with a latency histogram and a note on how QoS settings changed it.
4. **CUDA kernel study.** Naive vs tiled matrix multiply, profiled. Artefact: notebook/repo with runtime table and, if hardware allows, Nsight Compute output; otherwise nvprof-style timing plus explanation of the bottleneck.
5. **Cache/SIMD optimization walkthrough.** Optimize one numerical kernel (row-major vs column-major access, compiler auto-vectorization). Artefact: written walkthrough with benchmark numbers and Compiler Explorer links showing the generated assembly.

## Build-now project (only if the JD needs a project type she has none of)

Her projects are hardware/FPGA-side; she has no software robotics-framework project. Spec (**not built yet**):
- Goal: simulate an onboard sensor-to-decision pipeline like the Onboard Systems team runs.
- Data: synthetic camera-frame and IMU streams generated in-process (no dataset needed).
- Stack: C++17, ROS 2 Humble, DDS pub/sub, Perfetto tracing, perf for profiling.
- Behavior: driver node -> preprocessing node -> mock perception node, each with a latency budget.
- Evaluation: end-to-end p50/p99 latency under increasing load; one documented optimization that cuts p99.
- Deliverable: public repo with README, trace screenshots, flame graphs, and the latency report.
- Hours: ~40 over weeks 3-5.

## Honest answers for the structural gaps

- "2+ years of relevant industry experience": "I'm earlier in my industry career than the posting describes, but I've built real-time and autonomous systems end to end — an FPGA-based autonomous vehicle and embedded control systems — and I can show you profiled, measured C++ work from the last month. I'd rather demonstrate the depth than claim the years."
- "Large-scale distributed systems": "My production-scale experience is in data systems — Kafka, Spark, Flink pipelines — not vehicle fleets. The concepts transfer and I've been studying onboard architectures, but I won't pretend I've debugged a fleet-wide deployment."

## When this may go on the resume

Only after each skill is actually learned AND written into data/context/, then re-registered — never before.
