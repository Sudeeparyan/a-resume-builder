"""
Aggregator feeds and the workspace importer.

Remotive, Arbeitnow and RemoteOK need no key at all. USAJobs is free and is the
only way to reach federal roles, many of which sit at cap-exempt institutions.
Adzuna is broad but needs a one-time signup, so it stays off until she adds the
credentials in Settings.

The workspace importer is the bridge back to Claude Code: /hunt writes
output/SUMMARY.md and system/data/applications.tsv, and anything found there
appears in the dashboard rather than being invisible to it.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from ... import legacy, paths, settings
from ...models import JobPosting
from .base import Source, html_to_text, is_us


class RemotiveSource(Source):
    name = "remotive"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        for category in ("software-dev", "data"):
            try:
                r = await client.get(
                    "https://remotive.com/api/remote-jobs",
                    params={"category": category, "limit": 120},
                )
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue
            for j in data.get("jobs", []) or []:
                loc = j.get("candidate_required_location") or ""
                if not _location_ok(loc):
                    continue
                out.append(self._post(
                    source_id=str(j.get("id")),
                    company=j.get("company_name") or "",
                    title=j.get("title") or "",
                    url=j.get("url") or "",
                    location=loc,
                    jd=html_to_text(j.get("description") or ""),
                    posted=j.get("publication_date"),
                    department=j.get("category") or "",
                ))
        return out


class ArbeitnowSource(Source):
    name = "arbeitnow"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        try:
            r = await client.get("https://www.arbeitnow.com/api/job-board-api")
            if r.status_code != 200:
                return out
            data = r.json()
        except Exception:  # noqa: BLE001
            return out
        for j in data.get("data", []) or []:
            loc = j.get("location") or ""
            if not is_us(loc) and not j.get("remote"):
                continue
            out.append(self._post(
                source_id=str(j.get("slug")),
                company=j.get("company_name") or "",
                title=j.get("title") or "",
                url=j.get("url") or "",
                location=loc,
                jd=html_to_text(j.get("description") or ""),
                posted=j.get("created_at"),
                department=", ".join(j.get("tags") or []),
            ))
        return out


class RemoteOKSource(Source):
    name = "remoteok"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        try:
            r = await client.get("https://remoteok.com/api")
            if r.status_code != 200:
                return out
            data = r.json()
        except Exception:  # noqa: BLE001
            return out
        for j in data or []:
            if not isinstance(j, dict) or not j.get("position"):
                continue          # the first element is a legal notice, not a job
            loc = j.get("location") or "Remote"
            if not _location_ok(loc):
                continue
            out.append(self._post(
                source_id=str(j.get("id") or j.get("slug")),
                company=j.get("company") or "",
                title=j.get("position") or "",
                url=j.get("url") or j.get("apply_url") or "",
                location=loc,
                jd=html_to_text(j.get("description") or ""),
                posted=j.get("date") or j.get("epoch"),
                department=", ".join(j.get("tags") or []),
            ))
        return out


class USAJobsSource(Source):
    """
    Federal roles. Free, but the API wants an email as the User-Agent. Many
    federal and federally-funded employers are cap-exempt.
    """

    name = "usajobs"
    needs_key = True

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        cfg = settings.get_settings()
        if not cfg.enable_usajobs or not cfg.usajobs_email:
            return []
        out: list[JobPosting] = []
        titles = kw.get("titles") or ["Data Engineer", "Software Engineer"]
        for title in titles[:4]:
            try:
                r = await client.get(
                    "https://data.usajobs.gov/api/search",
                    params={"Keyword": title, "ResultsPerPage": 50},
                    headers={"User-Agent": cfg.usajobs_email, "Host": "data.usajobs.gov"},
                )
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue
            for item in (data.get("SearchResult", {}).get("SearchResultItems") or []):
                d = item.get("MatchedObjectDescriptor") or {}
                ud = d.get("UserArea", {}).get("Details", {}) or {}
                jd = "\n\n".join(filter(None, [
                    d.get("QualificationSummary") or "",
                    ud.get("JobSummary") or "",
                    ud.get("MajorDuties") and " ".join(ud["MajorDuties"]) or "",
                ]))
                locs = d.get("PositionLocation") or []
                out.append(self._post(
                    source_id=str(d.get("PositionID")),
                    company=d.get("OrganizationName") or "",
                    title=d.get("PositionTitle") or "",
                    url=d.get("PositionURI") or "",
                    location=(locs[0].get("LocationName") if locs else "") or "",
                    jd=html_to_text(jd),
                    posted=d.get("PublicationStartDate"),
                ))
        return out


class AdzunaSource(Source):
    name = "adzuna"
    needs_key = True

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        cfg = settings.get_settings()
        if not (cfg.enable_adzuna and cfg.adzuna_app_id and cfg.adzuna_app_key):
            return []
        out: list[JobPosting] = []
        titles = kw.get("titles") or ["data engineer", "software engineer"]
        for title in titles[:5]:
            try:
                r = await client.get(
                    "https://api.adzuna.com/v1/api/jobs/us/search/1",
                    params={
                        "app_id": cfg.adzuna_app_id,
                        "app_key": cfg.adzuna_app_key,
                        "results_per_page": 50,
                        "what": title,
                        "max_days_old": 30,
                        "content-type": "application/json",
                    },
                )
                if r.status_code != 200:
                    continue
                data = r.json()
            except Exception:  # noqa: BLE001
                continue
            for j in data.get("results", []) or []:
                out.append(self._post(
                    source_id=str(j.get("id")),
                    company=(j.get("company") or {}).get("display_name") or "",
                    title=j.get("title") or "",
                    url=j.get("redirect_url") or "",
                    location=(j.get("location") or {}).get("display_name") or "",
                    jd=html_to_text(j.get("description") or ""),
                    posted=j.get("created"),
                    department=(j.get("category") or {}).get("label") or "",
                ))
        return out


_ROW_RE = re.compile(r"^\|\s*(\d+)?\s*\|(.+)\|\s*$")

# Must match workspace_sync._SHORTLIST_HEADING -- the two are a pair.
_SHORTLIST_HEADING = "## Companies found, no resume yet"


def _shortlist_block(text: str) -> str:
    """
    Only the shortlist table, never the rest of the page.

    SUMMARY.md holds five markdown tables: resumes built, the pipeline, the
    shortlist, the exclusions, and the explainer of the sponsorship tiers. Read
    every "|" line in the file and the *header row* of those other tables turns
    into a job -- "| Company | Role | Why | Triggering sentence |" yields a
    company called "Role" applying for a job called "Why". Those get scored,
    excluded, and written back into the exclusions table, which produces the
    same garbage again on the next scan. Scoping to one section breaks the loop.
    """
    if _SHORTLIST_HEADING not in text:
        return ""
    return text.split(_SHORTLIST_HEADING, 1)[1].split("\n## ", 1)[0]


_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")


class WorkspaceSource(Source):
    """
    Everything /hunt already found.

    The Indeed connector is unreachable from this process, so roles discovered
    inside a Claude Code session would otherwise be invisible here. This reads
    them out of SUMMARY.md and applications.tsv instead.
    """

    name = "workspace"

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        out: list[JobPosting] = []
        seen: set[tuple[str, str]] = set()

        for row in legacy.load_applications():
            company, title = (row.get("company") or "").strip(), (row.get("role_title") or "").strip()
            if not company or not title:
                continue
            key = (company.lower(), title.lower())
            if key in seen:
                continue
            seen.add(key)
            folder = (row.get("folder") or "").strip()
            jd = ""
            if folder:
                jd = paths.read_text(paths.OUTPUT / folder / "job-description.txt")
            out.append(self._post(
                source_id=row.get("app_id") or f"{company}-{title}",
                company=company, title=title,
                url=row.get("job_url") or "",
                jd=jd,
                raw={"tracked": True, "status": row.get("status"),
                     "tier_hint": row.get("sponsor_tier")},
            ))

        for line in _shortlist_block(paths.read_text(paths.SUMMARY)).splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or set(cells[0]) <= set("-: "):
                continue
            company = re.sub(r"\*\*(.+?)\*\*", r"\1", cells[1]).strip() if len(cells) > 1 else ""
            title = cells[2].strip() if len(cells) > 2 else ""
            if not company or not title or company.lower() in ("company", "#"):
                continue
            key = (company.lower(), title.lower())
            if key in seen:
                continue
            seen.add(key)
            link = ""
            for cell in cells:
                m = _LINK_RE.search(cell)
                if m:
                    link = m.group(2)
                    break
            out.append(self._post(
                source_id=f"summary-{company}-{title}",
                company=company, title=title, url=link,
                raw={"from_summary": True},
            ))
        return out


def _location_ok(loc: str) -> bool:
    low = (loc or "").lower()
    if "usa" in low or "united states" in low or "us only" in low:
        return True
    if "worldwide" in low or "anywhere" in low:
        return True
    return is_us(loc)


FREE = [RemotiveSource(), ArbeitnowSource(), RemoteOKSource()]
KEYED = [USAJobsSource(), AdzunaSource()]
WORKSPACE = [WorkspaceSource()]
