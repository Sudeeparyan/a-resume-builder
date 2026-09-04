#!/usr/bin/env python3
"""
init_profile.py — set up and audit a candidate workspace.

  python3 system/scripts/init_profile.py --check
      Report every unfilled {{PLACEHOLDER}} and every file still holding template text.

  python3 system/scripts/init_profile.py --set FULL_NAME="Jane Doe" --set CITY=Fayetteville
      Substitute one or more tokens across system/profile/, system/config/ and system/templates/.

  python3 system/scripts/init_profile.py --from-yaml system/config/profile.yml
      Pull the candidate block out of system/config/profile.yml and substitute what it holds.

  python3 system/scripts/init_profile.py --check --json
      Machine-readable report (for CI or an agent).

Stdlib only. Never overwrites a file unless a substitution actually changes it.
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from pathlib import Path

# Play nicely with `| head` and friends.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass  # Windows has no SIGPIPE

# scripts live at <workspace>/system/scripts/, so the workspace root is three levels up
ROOT = Path(__file__).resolve().parents[2]

# Windows terminals default to cp1252 and choke on the arrows/ellipses in the report below.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass
TOKEN = re.compile(r"\{\{([A-Z][A-Z_0-9]*)\}\}")

SCAN_DIRS = ["system/profile", "system/config", "system/modes", "system/templates", "system/data"]
SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".tex", ".tsv", ".txt"}

# Tokens that must be filled before any resume can be generated.
BLOCKING = {
    "FULL_NAME", "EMAIL", "PHONE", "CITY", "COUNTRY",
    "SUMMARY_PARAGRAPH", "TRACK_A_NAME", "TRACK_B_NAME",
}


def iter_files(dirs=None):
    for d in (dirs if dirs is not None else SCAN_DIRS):
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix in SCAN_SUFFIXES:
                yield p


def scan(dirs=None):
    """Return {token: [relative paths]} and {path: count}.

    `dirs` narrows the scan. doctor.py passes the profile/config layer only,
    because system/templates/** is supposed to keep its {{TOKENS}}.
    """
    tokens: dict[str, list[str]] = {}
    per_file: dict[str, int] = {}
    for p in iter_files(dirs):
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found = TOKEN.findall(text)
        if not found:
            continue
        rel = str(p.relative_to(ROOT))
        per_file[rel] = len(found)
        for t in set(found):
            tokens.setdefault(t, []).append(rel)
    return tokens, per_file


def substitute(mapping: dict[str, str]) -> int:
    changed = 0
    for p in iter_files():
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = TOKEN.sub(lambda m: mapping.get(m.group(1), m.group(0)), text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed += 1
            print(f"  updated {p.relative_to(ROOT)}")
    return changed


def from_yaml(path: Path) -> dict[str, str]:
    """Extract simple `key: "value"` pairs from the candidate block without needing PyYAML."""
    mapping: dict[str, str] = {}
    key_to_token = {
        "full_name": "FULL_NAME", "email": "EMAIL", "phone": "PHONE",
        "linkedin": "LINKEDIN_URL", "github": "GITHUB_URL", "portfolio_url": "PORTFOLIO_URL",
        "current_status": "CURRENT_STATUS", "work_authorisation": "WORK_AUTH",
        "years_professional_experience": "YEARS_EXPERIENCE", "availability": "AVAILABILITY",
        "city": "CITY", "timezone": "TIMEZONE", "currency": "CURRENCY",
        "target_range": "COMP_RANGE", "minimum": "COMP_MINIMUM",
    }
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*([a-z_]+):\s*"?([^"#]*?)"?\s*(?:#.*)?$', line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        token = key_to_token.get(key)
        if token and value and not TOKEN.fullmatch(value):
            mapping[token] = value
    # location: "City, Country"
    m = re.search(r'location:\s*"([^"]+)"', path.read_text(encoding="utf-8"))
    if m and "," in m.group(1) and "{{" not in m.group(1):
        city, country = [x.strip() for x in m.group(1).split(",", 1)]
        mapping.setdefault("CITY", city)
        mapping.setdefault("COUNTRY", country)
    return mapping


def report(as_json: bool) -> int:
    tokens, per_file = scan()
    blocking = sorted(t for t in tokens if t in BLOCKING)
    other = sorted(t for t in tokens if t not in BLOCKING)

    if as_json:
        print(json.dumps({
            "unfilled_total": len(tokens),
            "blocking": {t: tokens[t] for t in blocking},
            "other": {t: tokens[t] for t in other},
            "files": per_file,
        }, indent=2))
        return 1 if blocking else 0

    if not tokens:
        print("✓ No placeholders left. Profile looks filled.")
        return 0

    print(f"{len(tokens)} distinct placeholder(s) still unfilled "
          f"across {len(per_file)} file(s).\n")
    if blocking:
        print("BLOCKING — a resume generated now would be incomplete:")
        for t in blocking:
            print(f"  {{{{{t}}}}}  → {', '.join(tokens[t][:4])}"
                  + (" …" if len(tokens[t]) > 4 else ""))
        print()
    if other:
        print("Remaining (fill what applies; delete the block if it does not):")
        width = max(len(t) for t in other) + 6
        for t in other:
            loc = tokens[t][0] + (f" +{len(tokens[t])-1} more" if len(tokens[t]) > 1 else "")
            print(f"  {('{{'+t+'}}').ljust(width)} {loc}")
        print()
    print("Next: add the missing facts to context/ and re-run the")
    print("profile-intake skill, or fill them directly in the files listed above.")
    return 1 if blocking else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report unfilled placeholders")
    ap.add_argument("--json", action="store_true", help="machine-readable output for --check")
    ap.add_argument("--set", action="append", default=[], metavar="TOKEN=VALUE",
                    help="substitute a token everywhere (repeatable)")
    ap.add_argument("--from-yaml", metavar="FILE",
                    help="substitute tokens using the candidate block of a profile.yml")
    args = ap.parse_args()

    mapping: dict[str, str] = {}
    if args.from_yaml:
        path = Path(args.from_yaml)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            print(f"error: {path} not found", file=sys.stderr)
            return 2
        mapping.update(from_yaml(path))
    for pair in args.set:
        if "=" not in pair:
            print(f"error: --set expects TOKEN=VALUE, got {pair!r}", file=sys.stderr)
            return 2
        k, v = pair.split("=", 1)
        mapping[k.strip().upper()] = v

    if mapping:
        print(f"Substituting {len(mapping)} token(s):")
        for k, v in sorted(mapping.items()):
            print(f"  {{{{{k}}}}} → {v}")
        n = substitute(mapping)
        print(f"{n} file(s) changed.\n")

    if args.check or not mapping:
        return report(args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
