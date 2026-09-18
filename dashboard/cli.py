#!/usr/bin/env python3
"""
Run the career workspace without opening anything.

    python dashboard/cli.py brief            the morning brief: find jobs, build resumes
    python dashboard/cli.py brief --count 5  fewer, or --no-resumes for a list only
    python dashboard/cli.py pack             rebuild the Claude/ChatGPT project pack
    python dashboard/cli.py schedule         print the Windows Task Scheduler command
    python dashboard/cli.py status           what is configured, and what ran last

This exists because the in-app scheduler only fires while the app is open. A
Task Scheduler entry calling `cli.py brief` runs at 09:00 whether or not she has
opened anything, which is the actual promise.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from backend import db, paths, settings  # noqa: E402


def _boot() -> None:
    paths.ensure_dirs()
    db.init()


async def _brief(count: int | None, build: bool) -> int:
    from backend.orchestrator import daily
    from backend.services import sponsor_index, workspace_sync

    sponsor_index.build()
    workspace_sync.bootstrap_tracker()
    workspace_sync.age_applications()

    print("Running the morning brief. This takes a few minutes.\n")
    s = await daily.run_brief(count=count, build_resumes=build)

    print(f"Found {s['found']} job(s) worth showing.")
    if s["built"]:
        print(f"Built {s['built']} resume(s):")
        for r in s["resumes"]:
            flag = "  (thin)" if r.get("short_of_target") else ""
            print(f"  - {r['company']:<28} {r['role_title'][:40]:<42} {r['folder']}{flag}")
    for p in s["problems"]:
        print(f"  ! {p['company']}: {p['why']}")
    print(f"\nOpen output/SUMMARY.md for the one page. Cost ${s.get('cost_usd', 0):.2f}.")
    return 0


def _pack() -> int:
    script = ROOT / "system" / "scripts" / "export_project_pack.py"
    return subprocess.call([sys.executable, str(script)])


def _schedule() -> int:
    py = sys.executable
    script = HERE / "cli.py"
    at = settings.get_settings().daily_at
    print("Run this once in PowerShell to have Windows fire the brief every day,")
    print("even with the app closed:\n")
    print(
        f'  schtasks /Create /SC DAILY /TN "CareerOps Morning Brief" '
        f'/TR "\\"{py}\\" \\"{script}\\" brief" /ST {at}\n'
    )
    print("To remove it:\n")
    print('  schtasks /Delete /TN "CareerOps Morning Brief" /F\n')
    print("On macOS or Linux, add this to `crontab -e` instead:\n")
    hh, _, mm = at.partition(":")
    print(f"  {int(mm or 0)} {int(hh)} * * *  {py} {script} brief\n")
    return 0


def _status() -> int:
    from backend import scheduler
    from backend.orchestrator import daily

    cfg = settings.get_settings()
    st = scheduler.status()
    print("Provider   :", cfg.llm_provider)
    if cfg.llm_provider in ("openai",) or cfg.openai_api_key:
        print("Endpoint   :", cfg.openai_base_url)
    print("Daily brief:", "on" if st["enabled"] else "off",
          f"at {st['at']}, {st['count']} job(s),",
          "with resumes" if st["build_resumes"] else "list only")
    print("Last run   :", st["last_run"] or "never")
    print("Next run   :", st["next_run"])
    last = daily.last_brief()
    if last:
        print(f"Last brief : {last['found']} found, {last['built']} built "
              f"at {last.get('finished_at', '?')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("brief", help="find jobs and build resumes")
    b.add_argument("--count", type=int, default=None)
    b.add_argument("--no-resumes", action="store_true",
                   help="just the ranked list, no resumes")

    sub.add_parser("pack", help="rebuild the Claude/ChatGPT project pack")
    sub.add_parser("schedule", help="print the OS scheduler command")
    sub.add_parser("status", help="show what is configured")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0

    _boot()
    if args.cmd == "brief":
        return asyncio.run(_brief(args.count, not args.no_resumes))
    if args.cmd == "pack":
        return _pack()
    if args.cmd == "schedule":
        return _schedule()
    if args.cmd == "status":
        return _status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
