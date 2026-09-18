"""
End-to-end scan in no-key mode.

This is the "does the product work with zero configuration" check:
real sources -> dedupe -> filters -> sponsorship gate -> never-re-apply ->
link check -> score -> SUMMARY.md.

Run: python dashboard/tests/probe_scan.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import db, paths, settings  # noqa: E402
from backend.orchestrator import events, runner  # noqa: E402


async def main() -> None:
    db.init()
    cfg = settings.get_settings()
    cfg.verify_links = False          # keep the probe fast; exercised separately
    cfg.default_job_count = 8

    run = runner.Run({"count": 8})
    runner.RUNS[run.id] = run

    async def watch() -> None:
        async for ev in events.subscribe(run.id):
            if ev["type"] == "stage_started":
                print(f"  > {ev['message']}")
            elif ev["type"] == "stage_finished":
                tag = "SKIP" if ev["data"].get("skipped") else "done"
                ms = ev["data"].get("duration_ms")
                print(f"    [{tag}] {ev['message']}" + (f"  ({ms}ms)" if ms else ""))
            elif ev["type"] == "eta":
                print(f"    ETA: {ev['message']}")
            elif ev["type"] in ("error", "quota_wait"):
                print(f"    !! {ev['message']}")
            elif ev["type"] == "run_finished":
                print(f"\nFINISHED: {ev['data'].get('status')} in {ev['data'].get('duration_s')}s")
                return

    watcher = asyncio.create_task(watch())
    await run.execute()
    await asyncio.wait_for(watcher, timeout=10)

    print("\n" + "=" * 74)
    print(f"found={run.counts.get('found')} kept={run.counts.get('kept')} "
          f"excluded={run.counts.get('excluded')}")

    print("\nTOP RESULTS (tier first, then score):")
    for i, s in enumerate(run.scored[:8], 1):
        print(f" {i}. [{s.sponsor.tier.value}] {s.score.total:5.1f}  "
              f"{s.job.company[:24]:24s} {s.job.role_title[:38]:38s} {s.recommendation}")
        print(f"       skill={s.score.skill_match:5.1f} comp={s.score.competition:5.1f} "
              f"co={s.score.company_profile:5.1f} recency={s.score.recency:5.1f}")
        print(f"       why : {s.score.evidence.get('skill_match','')[:90]}")

    print("\nEXCLUSIONS (each must carry the sentence that caused it):")
    from collections import Counter
    by_stage = Counter(e.stage for e in run.excluded)
    print("  by stage:", dict(by_stage))
    shown = 0
    for e in run.excluded:
        if e.stage == "sponsorship" and shown < 3:
            print(f"  - {e.company[:22]} / {e.role_title[:34]}")
            print(f"      why : {e.why}")
            print(f"      said: {(e.triggering_sentence or '')[:100]!r}")
            shown += 1

    print("\nARTIFACTS:")
    print("  SUMMARY.md        ", paths.SUMMARY.exists(), paths.SUMMARY.stat().st_size, "bytes")
    print("  applications.tsv  ", paths.APPLICATIONS_TSV.exists())
    print("  scan-history.tsv  ", paths.SCAN_HISTORY.exists())
    print("  applied-companies ", paths.APPLIED_COMPANIES.exists())


if __name__ == "__main__":
    asyncio.run(main())
