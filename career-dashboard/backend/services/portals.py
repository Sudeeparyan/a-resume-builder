"""Tracked companies' own career pages, read through their public ATS JSON feeds.

Greenhouse, Lever and Ashby publish every open posting as JSON with the full job
description. No AI call is needed to find, gate and save these, so this is the
cheapest and most reliable discovery mode: it reads data/config/portals.yml,
pulls each company's board, and hands the postings to the same relevance,
sponsorship and never-re-apply gates as the AI search.

Standard library only (urllib + json). Network failures skip a board; they never
stop the pass.
"""
from __future__ import annotations

import html as _html
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.paths import CONFIG, TIMEZONE


def _today() -> str:
    """The access date in Annie's time zone, for the source records on each posting."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()

PORTALS_YML = CONFIG / "portals.yml"
TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (annie-career-workspace; local job search)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")
_NL_RE = re.compile(r"\n{3,}")


def html_to_text(raw: str) -> str:
    """Greenhouse returns HTML-escaped HTML, so unescape then strip, repeatedly."""
    if not raw:
        return ""
    text = raw
    for _ in range(3):
        before = text
        text = _html.unescape(text)
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|ul|ol)\s*>", "\n", text)
        text = re.sub(r"(?i)<li[^>]*>", "\n- ", text)
        text = _TAG_RE.sub(" ", text)
        if text == before:
            break
    text = text.replace("\xa0", " ").replace("​", "")
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NL_RE.sub("\n\n", text).strip()


def tracked_companies(enabled_only: bool = True) -> list[dict[str, Any]]:
    """Read portals.yml; cap-exempt employers first (no lottery for them)."""
    try:
        import yaml
        data = yaml.safe_load(PORTALS_YML.read_text()) or {}
    except Exception:  # noqa: BLE001 - a missing or broken file means no tracked boards
        return []
    rows = [r for r in data.get("tracked_companies") or [] if isinstance(r, dict) and (not enabled_only or r.get("enabled", True))]
    rows.sort(key=lambda r: (not r.get("cap_exempt", False), r.get("name", "")))
    return rows


def board_token(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """(ats, token) from explicit fields, else inferred from the careers URL."""
    ats = (row.get("ats") or "").strip().lower() or None
    token = (row.get("ats_token") or "").strip() or None
    if ats and token:
        return ats, token
    url = (row.get("careers_url") or "").lower()
    for key, marker in (("greenhouse", "boards.greenhouse.io/"), ("greenhouse", "job-boards.greenhouse.io/"),
                        ("lever", "jobs.lever.co/"), ("ashby", "jobs.ashbyhq.com/")):
        if marker in url:
            tail = url.split(marker, 1)[1].strip("/").split("/")[0].split("?")[0]
            if tail:
                return key, tail
    return ats, token


def _get_json(url: str):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None


def _posting(row, source_id, title, url, location, description, employer_type="company"):
    return {
        "company": row.get("name") or "",
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "url": url or "",
        "requisition_id": str(source_id or ""),
        "description": (description or "").strip(),
        "company_sources": [{"title": f"{row.get('name')} careers", "url": row.get("careers_url", ""), "accessed_at": _today()}],
        "legal_presence": "Posting read from the company's own ATS board (tracked in portals.yml).",
        "verification": "Read directly from the employer's ATS JSON feed.",
        "red_flags": [],
        "size_category": "unknown",
        "employee_min": None,
        "employee_max": None,
        "sponsorship_state": "unknown",
        "sponsorship_evidence": [],
        "restriction_quote": "",
        "employer_type": "university" if row.get("cap_exempt") else employer_type,
        "applicant_count": None,
        "competition_signals": {"posted_within_72h": False, "limited_syndication": True, "niche_match": False},
    }


def fetch_board(row: dict[str, Any]) -> list[dict[str, Any]]:
    ats, token = board_token(row)
    if not ats or not token:
        return []
    out: list[dict[str, Any]] = []
    if ats == "greenhouse":
        data = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true") or {}
        for job in data.get("jobs", []) or []:
            out.append(_posting(row, job.get("id"), job.get("title"), job.get("absolute_url"),
                                ((job.get("location") or {}).get("name") or ""), html_to_text(job.get("content") or "")))
    elif ats == "lever":
        data = _get_json(f"https://api.lever.co/v0/postings/{token}?mode=json") or []
        for job in data or []:
            cats = job.get("categories") or {}
            body = job.get("descriptionPlain") or html_to_text(job.get("description") or "")
            for lst in job.get("lists") or []:
                body += "\n\n" + (lst.get("text") or "") + "\n" + html_to_text(lst.get("content") or "")
            out.append(_posting(row, job.get("id"), job.get("text"), job.get("hostedUrl") or job.get("applyUrl"),
                                cats.get("location") or "", body))
    elif ats == "ashby":
        data = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true") or {}
        for job in data.get("jobs", []) or []:
            out.append(_posting(row, job.get("id") or job.get("jobId"), job.get("title"), job.get("jobUrl") or job.get("applyUrl"),
                                job.get("location") or "", job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml") or "")))
    return out


def fetch_all(limit_per_board: int | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """Every open posting on every tracked board that has an ATS feed, plus a coverage note per board."""
    postings: list[dict[str, Any]] = []
    coverage: list[str] = []
    for row in tracked_companies():
        ats, token = board_token(row)
        if not ats or not token:
            coverage.append(f"{row.get('name')}: no public ATS feed configured (careers page only)")
            continue
        found = fetch_board(row)
        postings.extend(found[:limit_per_board] if limit_per_board else found)
        coverage.append(f"{row.get('name')}: {len(found)} open postings via {ats}")
    return postings, coverage
