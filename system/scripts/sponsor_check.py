#!/usr/bin/env python3
"""
The sponsorship gate.

Two things, usable together or separately:

  1. SCREEN a job description's text     -> EXCLUDE / KEEP, with the triggering sentence
  2. LOOK UP a company's H-1B history    -> ranking tier + evidence

The rule this implements:

    posting explicitly WILL NOT sponsor          -> EXCLUDE, never shown
    posting says NOTHING about sponsorship       -> KEEP  (most postings; the largest bucket)
    posting explicitly WILL sponsor              -> KEEP, tier A
    posting requires citizenship/clearance/ITAR  -> EXCLUDE (cannot be hired at all)

Sponsorship history NEVER excludes. It only ranks.

Usage
-----
  python system/scripts/sponsor_check.py --jd path/to/jd.txt --company "Acme Inc"
  python system/scripts/sponsor_check.py --jd-text "..." --json
  python system/scripts/sponsor_check.py --company "Medtronic" --state MN
  echo "<jd text>" | python system/scripts/sponsor_check.py --jd -

Exit codes: 0 = keep, 1 = excluded, 2 = usage error.
Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

try:  # keep console output sane on Windows cp1252
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "system" / "config" / "sponsorship.yml"
USCIS_CACHE = ROOT / "system" / "data" / "sponsors-uscis.csv"
LCA_CACHE = ROOT / "system" / "data" / "sponsors-lca.csv"

OK, EXCLUDED, USAGE = 0, 1, 2


# --------------------------------------------------------------------------
# Minimal YAML reader.
#
# sponsorship.yml is a flat map of string lists plus a couple of nested maps.
# Rather than depend on PyYAML, pull out just the list-of-strings blocks we
# need. If PyYAML happens to be installed we use it and skip all this.
# --------------------------------------------------------------------------
def load_config(path: Path = CONFIG) -> dict:
    if not path.exists():
        die(f"missing config: {path}")
    text = path.read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except Exception:
        pass

    cfg: dict = {}
    current_key = None
    current_list: list[str] | None = None

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        # top-level key
        m = re.match(r"^([a-z_][a-z0-9_]*):\s*(.*)$", raw)
        if m:
            if current_key and current_list is not None:
                cfg[current_key] = current_list
            current_key, rest = m.group(1), m.group(2).strip()
            current_list = [] if not rest else None
            if rest and not rest.startswith(">"):
                cfg[current_key] = rest.strip("'\"")
                current_key, current_list = None, None
            continue
        # list item under a top-level key
        m = re.match(r"^\s+-\s+(.*)$", raw)
        if m and current_list is not None:
            item = m.group(1).strip()
            if item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            elif item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            current_list.append(item)

    if current_key and current_list is not None:
        cfg[current_key] = current_list
    return cfg


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(USAGE)


# --------------------------------------------------------------------------
# Screening
# --------------------------------------------------------------------------
def split_sentences(text: str) -> list[str]:
    """Rough sentence split. Job descriptions are bullet soup, so treat
    newlines and bullet glyphs as terminators too."""
    normalized = re.sub(r"[\r\n•·•]+", ". ", text)
    parts = re.split(r"(?<=[.!?;])\s+", normalized)
    return [p.strip() for p in parts if p.strip()]


def _match(patterns: list[str], sentence: str) -> str | None:
    for pat in patterns:
        try:
            if re.search(pat, sentence, re.IGNORECASE):
                return pat
        except re.error:
            continue
    return None


def screen(jd_text: str, cfg: dict) -> dict:
    """Return a verdict dict. Never raises on odd input."""
    no_sponsor = cfg.get("exclude_no_sponsorship", []) or []
    cannot_hire = cfg.get("exclude_cannot_hire", []) or []
    positive = cfg.get("positive_sponsorship", []) or []
    innocent = cfg.get("ambiguous_sponsor_noun", []) or []

    everify_pats = cfg.get("everify_signals", []) or []
    everify = bool(_match(everify_pats, jd_text))

    sentences = split_sentences(jd_text)
    hits_positive: list[dict] = []

    for sentence in sentences:
        # Skip sentences where "sponsor" is clearly innocent (event sponsor etc.)
        if _match(innocent, sentence):
            continue

        pat = _match(cannot_hire, sentence)
        if pat:
            return {
                "verdict": "EXCLUDED",
                "reason": "cannot_hire",
                "reason_label": "Requires citizenship / clearance / ITAR / permanent residency",
                "pattern": pat,
                "sentence": sentence[:400],
                "tier": "EXCLUDED",
                "everify": everify,
            }

        pat = _match(no_sponsor, sentence)
        if pat:
            return {
                "verdict": "EXCLUDED",
                "reason": "no_sponsorship",
                "reason_label": "Posting explicitly will not sponsor",
                "pattern": pat,
                "sentence": sentence[:400],
                "tier": "EXCLUDED",
                "everify": everify,
            }

        pat = _match(positive, sentence)
        if pat:
            hits_positive.append({"pattern": pat, "sentence": sentence[:400]})

    if hits_positive:
        return {
            "verdict": "KEEP",
            "reason": "explicit_sponsorship",
            "reason_label": "Posting explicitly offers sponsorship",
            "tier": "A",
            "evidence": hits_positive[:3],
            "everify": everify,
        }

    return {
        "verdict": "KEEP",
        "reason": "silent",
        "reason_label": "Posting says nothing about sponsorship — the normal case",
        "tier": None,  # resolved by the company lookup: B if history, else C
        "evidence": [],
        "everify": everify,
    }


# --------------------------------------------------------------------------
# Company lookup
# --------------------------------------------------------------------------
SUFFIXES = (
    "incorporated", "inc", "llc", "l.l.c", "ltd", "limited", "corp", "corporation",
    "company", "co", "plc", "gmbh", "llp", "lp", "pllc", "pc", "sa", "nv", "ag",
    "holdings", "group", "technologies", "technology", "labs", "laboratories",
    "solutions", "services", "systems", "usa", "us", "america", "international",
)


def normalize(name: str) -> str:
    s = (name or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def is_cap_exempt(name: str, cfg: dict, domain: str = "") -> tuple[bool, str]:
    lowered = (name or "").lower()
    for d in (".edu", ".gov"):
        if domain and domain.lower().endswith(d):
            return True, f"domain {d}"
    for needle in cfg.get("cap_exempt_name_contains", []) or [
        "university", "college", "institute of technology", "national laboratory",
        "national lab", "research institute", "medical center", "health system",
        "children's hospital", "cancer center", "academy of sciences",
    ]:
        if needle.lower() in lowered:
            return True, f"name contains '{needle}'"
    return False, ""


def lookup_history(company: str, state: str = "") -> dict:
    """Look the company up in the cached USCIS/LCA indexes."""
    key = normalize(company)
    if not key:
        return {"found": False, "reason": "empty company name"}

    result = {
        "found": False,
        "matched_name": None,
        "approvals": 0,
        "years": [],
        "states": [],
        "source": None,
    }

    for cache, label in ((USCIS_CACHE, "USCIS H-1B Employer Data Hub"), (LCA_CACHE, "DOL LCA")):
        if not cache.exists():
            continue
        try:
            with cache.open("r", encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    if row.get("employer_key") != key:
                        continue
                    if state and row.get("state") and row["state"].upper() != state.upper():
                        # record it, but a state mismatch is not disqualifying
                        pass
                    result["found"] = True
                    result["matched_name"] = row.get("employer") or company
                    try:
                        result["approvals"] += int(row.get("approvals") or 0)
                    except ValueError:
                        pass
                    y = row.get("fiscal_year")
                    if y and y not in result["years"]:
                        result["years"].append(y)
                    st = row.get("state")
                    if st and st not in result["states"]:
                        result["states"].append(st)
                    result["source"] = label
        except OSError:
            continue

    result["years"] = sorted(result["years"])
    return result


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sponsorship gate: screen a JD and/or look up a company's H-1B history."
    )
    ap.add_argument("--jd", help="path to a file with the job description text, or - for stdin")
    ap.add_argument("--jd-text", help="job description text inline")
    ap.add_argument("--company", help="employer name")
    ap.add_argument("--state", default="", help="two-letter state, optional")
    ap.add_argument("--domain", default="", help="company domain, helps detect cap-exempt")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if not (args.jd or args.jd_text or args.company):
        ap.print_help()
        return USAGE

    cfg = load_config()
    out: dict = {"company": args.company}

    # ---- screen ----
    jd_text = ""
    if args.jd == "-":
        jd_text = sys.stdin.read()
    elif args.jd:
        p = Path(args.jd)
        if not p.exists():
            die(f"no such file: {p}")
        jd_text = p.read_text(encoding="utf-8", errors="replace")
    elif args.jd_text:
        jd_text = args.jd_text

    verdict = None
    if jd_text:
        verdict = screen(jd_text, cfg)
        out["screen"] = verdict

    # ---- company ----
    tier = verdict["tier"] if verdict else None
    if args.company:
        exempt, why = is_cap_exempt(args.company, cfg, args.domain)
        history = lookup_history(args.company, args.state)
        out["cap_exempt"] = exempt
        out["cap_exempt_reason"] = why
        out["history"] = history

        if verdict and verdict["verdict"] == "EXCLUDED":
            tier = "EXCLUDED"
        elif exempt:
            tier = "S"
        elif tier != "A":
            tier = "B" if history.get("found") else "C"

    out["tier"] = tier
    excluded = bool(verdict and verdict["verdict"] == "EXCLUDED")
    out["verdict"] = "EXCLUDED" if excluded else "KEEP"

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        _print_human(out)

    return EXCLUDED if excluded else OK


TIER_LABEL = {
    "S": "S — cap-exempt (no H-1B lottery, files year-round)",
    "A": "A — posting explicitly offers sponsorship",
    "B": "B — proven sponsor, posting silent",
    "C": "C — silent, no record (normal case, still worth applying)",
    "EXCLUDED": "EXCLUDED",
}


def _print_human(out: dict) -> None:
    company = out.get("company") or "(no company given)"
    print(f"Company : {company}")
    print(f"Verdict : {out['verdict']}")
    print(f"Tier    : {TIER_LABEL.get(out.get('tier'), out.get('tier') or 'n/a')}")

    s = out.get("screen")
    if s:
        print(f"\nScreen  : {s['reason_label']}")
        if s["verdict"] == "EXCLUDED":
            print(f"  triggered by : {s['sentence']}")
            print(f"  pattern      : {s['pattern']}")
        for ev in s.get("evidence", [])[:2]:
            print(f"  positive     : {ev['sentence']}")
        if s.get("everify"):
            print("  E-Verify     : YES - employer participates in E-Verify.")
            print("                 That is what the STEM OPT extension (+24 months) requires,")
            print("                 and it needs no sponsorship at all.")

    h = out.get("history")
    if h:
        if h.get("found"):
            years = ", ".join(h["years"]) or "?"
            states = ", ".join(h["states"][:6]) or "?"
            print(f"\nHistory : {h['approvals']} H-1B approvals  (FY {years})")
            print(f"  states : {states}")
            print(f"  source : {h['source']}")
        else:
            print("\nHistory : no H-1B record in the local index.")
            print("  This is NOT a reason to skip the company — most employers")
            print("  never appear here, and many sponsor after the interviews.")

    if out.get("cap_exempt"):
        print(f"\nCap-exempt: YES ({out.get('cap_exempt_reason')})")
        print("  Files H-1B any time of year with no lottery. Rank first.")


if __name__ == "__main__":
    sys.exit(main())
