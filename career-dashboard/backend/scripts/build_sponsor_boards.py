#!/usr/bin/env python3
"""Build data/sponsors/sponsor-boards.csv: careers boards of employers in the USCIS H-1B data.

Run it when the USCIS data is refreshed, or monthly to pick up employers that moved boards:

    backend/.venv/Scripts/python.exe backend/scripts/build_sponsor_boards.py --top 1500

1. Candidates: the employers with the most H-1B approvals (at least --min-approvals),
   leaving out those already tracked in data/config/portals.yml and public bodies,
   universities and hospitals (their jobs are not on these boards; the AI search covers them).
2. backend/services/sponsor_boards.py guesses a few board names on Greenhouse, Lever, Ashby
   and SmartRecruiters and accepts a board only when it lists a current US posting and names
   the same employer (its own name, or a US posting's text when the board states none).

Writes the registry CSV, its .meta.yml and a review file of what was tried and refused
(data/sponsors/sponsor-boards-review.json). A run of 1,500 employers takes about an hour,
so progress is checkpointed every 25 employers (sponsor-boards-progress.json); after an
interruption, ``--resume`` carries on from the checkpoint instead of starting again. Requests go through the portals reader: one at
a time per host, with a pause between them. Public data only; nothing about Annie is sent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

import yaml  # noqa: E402

from backend.paths import TIMEZONE  # noqa: E402
from backend.services import portals, sponsor_boards  # noqa: E402
from backend.services.sponsorship import SPONSORS_CSV, normalize  # noqa: E402


def tracked_keys() -> set[str]:
    return {normalize(row.get("name") or "") for row in portals.tracked_companies(enabled_only=False)} - {""}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=1500, help="how many of the largest H-1B employers to try")
    parser.add_argument("--min-approvals", type=int, default=5)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--only", action="append", default=[], help="try only this USCIS employer name (repeatable)")
    parser.add_argument("--keep", action="store_true", help="keep existing rows not re-found this run")
    parser.add_argument("--output", type=Path, default=sponsor_boards.BOARDS_CSV)
    parser.add_argument("--resume", action="store_true", help="carry on from the last checkpoint")
    args = parser.parse_args(argv)
    progress_path = args.output.parent / "sponsor-boards-progress.json"

    from zoneinfo import ZoneInfo
    on = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
    skip = tracked_keys()
    pool = sponsor_boards.candidates(args.top if not args.only else 100000, min_approvals=args.min_approvals, skip=skip)
    chosen = [c for c in pool if not args.only or c["legal_name"] in args.only]
    started = time.monotonic()
    results: dict[str, dict] = {}
    accepted: list[dict] = []
    if args.resume and progress_path.is_file():
        saved = json.loads(progress_path.read_text(encoding="utf-8"))
        results, accepted = saved.get("results") or {}, saved.get("accepted") or []
        print(f"Resuming: {len(results)} employers already decided, {len(accepted)} boards found.", file=sys.stderr, flush=True)
    total = len(chosen)
    chosen = [c for c in chosen if c["legal_name"] not in results]

    def checkpoint():
        temp = progress_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "results": results, "accepted": accepted}), encoding="utf-8")
        temp.replace(progress_path)

    print(f"Trying {len(chosen)} H-1B employers on {', '.join(sponsor_boards.KINDS)}...", file=sys.stderr, flush=True)

    def work(candidate):
        try:
            return candidate, sponsor_boards.resolve(candidate["legal_name"], state=candidate.get("state", ""),
                                                     city=candidate.get("city", ""))
        except Exception as exc:  # noqa: BLE001 - one odd employer must never stop the build
            return candidate, {"status": "unresolved", "legal_name": candidate["legal_name"], "tried": [],
                               "refused": [], "reason": f"{type(exc).__name__}: {exc}"[:200]}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        for done, (candidate, found) in enumerate(executor.map(work, chosen), total - len(chosen) + 1):
            results[candidate["legal_name"]] = {**found, "h1b_approvals": candidate["h1b_approvals"]}
            if found["status"] == "resolved":
                accepted.append(sponsor_boards.registry_row(found, candidate, on))
                print(f"  + {candidate['legal_name']}: {found['ats']}:{found['token']} ({found['reason']}; "
                      f"{found['us_postings']} US, {found['target_postings']} in her tracks)", file=sys.stderr, flush=True)
            if done % 25 == 0:
                checkpoint()
            if done % 50 == 0:
                print(f"  {done}/{total} tried, {len(accepted)} boards, {time.monotonic() - started:.0f}s",
                      file=sys.stderr, flush=True)

    # One row per board: two USCIS entities can share a brand's board; keep the larger sponsor.
    by_board: dict[str, dict] = {}
    for row in sorted(accepted, key=lambda r: -int(r["h1b_approvals"])):
        by_board.setdefault(sponsor_boards.board_id(row), row)
    rows = list(by_board.values())
    if args.keep:
        current = {sponsor_boards.board_id(r) for r in rows}
        tried = set(results)
        rows += [r for r in sponsor_boards.load(args.output)
                 if sponsor_boards.board_id(r) not in current and r["legal_name"] not in tried]
    rows.sort(key=lambda r: (-int(r["h1b_approvals"] or 0), r["employer"]))
    sponsor_boards.write(rows, args.output)

    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    meta = {
        "source": "Careers boards of employers in the USCIS H-1B Employer Data Hub (data/sponsors/sponsors-uscis.csv)",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "uscis_csv": SPONSORS_CSV.name,
        "candidates": total,
        "rows": len(rows),
        "boards_by_ats": dict(Counter(r["ats"] for r in rows)),
        "acceptance": ("At least one current US posting, and the board names the same employer: its own name equals "
                       "the USCIS legal name (exact), is at least 85% similar (similar), or is the brand the legal name "
                       "extends with descriptor words (brand); a board that states no name needs a US posting whose own "
                       "text names the employer (text). When the match rests on one word left after dropping words from "
                       "the legal name, a US posting must also be in the city or state USCIS records for the employer."),
        "csv_sha256": digest,
    }
    args.output.with_suffix(".meta.yml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    review = args.output.parent / "sponsor-boards-review.json"
    review.write_text(json.dumps({"built_at": meta["built_at"], "results": results}, indent=1) + "\n", encoding="utf-8")
    progress_path.unlink(missing_ok=True)  # a finished build needs no checkpoint
    print(json.dumps({"rows": len(rows), "candidates": total, "boards_by_ats": meta["boards_by_ats"],
                      "seconds": round(time.monotonic() - started), "output": str(args.output)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
