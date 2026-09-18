#!/usr/bin/env python3
"""
verify_job_url.py — check whether job listings are still open.

  python3 system/scripts/verify_job_url.py --url "https://example.com/jobs/123"
  python3 system/scripts/verify_job_url.py --file output/SUMMARY.md --delay 6
  python3 system/scripts/verify_job_url.py --file output/SUMMARY.md --output system/data/verify.json

Statuses: ACTIVE · EXPIRED · BROKEN · NEEDS_CHECK
  NEEDS_CHECK means a login wall, a JS-rendered page, or a careers homepage rather than a
  listing — open it yourself. It is never safe to record such a page as ACTIVE.

Uses requests + BeautifulSoup when they are installed, and falls back to the standard library
otherwise, so it runs with no install step. Be polite: keep --delay at 5s or more.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests  # type: ignore
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False
    import urllib.error
    import urllib.request

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAVE_BS4 = True
except ImportError:
    HAVE_BS4 = False

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

EXPIRED_PATTERNS = [
    r"no longer accepting applications", r"this job is no longer available",
    r"this position has been filled", r"job expired", r"applications? (are )?closed",
    r"this job has expired", r"this posting is no longer available",
    r"this listing has expired", r"this role has been filled", r"position filled",
    r"no longer available", r"page not found", r"404 not found",
    r"we can.?t find this page", r"this page does(n.?t| not) exist",
    r"this job has been archived", r"this opportunity is closed",
    r"this position is no longer (open|available|active|listed)",
    r"this vacancy (has )?(been )?closed", r"job not found", r"job listing not found",
    r"application deadline has passed", r"the deadline for this (job|position|role) has passed",
]

CAREER_PORTAL_PATTERNS = [
    r"/careers/?$", r"/careers/jobs/?$", r"/company/careers/?$", r"/jobs/?$",
    r"myworkdayjobs\.com/.*(External|Career)[^/]*/?$", r"recruitee\.com/?$",
]

TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
ANY_TAG = re.compile(r"<[^>]+>")
ROW_RE = re.compile(r"\[(?:Apply|apply|Link|link)\]\((https?://[^)\s]+)\)")


def classify(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "linkedin.com" in host:
        return "linkedin"
    for pat in CAREER_PORTAL_PATTERNS:
        if re.search(pat, url, re.I):
            return "career_portal"
    if any(p in url.lower() for p in ("workable.com/", "ashbyhq.com/", "recruitee.com/")):
        if len([s for s in urlparse(url).path.split("/") if s]) <= 1:
            return "career_portal"
    return "direct_job"


def fetch(url: str, timeout: int = 20):
    """Return (status_code, final_url, text) or raise."""
    if HAVE_REQUESTS:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r.status_code, r.url, r.text
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.status, resp.geturl(), raw.decode(charset, errors="ignore")


def page_text(html: str) -> str:
    if HAVE_BS4:
        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
    return ANY_TAG.sub(" ", TAG_RE.sub(" ", html)).lower()


def check(url: str, kind: str | None = None) -> dict:
    kind = kind or classify(url)
    out = {"url": url, "url_type": kind, "status": "ACTIVE", "reason": "",
           "http_status": None, "final_url": None}
    try:
        code, final, html = fetch(url)
        out["http_status"], out["final_url"] = code, final

        if final != url and classify(final) == "career_portal" and kind != "career_portal":
            out.update(status="EXPIRED", reason=f"redirected to a careers homepage: {final}")
            return out
        if code >= 400:
            out.update(status="BROKEN", reason=f"HTTP {code}")
            return out
        if kind == "career_portal":
            out.update(status="NEEDS_CHECK",
                       reason="careers homepage, not a specific listing — search it yourself")
            return out

        text = page_text(html)
        for pat in EXPIRED_PATTERNS:
            m = re.search(pat, text)
            if m:
                out.update(status="EXPIRED", reason=m.group(0).strip())
                return out
        if kind == "linkedin" and len(text) < 400:
            out.update(status="NEEDS_CHECK", reason="LinkedIn auth wall — open it signed in")
            return out
        if len(text) < 200:
            out.update(status="NEEDS_CHECK", reason="page rendered by JavaScript — open it yourself")
    except Exception as exc:                      # noqa: BLE001 - report, never crash the batch
        name = type(exc).__name__
        reason = f"{name}: {str(exc)[:120]}"
        out.update(status="NEEDS_CHECK" if "Timeout" in name else "BROKEN", reason=reason)
    return out


def extract(md_path: Path) -> list[dict]:
    """Pull [Apply](url) links out of any Markdown table, with the row's company/role if present."""
    entries = []
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.search(line)
        if not m:
            continue
        cells = [c.strip().strip("*") for c in line.split("|")]
        company = cells[2] if len(cells) > 3 else ""
        role = cells[3] if len(cells) > 4 else ""
        entries.append({"company": company, "role": role, "url": m.group(1)})
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url")
    g.add_argument("--file")
    ap.add_argument("--delay", type=float, default=6.0, help="seconds between requests (min 5 is polite)")
    ap.add_argument("--output", help="where to write the JSON report")
    args = ap.parse_args()

    if not HAVE_REQUESTS:
        print("note: 'requests' not installed — using the standard library fallback.\n"
              "      pip install requests beautifulsoup4  for slightly better results.",
              file=sys.stderr)

    results = []
    if args.url:
        results.append(check(args.url) | {"company": "", "role": ""})
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"error: {path} not found", file=sys.stderr)
            return 2
        entries = extract(path)
        if not entries:
            print(f"No [Apply](url) links found in {path}", file=sys.stderr)
            return 1
        print(f"Checking {len(entries)} listing(s) — about "
              f"{len(entries) * args.delay / 60:.1f} min at {args.delay}s apart\n", file=sys.stderr)
        for i, e in enumerate(entries, 1):
            r = check(e["url"]) | {"company": e["company"], "role": e["role"]}
            icon = {"ACTIVE": "OK ", "EXPIRED": "GONE", "BROKEN": "ERR ", "NEEDS_CHECK": "?? "}[r["status"]]
            print(f"[{i}/{len(entries)}] {icon} {e['company'] or e['url'][:50]} — "
                  f"{r['status']}{': ' + r['reason'] if r['reason'] else ''}", file=sys.stderr)
            results.append(r)
            if i < len(entries):
                time.sleep(args.delay)

    out_path = Path(args.output) if args.output else Path(f"verification_results_{date.today()}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("ACTIVE", "EXPIRED", "BROKEN", "NEEDS_CHECK")}
    print(f"\nActive {counts['ACTIVE']} · Expired {counts['EXPIRED']} · "
          f"Broken {counts['BROKEN']} · Needs check {counts['NEEDS_CHECK']}", file=sys.stderr)
    print(f"Report: {out_path}", file=sys.stderr)
    if counts["EXPIRED"] or counts["BROKEN"]:
        print("\nRemove these rows from the companies file:", file=sys.stderr)
        for r in results:
            if r["status"] in ("EXPIRED", "BROKEN"):
                print(f"  {r['company'] or r['url']} — {r['reason']}", file=sys.stderr)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
