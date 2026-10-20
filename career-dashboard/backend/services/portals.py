"""Tracked companies' own career pages, read through their public ATS JSON feeds.

Greenhouse, Lever and Ashby publish every open posting as JSON with the full job
description; Workday and SmartRecruiters publish a searchable listing plus one JSON
document per posting. No AI call is needed to find, gate and save these, so this is
the cheapest and most reliable discovery mode: it reads data/config/portals.yml,
pulls each company's board, and hands the postings to the same relevance,
sponsorship and never-re-apply gates as the AI search.

Workday and SmartRecruiters boards list thousands of roles, so only titles that name
one of Annie's four tracks at entry level (backend/job_quality.py) have their full
posting fetched, a few dozen per board. Boards are read in parallel, at most one
request at a time per host with a short pause between them.

Standard library only (urllib + json). A board that cannot be read is reported as
FETCH FAILED in the coverage notes; it never stops the pass and never looks empty.
"""
from __future__ import annotations

import html as _html
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
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
        data = yaml.safe_load(PORTALS_YML.read_text(encoding="utf-8")) or {}
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
    raw = row.get("careers_url") or ""
    url = raw.lower()
    for key, marker in (("greenhouse", "boards.greenhouse.io/"), ("greenhouse", "job-boards.greenhouse.io/"),
                        ("lever", "jobs.lever.co/"), ("ashby", "jobs.ashbyhq.com/"),
                        ("smartrecruiters", "jobs.smartrecruiters.com/"), ("smartrecruiters", "careers.smartrecruiters.com/")):
        if marker in url:
            # SmartRecruiters company ids keep their case ("BoschGroup"); the others are lower case.
            tail = raw[url.index(marker) + len(marker):].strip("/").split("/")[0].split("?")[0]
            if tail:
                return key, tail if key == "smartrecruiters" else tail.lower()
    workday = workday_board(row.get("careers_url") or "")
    if workday and ats in (None, "workday"):
        return "workday", workday
    return ats, token


_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def workday_board(url: str) -> str | None:
    """"host/site" of a myworkdayjobs.com careers URL, e.g. "medtronic.wd1.myworkdayjobs.com/MedtronicCareers"."""
    parts = urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if not host.endswith(".myworkdayjobs.com"):
        return None
    path = [segment for segment in parts.path.split("/") if segment]
    if path and _LOCALE.match(path[0]):
        path = path[1:]
    return f"{host}/{path[0]}" if path else None


# One request at a time per host, with a pause between them: these are an employer's
# public job APIs, read the way a person paging through them would.
MIN_INTERVAL = 0.4
_host_locks: dict[str, threading.Lock] = {}
_host_last: dict[str, float] = {}
_locks_guard = threading.Lock()


def _polite(url: str):
    host = (urlsplit(url).hostname or "").lower()
    with _locks_guard:
        lock = _host_locks.setdefault(host, threading.Lock())
    lock.acquire()
    wait = _host_last.get(host, 0.0) + MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    return lock, host


def _get_json(url: str, body: dict | None = None):
    """(data, error): a board that cannot be read reports why instead of looking empty."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    lock, host = _polite(url)
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return None, f"HTTP {response.status}"
            return json.loads(response.read().decode("utf-8", errors="replace")), None
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        return None, f"unreachable ({type(exc).__name__})"
    except ValueError:
        return None, "the board returned invalid JSON"
    finally:
        _host_last[host] = time.monotonic()
        lock.release()


def _posting(row, source_id, title, url, location, description, employer_type="company"):
    return {
        "company": row.get("name") or "",
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "url": url or "",
        "requisition_id": str(source_id or ""),
        "description": (description or "").strip(),
        "company_sources": [{"title": f"{row.get('name')} careers", "url": row.get("careers_url", ""), "accessed_at": _today()}],
        # "tracked" (portals.yml) or "sponsor_board" (the USCIS H-1B sponsor-board registry).
        "source": row.get("_source") or "tracked",
        "legal_name": row.get("legal_name") or "",
        "_vouched": row.get("_vouched") or "",
        "legal_presence": row.get("_vouched") or "Posting read from the company's own ATS board (tracked in portals.yml).",
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


def title_worth_opening(title: str) -> bool:
    """An entry-level title in one of Annie's four tracks (the relevance gate's own title tests)."""
    from backend.job_quality import INTERNSHIP, SENIORITY_BLOCK, title_in_tracks
    return title_in_tracks(title) and not SENIORITY_BLOCK.search(title or "") and not INTERNSHIP.search(title or "")


def location_worth_opening(where: str) -> bool:
    """A US location, a bare "Remote", or Workday's "3 Locations" (decided on the posting itself)."""
    from backend.job_quality import is_us_location
    where = where or ""
    return is_us_location(where) or bool(re.fullmatch(r"(?i)\s*(remote|\d+\s+locations?)\s*", where))


