"""
Job sources: shared plumbing.

The existing skills find jobs through the Indeed MCP connector, which only
exists inside a Claude Code session. A standalone FastAPI process cannot reach
it, so the dashboard sources jobs itself from endpoints that need no key, and
separately imports whatever /hunt already produced.

Never synthesise an apply URL. Every posting carries the link its source gave
us, and anything we could not verify is labelled rather than presented as live.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from ...models import JobPosting

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")


def html_to_text(raw: str) -> str:
    """
    JD text for the sponsorship gate and the keyword scorer.

    Greenhouse returns content that is HTML-ESCAPED HTML: the payload contains
    &lt;li&gt; rather than <li>. Unescaping once yields real tags, so tags must
    be stripped AFTER unescaping, and the whole cycle repeated -- otherwise
    markup leaks into the verbatim triggering sentence we show the user, which
    is the one string that has to be clean.
    """
    import html as _html

    if not raw:
        return ""
    s = raw
    for _ in range(3):
        before = s
        s = _html.unescape(s)
        s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
        s = re.sub(r"(?i)<br\s*/?>", "\n", s)
        s = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|ul|ol)\s*>", "\n", s)
        s = re.sub(r"(?i)<li[^>]*>", "\n- ", s)
        s = _TAG_RE.sub(" ", s)
        if s == before:
            break

    s = s.replace("\xa0", " ").replace("​", "")
    s = _WS_RE.sub(" ", s)
    s = "\n".join(line.strip() for line in s.splitlines())
    return _NL_RE.sub("\n\n", s).strip()


def parse_date(value: Any) -> datetime | None:
    if value in (None, "", 0):
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e11:            # milliseconds
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    s = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s.replace("+00:00", "Z" if fmt.endswith("Z") else "+00:00"), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def content_hash(company: str, title: str, jd: str) -> str:
    basis = f"{company.strip().lower()}|{title.strip().lower()}|{(jd or '')[:2000].strip().lower()}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def is_us(location: str) -> bool:
    """
    US-only is a confirmed hard preference. Absence of a country is treated as
    US when the source is US-scoped; a named non-US country is a drop.
    """
    if not location:
        return True
    low = location.lower()
    non_us = (
        "united kingdom", "london", "ireland", "dublin", "germany", "berlin",
        "france", "paris", "spain", "netherlands", "amsterdam", "poland",
        "canada", "toronto", "vancouver", "india", "bangalore", "hyderabad",
        "australia", "sydney", "singapore", "japan", "tokyo", "china",
        "brazil", "mexico", "israel", "tel aviv", "sweden", "switzerland",
        "zurich", "portugal", "lisbon", "romania", "ukraine", "emea", "apac",
    )
    if any(k in low for k in non_us):
        # A named non-US country wins, UNLESS the string also names the US --
        # multi-site postings read "London, UK / Austin, United States".
        return any(k in low for k in ("united states", ", us", "usa", "(us)", " us "))
    return True


def looks_remote(location: str, extra: str = "") -> bool:
    blob = f"{location} {extra}".lower()
    return "remote" in blob or "anywhere" in blob or "distributed" in blob


class Source:
    """One place jobs come from."""

    name: str = "base"
    needs_key: bool = False

    async def fetch(self, client: httpx.AsyncClient, **kw: Any) -> list[JobPosting]:
        raise NotImplementedError

    def _post(
        self, *, source_id: str, company: str, title: str, url: str,
        location: str = "", jd: str = "", posted: Any = None,
        department: str = "", raw: dict | None = None,
    ) -> JobPosting:
        return JobPosting(
            source=self.name,
            source_id=str(source_id),
            company=company.strip(),
            role_title=title.strip(),
            url=url,
            location=location.strip(),
            remote=looks_remote(location, title),
            posted_at=parse_date(posted),
            jd_text=jd,
            department=department,
            content_hash=content_hash(company, title, jd),
            raw=raw or {},
        )


async def gather_sources(
    sources: Iterable[Source], *, timeout: float = 25.0, concurrency: int = 6, **kw: Any
) -> tuple[list[JobPosting], list[dict[str, Any]]]:
    """
    Run every source concurrently. A source that fails is reported, never fatal --
    one dead job board must not take the scan down.
    """
    results: list[JobPosting] = []
    report: list[dict[str, Any]] = []
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=timeout, follow_redirects=True
    ) as client:

        async def run(src: Source) -> None:
            async with sem:
                try:
                    got = await src.fetch(client, **kw)
                    results.extend(got)
                    report.append({"source": src.name, "ok": True, "count": len(got)})
                except Exception as exc:  # noqa: BLE001
                    report.append({
                        "source": src.name, "ok": False, "count": 0,
                        "error": f"{type(exc).__name__}: {exc}"[:200],
                    })

        await asyncio.gather(*(run(s) for s in sources))

    return results, report
