"""
Build a resume for three different job types and show what was chosen.

Run: python dashboard/tests/probe_build.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import paths  # noqa: E402
from backend.agents import builder  # noqa: E402
from backend.models import JobPosting  # noqa: E402

CASES = {
    "streaming-data": (
        "Required: Apache Kafka, Apache Flink, SQL, Python. Requirements: build ETL "
        "pipelines, ClickHouse OLAP store, Grafana dashboards, medical device telemetry, "
        "low-latency streaming, data quality validation, AWS Glue, Airflow orchestration."
    ),
    "computer-vision": (
        "Requirements: PyTorch, computer vision, object detection and tracking, deep "
        "learning research, keypoint estimation, LSTM sequence models, Python."
    ),
    "embedded-test": (
        "Required: Embedded C, PIC microcontrollers, FPGA Vivado, MicroBlaze, hardware "
        "validation, test automation, LabVIEW, NI TestStand, medical device V&V."
    ),
}


async def main() -> int:
    failures = 0
    for name, jd in CASES.items():
        job = JobPosting(
            source="probe", source_id=name, company=f"Acme {name}",
            role_title="Engineer", url="https://example.com", jd_text=jd,
        )
        r = await builder.build(job, resume_id=f"probe-{name}")
        fit = r.report["fit"]
        ok = fit["pages"] == 1 and r.guards.ok
        failures += 0 if ok else 1

        print(f"\n{'=' * 70}\n{name.upper()}   pages={fit['pages']} chars={fit['chars']} "
              f"track={r.report['track']} signature={r.report['signature_project']} "
              f"guards_ok={r.guards.ok}")
        print(f"  fit: {fit['note']}")

        body = r.tex.split("\\begin" + "{document}")[-1]
        for line in body.splitlines():
            t = line.strip()
            if t.startswith(("\\section", "\\resumeSubheading", "\\resumeSingleHeading")):
                print("   ", t[:110])
            elif t.startswith("\\resumeItem{"):
                print("        -", t[12:-1][:96])

        out = paths.TMP / f"probe-{name}.tex"
        out.write_text(r.tex, encoding="utf-8")

    print(f"\n{'=' * 70}")
    print("PASS — every build is one page and passes the guards" if not failures
          else f"FAIL — {failures} build(s) had problems")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
