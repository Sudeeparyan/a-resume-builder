# Study plan for Bosch - Associate Motorsport Software Engineer

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill | Bucket | Why the JD wants it |
|---|---|---|
| Python, C#, SQL, MongoDB, SQL Server | Have | "programming or scripting languages, such as Python, MATLAB, or C#"; "SQL Server, MongoDB, or InfluxDB" |
| MQTT, Grafana, Docker, Linux, AWS | Have | "Microsoft Azure, AWS, Kubernetes, MQTT, and Grafana"; "Linux or Windows command-line" |
| Embedded C, SPI/I2C/UART, test automation, V&V | Have | "embedded systems"; "Validate... requirements" |
| MATLAB | Learnable (3-6 wks) | named first in scripting languages |
| OSI / TCP-IP models, TCP/UDP/Ethernet/Wi-Fi/cellular | Learnable | "network communication frameworks, including the OSI and TCP/IP models" |
| CAN protocol | Learnable | "automotive communication protocols such as CAN and Ethernet" |
| Wireshark | Learnable | "diagnostic, or test tools such as Wireshark" |
| InfluxDB | Learnable | named time-series database for telemetry data |
| Reading electrical schematics | Learnable | "read and interpret electrical schematics" |
| HIL bench testing | Learnable concepts; real rig time structural | "Hardware-in-the-Loop (HIL) bench tests" |
| Professional/collegiate motorsport experience | Structural | "Experience in professional motorsport, significant collegiate racing (e.g., Formula SAE, EcoCAR)" |
| 1+ yrs industry application engineering | Structural | Required qualification; only real time counts |
| Powertrain / vehicle-level diagnostics depth | Structural (basics learnable) | "internal combustion, hybrid, and/or battery-electric vehicle systems" |
| Kubernetes | Never-claim | JD names it; on her never-claim list — learn privately if desired, never claim |

## Tier 1 - before the screening call (week 1-2)

1. **OSI and TCP/IP models, TCP vs UDP** (JD: "OSI and TCP/IP models... TCP, UDP"). Learn the 7/4 layers, handshake vs datagram tradeoffs, why telemetry often rides UDP. Resource: Practical Networking's free YouTube "Networking Fundamentals" playlist. Self-check: in 30 minutes, draw both models from memory and explain aloud when UDP beats TCP for race telemetry.
2. **CAN bus fundamentals** (JD: "CAN"). Frame anatomy (ID, DLC, payload), arbitration, bit rates, OBD-II vs raw CAN. Resource: CSS Electronics' free "CAN Bus Explained" intro series. Self-check: hand-decode three sample CAN frames and say which node wins arbitration and why.
3. **Wireshark basics** (JD: "tools such as Wireshark"). Capture filters, display filters, TCP handshake and retransmission spotting. Resource: official Wireshark sample captures at wiki.wireshark.org/SampleCaptures plus the user guide. Self-check: capture 5 minutes of local traffic, isolate a full TCP handshake, flag one retransmission, explain it.
4. **MATLAB fundamentals** (JD lists MATLAB first among languages). Arrays, plotting, data import, scripts vs functions. Resource: free MATLAB Onramp (MathWorks, ~2 hours). Self-check: load a CSV of sensor data, clean it, plot two channels, compute basic stats — timed, 30 minutes.
5. **Telemetry vocabulary + honest self-positioning** (JD: "telemetry gateway units", "trackside telemetry servers"). Learn the end-to-end path: ECU → CAN → gateway → radio/cellular → server → dashboard. Resource: Bosch Motorsport's public telemetry product pages. Self-check: deliver a 2-minute verbal walkthrough of that chain, ending with one honest sentence on where she personally stands.

## Tier 2 - before the technical round (week 2-5)

1. **Simulated CAN telemetry pipeline.** Use python-can with a virtual CAN interface to generate frames (rpm, speed, temps), publish over MQTT (registered), visualize in Grafana (registered). Artefact: a small public repo with README, docker-compose, and screenshots — a miniature of the JD's "telemetry gateway... data collection, analysis, and distribution."
2. **InfluxDB depth** (JD names it). Time-series schema, tags vs fields, retention, Flux queries. Artefact: extend the same repo to log the simulated CAN stream into InfluxDB, with a notebook comparing query patterns against her registered MongoDB approach.
3. **Networking troubleshooting walkthrough** (JD: "wired and wireless... Wi-Fi, and cellular"). Latency/packet-loss diagnosis with ping, traceroute, Wireshark; Wi-Fi vs cellular link budget intuition. Artefact: a written walkthrough of diagnosing a staged flaky-connection scenario, with captures attached.
4. **HIL-by-analogy bench rig** (JD: "HIL bench tests"). ESP32 (registered) as a stand-in ECU emitting sensor data; a Python test harness injecting faults and asserting behavior. Artefact: repo plus a one-page test report written like a V&V record — honest framing as a bench-test exercise, not real HIL.
5. **Vehicle systems literacy** (JD: "powertrain, chassis, or controls"). ICE vs hybrid vs BEV architecture at block-diagram level; how PID control (registered) maps to throttle/boost control. Resource: free chapters of the SAE "Automotive Engineering Fundamentals" summaries and Bosch's public mobility explainers. Artefact: a short written walkthrough connecting a control loop from her Elevator Control System project to an automotive control problem.

## Honest answers for the structural gaps

- **Motorsport experience:** "I haven't raced or been on a Formula SAE team — I won't pretend otherwise. What I bring is embedded systems and real-time telemetry work, and since applying I've built a simulated CAN-to-Grafana pipeline so I can be useful trackside faster."
- **Industry application engineering year:** "My application-engineering exposure so far is academic and project-based — requirements, bench testing, and customer-style documentation — and I'm looking for this role to be where I convert that into industry experience."
- **HIL hardware time:** "I've practiced the closed-loop test discipline on a bench rig I built myself; real HIL rigs are exactly what I'm here to learn on."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — never before, and Kubernetes never.
