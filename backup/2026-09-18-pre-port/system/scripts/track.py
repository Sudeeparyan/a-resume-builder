#!/usr/bin/env python3
"""
Application and rejection tracker.

Answers the question that was costing the most time: "have I already applied
here, and did they already say no?"

Store: system/data/applications.tsv  (tab-separated, safe to open in Excel)

Status lifecycle
----------------
  PREPARED -> APPLIED -> SCREEN -> INTERVIEW -> OFFER
  any -> REJECTED | GHOSTED | WITHDRAWN | CLOSED

Exclusion rules, applied BEFORE scoring on every scan
-----------------------------------------------------
  * same company + same role title  -> never re-surfaced, any status
  * company REJECTED                -> suppressed for 180 days; that exact role never again
  * APPLIED with no reply for 21 days -> auto-flips to GHOSTED; company eligible again
                                         after 90 days for a DIFFERENT role only

Usage
-----
  python system/scripts/track.py --add --company "Acme" --role "Data Engineer" \
      --url https://... --tier B --score 78 --folder Annie_Manoharan_Acme_01
  python system/scripts/track.py --status 3 APPLIED
  python system/scripts/track.py --status 3 REJECTED --note "rejected after screen"
  python system/scripts/track.py --list
  python system/scripts/track.py --list --open
  python system/scripts/track.py --exclusions            # what the hunter must skip
  python system/scripts/track.py --check "Acme" "Data Engineer"
  python system/scripts/track.py --age                   # run the 21-day auto-flip
  python system/scripts/track.py --sync-applied-companies

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "system" / "data"
TSV = DATA / "applications.tsv"
APPLIED_MD = DATA / "applied-companies.md"

FIELDS = [
    "app_id", "date_found", "date_applied", "company", "role_title", "job_url",
    "ats", "track", "score", "sponsor_tier", "sponsor_evidence", "status",
    "last_update", "folder", "notes",
]

OPEN_STATUSES = {"PREPARED", "APPLIED", "SCREEN", "INTERVIEW", "OFFER"}
CLOSED_STATUSES = {"REJECTED", "GHOSTED", "WITHDRAWN", "CLOSED"}
ALL_STATUSES = OPEN_STATUSES | CLOSED_STATUSES

GHOST_AFTER_DAYS = 21
REJECT_COOLDOWN_DAYS = 180
GHOST_COOLDOWN_DAYS = 90

TODAY = date.today()


def norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def load() -> list[dict]:
    if not TSV.exists():
        return []
    with TSV.open("r", encoding="utf-8", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter="\t")]


def save(rows: list[dict]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime((s or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def next_id(rows: list[dict]) -> str:
    best = 0
    for r in rows:
        try:
            best = max(best, int(r.get("app_id") or 0))
        except ValueError:
            pass
    return str(best + 1)


# --------------------------------------------------------------------------
def cmd_add(args) -> int:
    rows = load()
    dup = [
        r for r in rows
        if norm(r["company"]) == norm(args.company)
        and norm(r["role_title"]) == norm(args.role)
    ]
    if dup and not args.force:
        r = dup[0]
        print(f"ALREADY TRACKED as #{r['app_id']}  [{r['status']}]  {r['date_found']}")
        print("  Nothing added. Use --force only if this is genuinely a new opening.")
        return 1

    row = {
        "app_id": next_id(rows),
        "date_found": TODAY.isoformat(),
        "date_applied": "",
        "company": args.company,
        "role_title": args.role,
        "job_url": args.url or "",
        "ats": args.ats or "",
        "track": args.track or "",
        "score": args.score or "",
        "sponsor_tier": args.tier or "",
        "sponsor_evidence": args.evidence or "",
        "status": args.status or "PREPARED",
        "last_update": TODAY.isoformat(),
        "folder": args.folder or "",
        "notes": args.note or "",
    }
    rows.append(row)
    save(rows)
    print(f"Added #{row['app_id']}  {row['company']} — {row['role_title']}  [{row['status']}]")
    return 0


def cmd_status(args) -> int:
    app_id, new_status = args.status[0], args.status[1].upper()
    if new_status not in ALL_STATUSES:
        print(f"error: unknown status '{new_status}'", file=sys.stderr)
        print(f"  valid: {', '.join(sorted(ALL_STATUSES))}", file=sys.stderr)
        return 2

    rows = load()
    for r in rows:
        if r["app_id"] == str(app_id):
            old = r["status"]
            r["status"] = new_status
            r["last_update"] = TODAY.isoformat()
            if new_status == "APPLIED" and not r["date_applied"]:
                r["date_applied"] = TODAY.isoformat()
            if args.note:
                r["notes"] = (r["notes"] + " | " if r["notes"] else "") + args.note
            save(rows)
            print(f"#{app_id}  {r['company']} — {r['role_title']}:  {old} -> {new_status}")
            if new_status == "REJECTED":
                until = (TODAY + timedelta(days=REJECT_COOLDOWN_DAYS)).isoformat()
                print(f"  {r['company']} is now suppressed from scans until {until}.")
                print(f"  '{r['role_title']}' there will never be surfaced again.")
            return 0
    print(f"error: no application #{app_id}", file=sys.stderr)
    return 2


def cmd_age(args) -> int:
    rows = load()
    flipped = 0
    for r in rows:
        if r["status"] != "APPLIED":
            continue
        applied = parse_date(r["date_applied"]) or parse_date(r["last_update"])
        if applied and (TODAY - applied).days >= GHOST_AFTER_DAYS:
            r["status"] = "GHOSTED"
            r["last_update"] = TODAY.isoformat()
            r["notes"] = (r["notes"] + " | " if r["notes"] else "") + \
                f"auto-ghosted after {GHOST_AFTER_DAYS}d"
            flipped += 1
            print(f"  #{r['app_id']}  {r['company']} — {r['role_title']}  -> GHOSTED")
    if flipped:
        save(rows)
        print(f"\n{flipped} application(s) flipped to GHOSTED.")
    else:
        print("Nothing to age out.")
    return 0


def exclusion_sets(rows: list[dict]) -> tuple[set, set, list]:
    """(company+role pairs to never show, companies in cooldown, human-readable reasons)"""
    pairs, companies, reasons = set(), set(), []
    for r in rows:
        pairs.add((norm(r["company"]), norm(r["role_title"])))
        updated = parse_date(r["last_update"]) or parse_date(r["date_found"])
        if not updated:
            continue
        age = (TODAY - updated).days
        if r["status"] == "REJECTED" and age < REJECT_COOLDOWN_DAYS:
            companies.add(norm(r["company"]))
            left = REJECT_COOLDOWN_DAYS - age
            reasons.append(f"{r['company']}: REJECTED, {left}d of cooldown left")
        elif r["status"] == "GHOSTED" and age < GHOST_COOLDOWN_DAYS:
            left = GHOST_COOLDOWN_DAYS - age
            reasons.append(
                f"{r['company']}: GHOSTED on '{r['role_title']}', "
                f"{left}d left (a DIFFERENT role there is fine)"
            )
        elif r["status"] in OPEN_STATUSES:
            reasons.append(f"{r['company']}: open application ({r['status']})")
    return pairs, companies, reasons


def cmd_exclusions(args) -> int:
    rows = load()
    pairs, companies, reasons = exclusion_sets(rows)
    print("EXCLUSIONS — apply these before scoring anything\n")
    print(f"Blocked company+role pairs ({len(pairs)}):")
    for c, role in sorted(pairs):
        print(f"  - {c}  /  {role}")
    print(f"\nCompanies fully suppressed right now ({len(companies)}):")
    for c in sorted(companies) or ["  (none)"]:
        print(f"  - {c}" if companies else c)
    print("\nWhy:")
    for why in reasons or ["  (nothing tracked yet)"]:
        print(f"  - {why}" if reasons else why)
    return 0


def cmd_check(args) -> int:
    company, role = args.check[0], (args.check[1] if len(args.check) > 1 else "")
    rows = load()
    hits = [r for r in rows if norm(r["company"]) == norm(company)]
    if not hits:
        print(f"{company}: never applied. Clear to go.")
        return 0
    print(f"{company}: {len(hits)} record(s)")
    blocked = False
    for r in hits:
        updated = parse_date(r["last_update"])
        age = (TODAY - updated).days if updated else 999
        print(f"  #{r['app_id']}  {r['role_title']}  [{r['status']}]  {age}d ago")
        if role and norm(r["role_title"]) == norm(role):
            print("     -> SAME ROLE. Never re-surface.")
            blocked = True
        if r["status"] == "REJECTED" and age < REJECT_COOLDOWN_DAYS:
            print(f"     -> REJECTED, {REJECT_COOLDOWN_DAYS - age}d cooldown left. Company suppressed.")
            blocked = True
    return 1 if blocked else 0


def cmd_list(args) -> int:
    rows = load()
    if args.open:
        rows = [r for r in rows if r["status"] in OPEN_STATUSES]
    if not rows:
        print("Nothing tracked yet.")
        return 0
    print(f"{'#':>3}  {'COMPANY':<26} {'ROLE':<30} {'TIER':<4} {'SCORE':>5}  {'STATUS':<10} AGE")
    print("-" * 100)
    for r in rows:
        updated = parse_date(r["last_update"])
        age = f"{(TODAY - updated).days}d" if updated else "?"
        print(f"{r['app_id']:>3}  {r['company'][:25]:<26} {r['role_title'][:29]:<30} "
              f"{r['sponsor_tier']:<4} {r['score']:>5}  {r['status']:<10} {age}")
    counts: dict[str, int] = {}
    for r in load():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


def cmd_sync(args) -> int:
    """Regenerate applied-companies.md from the TSV. Never hand-edit that file."""
    rows = load()
    _, companies, reasons = exclusion_sets(rows)
    DATA.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Applied companies — GENERATED FILE, DO NOT EDIT",
        "",
        "Regenerated by `system/scripts/track.py --sync-applied-companies`.",
        "Source of truth is `system/data/applications.tsv`.",
        "",
        f"Last synced: {TODAY.isoformat()}",
        "",
        "## Never surface these company + role pairs again",
        "",
    ]
    for r in rows:
        lines.append(f"- **{r['company']}** — {r['role_title']}  "
                     f"(#{r['app_id']}, {r['status']}, {r['last_update']})")
    lines += ["", "## Companies fully suppressed right now", ""]
    lines += [f"- {c}" for c in sorted(companies)] or ["- (none)"]
    lines += ["", "## Reasons", ""]
    lines += [f"- {w}" for w in reasons] or ["- (nothing tracked yet)"]
    APPLIED_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {APPLIED_MD.relative_to(ROOT)}  ({len(rows)} records)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Track applications, rejections, and exclusions.")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--company")
    ap.add_argument("--role")
    ap.add_argument("--url")
    ap.add_argument("--ats")
    ap.add_argument("--track")
    ap.add_argument("--score")
    ap.add_argument("--tier")
    ap.add_argument("--evidence")
    ap.add_argument("--folder")
    ap.add_argument("--note")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", nargs=2, metavar=("ID", "STATUS"))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--open", action="store_true", help="with --list, show only live applications")
    ap.add_argument("--exclusions", action="store_true")
    ap.add_argument("--check", nargs="+", metavar=("COMPANY", "ROLE"))
    ap.add_argument("--age", action="store_true")
    ap.add_argument("--sync-applied-companies", dest="sync", action="store_true")
    args = ap.parse_args()

    if args.add:
        if not (args.company and args.role):
            print("error: --add needs --company and --role", file=sys.stderr)
            return 2
        return cmd_add(args)
    if args.status:
        return cmd_status(args)
    if args.age:
        return cmd_age(args)
    if args.exclusions:
        return cmd_exclusions(args)
    if args.check:
        return cmd_check(args)
    if args.sync:
        return cmd_sync(args)
    if args.list:
        return cmd_list(args)

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
