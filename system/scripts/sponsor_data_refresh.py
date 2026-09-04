#!/usr/bin/env python3
"""
Build the local H-1B sponsorship index.

Downloads the USCIS H-1B Employer Data Hub bulk CSVs and normalizes them into
one lookup file that sponsor_check.py reads:

    system/data/sponsors-uscis.csv
    employer_key,employer,fiscal_year,approvals,denials,state,city

Source CSVs carry these columns:
    Fiscal Year, Employer, Initial Approval, Initial Denial,
    Continuing Approval, Continuing Denial, NAICS, Tax ID, State, City, ZIP

Notes
-----
FY2024+ bulk exports are not published by USCIS. FY2023 is the newest bulk year
and remains a sound "has sponsored" signal. The interactive hub goes further
(through FY2026 Q3) but is not bulk-downloadable.

This index is a RANKING signal only. A company absent from it is still shown.

Usage
-----
  python system/scripts/sponsor_data_refresh.py
  python system/scripts/sponsor_data_refresh.py --years 2022 2023
  python system/scripts/sponsor_data_refresh.py --lca      # 252MB, opt-in

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "system" / "data"
OUT = DATA / "sponsors-uscis.csv"
STAMP = DATA / "sponsors-refreshed.txt"

URL = "https://www.uscis.gov/sites/default/files/document/data/h1b_datahubexport-{year}.csv"
DEFAULT_YEARS = [2021, 2022, 2023]
UA = "Mozilla/5.0 (compatible; career-ops-workspace/1.0)"

SUFFIXES = (
    "incorporated", "inc", "llc", "l.l.c", "ltd", "limited", "corp", "corporation",
    "company", "co", "plc", "gmbh", "llp", "lp", "pllc", "pc", "sa", "nv", "ag",
    "holdings", "group", "technologies", "technology", "labs", "laboratories",
    "solutions", "services", "systems", "usa", "us", "america", "international",
)


def normalize(name: str) -> str:
    """Must stay identical to sponsor_check.normalize()."""
    s = (name or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def fetch(url: str, timeout: int = 180) -> bytes:
    """Fetch a URL, preferring curl.

    uscis.gov sits behind bot protection that rejects Python's TLS handshake
    with a 403 regardless of headers, while curl gets through. curl ships with
    Windows 10+ and with Git Bash, so it is the primary path; urllib is the
    fallback for environments without it.
    """
    curl = shutil.which("curl")
    if curl:
        proc = subprocess.run(
            [curl, "-sSL", "--fail", "--max-time", str(timeout),
             "-A", "curl/8.0", "-o", "-", url],
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        # curl --fail exits 22 on 4xx/5xx; surface it like an HTTPError
        code = 403
        m = re.search(r"\b(\d{3})\b", err)
        if m:
            code = int(m.group(1))
        raise urllib.error.HTTPError(url, code, err or "curl failed", None, None)

    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def pick(row: dict, *names: str) -> str:
    """Column headers drift between fiscal years — try several spellings."""
    for n in names:
        for key in row:
            if key and key.strip().lower() == n.lower():
                return (row[key] or "").strip()
    return ""


def to_int(value: str) -> int:
    try:
        return int(float(str(value).replace(",", "").strip() or 0))
    except (ValueError, TypeError):
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the local H-1B sponsor index.")
    ap.add_argument("--years", nargs="*", type=int, default=DEFAULT_YEARS)
    ap.add_argument("--lca", action="store_true",
                    help="also fetch the 252MB DOL LCA file (slow, needs openpyxl)")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)

    # employer_key -> aggregated record
    index: dict[str, dict] = {}
    fetched_years: list[int] = []

    for year in args.years:
        url = URL.format(year=year)
        print(f"  fetching FY{year} ...", end=" ", flush=True)
        try:
            raw = fetch(url)
        except urllib.error.HTTPError as e:
            print(f"skipped (HTTP {e.code} — no bulk export published for FY{year})")
            continue
        except Exception as e:  # network, TLS, timeout
            print(f"skipped ({type(e).__name__}: {e})")
            continue

        text = raw.decode("utf-8-sig", errors="replace")
        rows = 0
        for row in csv.DictReader(io.StringIO(text)):
            employer = pick(row, "Employer", "Employer Name")
            if not employer:
                continue
            key = normalize(employer)
            if not key:
                continue

            approvals = to_int(pick(row, "Initial Approval", "Initial Approvals")) + \
                to_int(pick(row, "Continuing Approval", "Continuing Approvals"))
            denials = to_int(pick(row, "Initial Denial", "Initial Denials")) + \
                to_int(pick(row, "Continuing Denial", "Continuing Denials"))
            state = pick(row, "State", "Petitioner State")
            city = pick(row, "City", "Petitioner City")

            rec = index.setdefault(key, {
                "employer_key": key,
                "employer": employer,
                "fiscal_year": str(year),
                "approvals": 0,
                "denials": 0,
                "state": state,
                "city": city,
            })
            rec["approvals"] += approvals
            rec["denials"] += denials
            if str(year) not in rec["fiscal_year"]:
                rec["fiscal_year"] = f"{rec['fiscal_year']};{year}"
            rows += 1

        fetched_years.append(year)
        print(f"{rows:,} rows  ({len(raw)/1_048_576:.1f} MB)")
        time.sleep(1)

    if not index:
        print("\nNo data fetched. The index was left unchanged.", file=sys.stderr)
        print("sponsor_check.py still works — it just reports 'no record',", file=sys.stderr)
        print("which never excludes a company.", file=sys.stderr)
        return 1

    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "employer_key", "employer", "fiscal_year", "approvals", "denials", "state", "city",
        ])
        w.writeheader()
        for rec in sorted(index.values(), key=lambda r: -r["approvals"]):
            w.writerow(rec)

    STAMP.write_text(
        f"refreshed: {date.today().isoformat()}\n"
        f"fiscal years: {', '.join(str(y) for y in fetched_years)}\n"
        f"employers: {len(index)}\n"
        f"source: USCIS H-1B Employer Data Hub (bulk CSV export)\n",
        encoding="utf-8",
    )

    print(f"\nWrote {OUT.relative_to(ROOT)}")
    print(f"  {len(index):,} distinct employers from FY {', '.join(str(y) for y in fetched_years)}")

    if args.lca:
        print("\nDOL LCA refresh requested (252MB).")
        print("  Not implemented as an automatic download — it needs openpyxl and")
        print("  several minutes. Run it deliberately when you want FY2026 freshness:")
        print("  https://www.dol.gov/media/LCA_Disclosure_Data_FY2026_Q3.xlsx")

    return 0


if __name__ == "__main__":
    sys.exit(main())
