# Study plan for Verkada - Software Engineer - Imaging Systems

**The wall:** every skill below is one Annie does not have yet. It never appears on the resume in any form until it is learned and written into data/context/.

## Demand map

| Skill (JD wording) | Bucket | Why the JD wants it |
|---|---|---|
| C++, C, "systems programming" | Have | "primarily in C++ and C" across the imaging stack |
| Embedded Linux / IoT on-device software | Have (Embedded C, FreeRTOS, Linux, ESP32) | "on-device software for IoT systems or embedded Linux environments" |
| Computer vision collaboration | Have (Object detection/tracking, YOLO, PyTorch) | "partnering closely with ... computer vision teams" |
| 3A algorithms: AE, AF, AWB | Missing - learnable | Core of the role: "autofocus, auto-exposure, image quality" |
| ISP algorithms, image sensors, optics | Missing - learnable (fundamentals in 3-6 wks) | "Working knowledge of optics, image sensors, ISP algorithms" |
| WDR, day/night transition | Missing - learnable | Named camera features she must discuss |
| Objective/subjective IQ evaluation (noise, sharpness, color) | Missing - learnable | "evaluate image quality both objectively and subjectively" |
| Sensor drivers / camera pipeline config (V4L2, MIPI CSI-2) | Missing - learnable (fundamentals) | "camera pipeline configuration, sensor drivers" |
| Vendor IQ tuning, production triage | Missing - structural | Real tuning-tool and field experience takes years; learn concepts only |
| "3+ years of software development experience" | Missing - structural | Cannot be learned; answer with project depth honestly |
| Onsite 5 days/week (San Mateo) | Structural (logistics) | Hard requirement, not a skill |
| Never-claim list | Never-claim | None of the never-claim skills appear in this JD; no conflict |

## Tier 1 - before the screening call (week 1-2)

1. **ISP pipeline overview** (Bayer, demosaic, black level, gamma, color correction) - react to "camera pipeline configuration". Resource: Raspberry Pi Camera Software libcamera docs (datasheets.raspberrypi.com). Self-check: draw the pipeline from photon to JPEG from memory in 30 min, label each block's failure mode.
2. **Auto-exposure fundamentals** (metering, exposure time vs gain, flicker). Resource: Cambridge in Colour "Camera Exposure" tutorial. Self-check: explain in 30 min why AE prefers gain over shutter at low light in security video, and what 50/60Hz flicker does to exposure steps.
3. **Autofocus types** (contrast-detection vs phase-detection, focus value curves). Resource: Cambridge in Colour autofocus tutorial. Self-check: sketch a contrast-AF hill-climbing search and name two ways it fails (low light, flat scenes).
4. **AWB basics** (gray world, white patch, color temperature). Resource: LearnOpenCV white-balance article (free). Self-check: explain why gray-world breaks on a single-color scene, in writing, 30 min.
5. **Vocabulary drill**: MIPI CSI-2, V4L2, WDR, ISP, IQ tuning, day/night IR-cut. Self-check: define each in one sentence and say honestly "I've studied this, not shipped it" for each.

## Tier 2 - before the technical round (week 2-5)

1. **Hands-on libcamera tuning** on a Raspberry Pi + camera module: edit the tuning JSON, capture before/after raw frames. Artefact: small repo with tuning file, paired images, and a README of what each change did.
2. **Implement a mini AE loop**: read raw frames (rawpy/libcamera), compute a metering statistic, adjust simulated exposure/gain to a target brightness. Artefact: Jupyter notebook with plots of convergence and a failure case (backlight).
3. **Implement AWB from scratch** (gray-world + white-patch) in Python or C++; compare against OpenCV's xphoto. Artefact: notebook with side-by-side images and a short write-up of when each method fails.
4. **Trace a real sensor driver**: read the Linux kernel imx219/imx477 V4L2 driver and the media-controller docs. Artefact: written walkthrough "how a frame gets from sensor to userspace on Linux," with the ioctl path annotated.
5. **Verkada-domain depth**: security-camera imaging constraints (low light, WDR scenes, IR day/night, edge AI on-device). Artefact: one-page written analysis of three hard imaging scenarios for security cameras and how 3A/ISP settings address each.

## Build-now project (only if the JD needs a project type she has none of)

She has embedded and CV projects but none on a camera imaging pipeline, so: **Mini ISP from raw sensor data** - *not built yet*. Goal: convert raw Bayer captures into viewable images with a self-built pipeline. Data: raw frames from a Raspberry Pi camera (DNG) or a public raw dataset. Stack: Python + NumPy for the pipeline (black-level, demosaic, AWB, CCM, gamma), C++ port of one hot path, libcamera for capture. Evaluation: objective metrics (SNR, color error vs a color-checker shot) plus subjective side-by-side against libcamera's own output. Deliverable: repo + notebook + one-page write-up. Hours: ~25-30 over weeks 3-5.

## Honest answers for the structural gaps

- **3+ years / vendor IQ tuning**: "My imaging work so far is academic and self-directed - I've built the pipeline pieces myself and tuned on real hardware, but I haven't done production IQ tuning with a sensor vendor. That part I'd be learning from the team, and it's exactly why I want this role."
- **Onsite**: "The onsite requirement works for me - I'm ready to be in San Mateo five days a week."

## When this may go on the resume

Only after a skill is genuinely learned, demonstrated in a project, and written into data/context/, then re-registered - never before.
