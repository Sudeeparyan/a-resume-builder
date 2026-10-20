# Study plan for BD - Engr 3, Hardware Test

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| LabVIEW programming ("Strong LabVIEW programming background") | Have | Core automation tool for DAQ and test sequences |
| NI TestStand / test automation | Have | Automated sequences and benchmark programs |
| Python, SQL ("Programming or scripting experience") | Have | Data aggregation, trending, reporting |
| Arduino / microcontrollers, SPI/I2C/UART, PID control | Have | "Improve or develop PLC- and microcontroller-based systems" |
| Verification and validation (V&V) | Have | PQPs, verification protocols |
| DOE ("full/fractional factorial, screening, response surface") | Missing, learnable | Characterize system performance, set design margins |
| ANOVA, regression, capability analysis (Cp/Cpk), hypothesis testing | Missing, learnable | Analyze DOE results in "Minitab, Python, or JMP" |
| MSA / Gage R&R ("Demonstrated experience... Gage R&R") | Missing, learnable | Prove test methods are repeatable before studies |
| Weibull / life data analysis ("MTBF/MCBF, hazard and survival plots, censored data") | Missing, learnable | Quantify reliability growth in life testing |
| FMEA, fault tree, 5-Why, 8D | Missing, learnable | Failure analysis and root-cause investigation |
| PLCs, motion control, NI DAQ hardware | Missing, learnable (PLC/DAQ hardware) | "Integrated DAQ systems for sensors, motion control" |
| Reliability sample-size / confidence-level judgment | Missing, learnable | Defend test plans to stakeholders |
| "Minimum experience of 5 years in a similar role" | Missing, structural | Seniority requirement; cannot be learned in weeks |
| "Experience mentoring, coaching, or technically leading" | Missing, structural | This is an Engr 3 / mentor role |
| Hands-on electro-mechanical fixture design (CAD, 45-lb lab work, on-site 4 days/wk) | Missing, structural | Physical lab presence and mechanical build experience |
| Never-claim list | Never-claim | None of these appear in the JD; nothing to add. Nothing from this plan goes on the resume |

## Tier 1 - before the screening call (week 1-2)

1. **DOE vocabulary**: factors, levels, responses, blocking, randomization, full vs. fractional factorial, screening vs. response surface. Resource: NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 5. Self-check: in 30 min, design on paper a 2^3 factorial for motor-torque vs. temperature vs. duty cycle, name the aliasing risk in a half-fraction.
2. **Gage R&R / MSA**: repeatability vs. reproducibility, %study variation, crossed vs. nested. Resource: Minitab's free support pages on Gage R&R. Self-check: explain in 2 minutes why a bad measurement system invalidates a DOE, and what %GR&R threshold is acceptable.
3. **Weibull basics**: shape/scale parameters, beta interpretation, MTBF vs. MCBF, censored data. Resource: ReliaWiki (ReliaSoft's public wiki), Weibull analysis chapters. Self-check: sketch a hazard plot by hand and state what beta > 1 means for wear-out.
4. **FMEA / fault tree / 8D**: severity-occurrence-detection scoring, RPN, AND/OR gates. Resource: ASQ's free FMEA and 8D overview pages. Self-check: build a 5-row FMEA table for a syringe-pump jam failure.
5. **PLC and motion-control fundamentals**: ladder logic basics, stepper/servo control loops (she has PID — extend it). Resource: NI's free "DAQ and motion control fundamentals" tutorials. Self-check: describe how she'd automate cycle counting on a life-test stand.

## Tier 2 - before the technical round (week 2-5)

1. **DOE executed in Python** (JD allows "Minitab, Python, or JMP"): pyDOE3 + statsmodels ANOVA/regression on a simulated electro-mechanical response. Artefact: Jupyter notebook running a fractional-factorial DOE end-to-end with residual checks and capability output (Cp/Cpk).
2. **Weibull life-data analysis**: the `reliability` Python library on a censored dataset (generate or use public bearing-life data). Artefact: notebook producing Weibull fits, hazard/survival plots, MTBF with confidence bounds, and a one-page "reliability growth" memo.
3. **Gage R&R study**: design a crossed GR&R (3 operators x 10 parts x 3 trials) in Python, compute %GR&R and ndc. Artefact: script + written interpretation she could defend as an MSA plan.
4. **LabVIEW DAQ depth**: DAQmx acquisition with logging, fault detection, and unattended-run error handling; TestStand sequence calling it. Artefact: small LabVIEW/TestStand repo simulating an automated life-cycle test with cycle counting and a fault-injection demo.
5. **Medical-device V&V context**: how PQPs, traceability, and ISO 13485 / ISO 14971 shape test protocols at a company like BD. Artefact: 1-2 page walkthrough mapping a sample PQP to reliability tests, sampling plan, and acceptance criteria.

## Build-now project (only if the JD needs a project type she has none of)

She has no automated reliability/life-test project; the JD centers on one. **Not built yet.**
- Goal: desktop accelerated-life test stand for a small DC motor or solenoid.
- Data: cycle counts, current draw, temperature, vibration; run-to-failure with right-censoring.
- Stack: ESP32/Arduino rig control + sensors (she has these), LabVIEW or Python DAQ/logging, `reliability` library for analysis.
- Features: unattended run, automatic fault detection and shutdown, CSV logging.
- Evaluation: Weibull fit on failure data, MTBF with confidence interval, short FMEA of the rig itself.
- Deliverable: repo with wiring diagram, firmware, DAQ code, analysis notebook, 2-page test report.
- Hours: ~30-40 across weeks 2-5.

## Honest answers for the structural gaps

- 5 years: "I don't have five years in a dedicated test role. What I bring is hands-on LabVIEW, embedded, and Python automation, and I've spent the last month building exactly the reliability toolkit this role uses — I'd rather show you that work than stretch my history."
- Mentoring: "I haven't formally managed engineers, but I've taught teammates instrumentation and debugging informally, and the statistical-rigor coaching this role describes is something I've been preparing for deliberately."
- Fixture/CAD: "My strength is the automation and data side; mechanical fixture CAD is where I'd lean on your mechanical engineers early and learn fast."

## When this may go on the resume

Only after a skill is genuinely learned AND written into data/context/, then re-registered — never before.