# Workday's own search, one phrase per family of roles Annie targets. Each phrase reads
# at most WORKDAY_PAGES pages of 20; at most DETAILS_PER_BOARD postings are opened.
WORKDAY_SEARCHES = ("data engineer", "software engineer", "machine learning", "AI engineer", "analytics",
                    "test engineer", "embedded", "automation engineer", "associate engineer", "new graduate")
WORKDAY_PAGES = 2
DETAILS_PER_BOARD = 30


def _workday_jobs(row: dict[str, Any], token: str, title_ok: Callable[[str], bool]) -> tuple[list[dict[str, Any]], str | None]:
    host, site = token.split("/", 1)
    tenant = host.split(".")[0]
    seen: dict[str, dict] = {}
    error = None
    for phrase in WORKDAY_SEARCHES:
        for page in range(WORKDAY_PAGES):
            data, error = _get_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                                    {"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": phrase})
            if not isinstance(data, dict):
                if not seen:
                    return [], error or "the board returned no listing"
                break
            batch = data.get("jobPostings") or []
            for item in batch:
                path = str(item.get("externalPath") or "")
                if path and path not in seen:
                    seen[path] = item
            if len(batch) < 20:
                break
    out: list[dict[str, Any]] = []
    opened = 0
    for path, item in seen.items():
        title, where = str(item.get("title") or ""), str(item.get("locationsText") or "")
        if not title_ok(title) or not location_worth_opening(where):
            continue
        if opened >= DETAILS_PER_BOARD:
            break
        opened += 1
        data, _ = _get_json(f"https://{host}/wday/cxs/{tenant}/{site}{path}")
        info = (data or {}).get("jobPostingInfo") if isinstance(data, dict) else None
        if not isinstance(info, dict) or not info.get("jobDescription"):
            continue
        places = [str(info.get("location") or "")] + [str(p) for p in info.get("additionalLocations") or []]
        country = ((info.get("country") or {}).get("descriptor") or "") if isinstance(info.get("country"), dict) else ""
        location = "; ".join(p for p in places if p)
        if country and country.casefold() not in location.casefold():
            location = f"{location}, {country}" if location else country
        posting = _posting(row, info.get("jobReqId") or path, info.get("title") or title,
                           str(info.get("externalUrl") or f"https://{host}/{site}{path}"), location,
                           html_to_text(info.get("jobDescription") or ""))
        posting["posted_at"] = str(info.get("startDate") or "")
        out.append(posting)
    return out, None


def _smartrecruiters_jobs(row: dict[str, Any], token: str, title_ok: Callable[[str], bool]) -> tuple[list[dict[str, Any]], str | None]:
    listing: list[dict] = []
    for offset in range(0, 400, 100):
        data, error = _get_json(f"https://api.smartrecruiters.com/v1/companies/{quote(token)}/postings"
                                f"?country=us&limit=100&offset={offset}")
        if not isinstance(data, dict):
            if not listing:
                return [], error or "the board returned no listing"
            break
        batch = data.get("content") or []
        listing.extend(batch)
        if len(batch) < 100 or offset + 100 >= int(data.get("totalFound") or 0):
            break
    out: list[dict[str, Any]] = []
    opened = 0
    for item in listing:
        if not title_ok(str(item.get("name") or "")):
            continue
        if opened >= DETAILS_PER_BOARD:
            break
        opened += 1
        posting_id = str(item.get("id") or "")
        data, _ = _get_json(f"https://api.smartrecruiters.com/v1/companies/{quote(token)}/postings/{quote(posting_id)}")
        if not isinstance(data, dict):
            continue
        sections = ((data.get("jobAd") or {}).get("sections") or {})
        parts = []
        for key in ("jobDescription", "qualifications", "additionalInformation"):
            section = sections.get(key) or {}
            if section.get("text"):
                parts.append((section.get("title") or "") + "\n" + html_to_text(section["text"]))
        description = "\n\n".join(part.strip() for part in parts if part.strip())
        if not description:
            continue
        place = data.get("location") or {}
        where = str(place.get("fullLocation") or ", ".join(
            str(place.get(k) or "") for k in ("city", "region", "country") if place.get(k)))
        if place.get("remote"):
            where = "Remote, " + where
        url = str(data.get("postingUrl") or f"https://jobs.smartrecruiters.com/{token}/{posting_id}")
        posting = _posting(row, data.get("refNumber") or posting_id, data.get("name") or item.get("name"), url, where, description)
        posting["posted_at"] = str(data.get("releasedDate") or "")
        out.append(posting)
    return out, None


