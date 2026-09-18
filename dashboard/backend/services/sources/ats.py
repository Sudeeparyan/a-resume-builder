"""
Company ATS boards: Greenhouse, Lever, Ashby.

These are the best source in the whole system. They are free, need no key, are
never stale, and a company's own board carries a role days before it reaches an
aggregator -- which matters at entry level, where a posting under 48 hours old
scores +10 and competition is the second-heaviest ranking factor.

The tracked company list lives in system/config/portals.yml and grows over time.
"""

from __future__ import annotations

from typing import Any

import httpx
import yaml

from ... import paths
from ...models import JobPosting
from .base import Source, html_to_text


def tracked_companies(enabled_only: bool = True) -> list[dict[str, Any]]:
    """Read portals.yml. Returns [] rather than raising if it is missing."""
    try:
        data = yaml.safe_load(paths.read_text(paths.PORTALS_YML)) or {}
    except yaml.YAMLError:
        return []
    rows = data.get("tracked_companies") or []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if enabled_only and not r.get("enabled", True):
            continue
        out.append(r)
    # Cap-exempt employers first: they can file for her any time of year with no
    # lottery, which is the single biggest structural advantage available.
    out.sort(key=lambda r: (not r.get("cap_exempt", False), r.get("name", "")))
    return out


def _board_token(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """(ats, token) from an explicit field, else inferred from the careers URL."""
    ats = (row.get("ats") or "").strip().lower() or None
    token = (row.get("ats_token") or "").strip() or None
    if ats and token:
        return ats, token

    url = (row.get("careers_url") or "").lower()
    for key, marker in (
        ("greenhouse", "boards.greenhouse.io/"),
        ("greenhouse", "job-boards.greenhouse.io/"),
        ("lever", "jobs.lever.co/"),
        ("ashby", "jobs.ashbyhq.com/"),
    ):
        if marker in url:
            tail = url.split(marker, 1)[1].strip("/").split("/")[0].split("?")[0]
            if tail:
                return key, tail
    return ats, token


class GreenhouseSource(Source):
    name = "greenhouse"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        for row in tracked_companies():
            ats, token = _board_token(row)
            if ats != "greenhouse" or not token:
                continue
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue

            for j in data.get("jobs", []) or []:
                loc = ((j.get("location") or {}).get("name") or "").strip()
                out.append(self._post(
                    source_id=str(j.get("id")),
                    company=row.get("name") or token,
                    title=j.get("title") or "",
                    url=j.get("absolute_url") or "",
                    location=loc,
                    jd=html_to_text(j.get("content") or ""),
                    posted=j.get("updated_at") or j.get("first_published"),
                    department=", ".join(
                        d.get("name", "") for d in (j.get("departments") or [])
                    ),
                    raw={"cap_exempt": row.get("cap_exempt", False), "tier_hint": row.get("tier")},
                ))
        return out


class LeverSource(Source):
    name = "lever"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        for row in tracked_companies():
            ats, token = _board_token(row)
            if ats != "lever" or not token:
                continue
            try:
                r = await client.get(f"https://api.lever.co/v0/postings/{token}?mode=json")
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue

            for j in data or []:
                cats = j.get("categories") or {}
                body = j.get("descriptionPlain") or html_to_text(j.get("description") or "")
                for lst in j.get("lists") or []:
                    body += "\n\n" + (lst.get("text") or "") + "\n" + html_to_text(lst.get("content") or "")
                out.append(self._post(
                    source_id=str(j.get("id")),
                    company=row.get("name") or token,
                    title=j.get("text") or "",
                    url=j.get("hostedUrl") or j.get("applyUrl") or "",
                    location=cats.get("location") or "",
                    jd=body.strip(),
                    posted=j.get("createdAt"),
                    department=cats.get("team") or "",
                    raw={"cap_exempt": row.get("cap_exempt", False), "tier_hint": row.get("tier")},
                ))
        return out


class AshbySource(Source):
    name = "ashby"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        for row in tracked_companies():
            ats, token = _board_token(row)
            if ats != "ashby" or not token:
                continue
            url = (
                f"https://api.ashbyhq.com/posting-api/job-board/{token}"
                "?includeCompensation=true"
            )
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue

            for j in data.get("jobs", []) or []:
                out.append(self._post(
                    source_id=str(j.get("id") or j.get("jobId")),
                    company=row.get("name") or token,
                    title=j.get("title") or "",
                    url=j.get("jobUrl") or j.get("applyUrl") or "",
                    location=j.get("location") or "",
                    jd=j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml") or ""),
                    posted=j.get("publishedAt") or j.get("updatedAt"),
                    department=j.get("department") or j.get("team") or "",
                    raw={"cap_exempt": row.get("cap_exempt", False), "tier_hint": row.get("tier")},
                ))
        return out


ALL = [GreenhouseSource(), LeverSource(), AshbySource()]