def fetch_board(row: dict[str, Any], title_ok: Callable[[str], bool] | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """(postings, error). ``error`` is None on success, even an empty board."""
    ats, token = board_token(row)
    if not ats or not token:
        return [], None
    if ats == "workday":
        return _workday_jobs(row, token, title_ok or title_worth_opening)
    if ats == "smartrecruiters":
        return _smartrecruiters_jobs(row, token, title_ok or title_worth_opening)
    out: list[dict[str, Any]] = []
    error: str | None = None
    if ats == "greenhouse":
        data, error = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
        for job in (data or {}).get("jobs", []) or []:
            out.append(_posting(row, job.get("id"), job.get("title"), job.get("absolute_url"),
                                ((job.get("location") or {}).get("name") or ""), html_to_text(job.get("content") or "")))
    elif ats == "lever":
        data, error = _get_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        for job in data or []:
            cats = job.get("categories") or {}
            body = job.get("descriptionPlain") or html_to_text(job.get("description") or "")
            for lst in job.get("lists") or []:
                body += "\n\n" + (lst.get("text") or "") + "\n" + html_to_text(lst.get("content") or "")
            out.append(_posting(row, job.get("id"), job.get("text"), job.get("hostedUrl") or job.get("applyUrl"),
                                cats.get("location") or "", body))
    elif ats == "ashby":
        data, error = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true")
        for job in (data or {}).get("jobs", []) or []:
            out.append(_posting(row, job.get("id") or job.get("jobId"), job.get("title"), job.get("jobUrl") or job.get("applyUrl"),
                                job.get("location") or "", job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml") or "")))
    return out, error


def fetch_rows(rows: list[dict[str, Any]], limit_per_board: int | None = None,
               workers: int = 6) -> list[tuple[dict[str, Any], list[dict[str, Any]], str | None, str]]:
    """Read these boards in parallel: (row, postings, error, coverage note) per row, in order."""

    def read(row):
        ats, token = board_token(row)
        if not ats or not token:
            return row, [], None, f"{row.get('name')}: no public ATS feed configured (careers page only)"
        try:
            found, error = fetch_board(row)
        except Exception as exc:  # noqa: BLE001 - one odd board must never stop the pass
            found, error = [], f"{type(exc).__name__}: {exc}"[:160]
        if error:
            return row, [], error, f"{row.get('name')}: FETCH FAILED ({error}) via {ats}"
        noun = "matching postings opened" if ats in ("workday", "smartrecruiters") else "open postings"
        found = found[:limit_per_board] if limit_per_board else found
        return row, found, None, f"{row.get('name')}: {len(found)} {noun} via {ats}"

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(read, rows))


def fetch_all(limit_per_board: int | None = None, workers: int = 6,
              rows: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """Every open posting on every tracked board that has an ATS feed, plus a coverage note per board.

    Boards are read in parallel; the result keeps portals.yml order (cap-exempt first)."""
    postings: list[dict[str, Any]] = []
    coverage: list[str] = []
    for _row, found, _error, note in fetch_rows(tracked_companies() if rows is None else rows, limit_per_board, workers):
        postings.extend(found)
        coverage.append(note)
    return postings, coverage
