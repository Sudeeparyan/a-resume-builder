"""
Find a company's job board automatically.

portals.yml pins an ATS and a token per company, and those go stale: Confluent
is listed as Greenhouse and 404s there, because they moved to Ashby where they
have 22 open roles. A pinned token is a silent zero -- the scan reports success
and finds nothing.

So: given a company name, probe the three ATSs for plausible tokens, keep what
answers, and cache it. Discovery is what lets the tracked list grow to hundreds
of employers without anyone hand-editing YAML -- which matters most for
cap-exempt employers, who file H-1B year-round with no lottery and are indexed
badly by every aggregator.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from ... import db
from .base import HEADERS

_CACHE_TTL_DAYS = 14


def token_candidates(company: str) -> list[str]:
    """Plausible board slugs for a company name, most likely first."""
    name = (company or "").strip().lower()
    if not name:
        return []
    name = re.sub(r"[.,]", "", name)
    name = re.sub(r"\b(inc|llc|ltd|corp|corporation|company|co|plc|the)\b", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    compact = re.sub(r"[^a-z0-9]", "", name)
    hyphen = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    first = name.split(" ")[0] if name else ""

    out = [compact, hyphen, first]
    # Universities and institutes are usually initialised on their boards.
    words = [w for w in name.split() if w not in ("of", "and", "for", "at")]
    if len(words) > 1:
        out.append("".join(w[0] for w in words))
    out.append(compact + "careers")
    seen, uniq = set(), []
    for t in out:
        if t and 2 <= len(t) <= 40 and t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


PROBES = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{t}/jobs",
    "lever": "https://api.lever.co/v0/postings/{t}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{t}",
}


def _count(ats: str, payload: Any) -> int:
    if ats == "lever":
        return len(payload) if isinstance(payload, list) else 0
    if isinstance(payload, dict):
        return len(payload.get("jobs") or [])
    return 0


async def probe_company(
    client: httpx.AsyncClient, company: str, hint_ats: str | None = None,
    hint_token: str | None = None,
) -> dict[str, Any] | None:
    """Return {company, ats, token, jobs} for the first board that answers."""
    tried: list[tuple[str, str]] = []
    if hint_ats and hint_token:
        tried.append((hint_ats, hint_token))
    for tok in token_candidates(company):
        for ats in ("greenhouse", "lever", "ashby"):
            if (ats, tok) not in tried:
                tried.append((ats, tok))

    for ats, tok in tried[:18]:
        url = PROBES[ats].format(t=tok)
        try:
            r = await client.get(url)
        except Exception:  # noqa: BLE001
            continue
        if r.status_code != 200:
            continue
        try:
            payload = r.json()
        except ValueError:
            continue
        n = _count(ats, payload)
        if n > 0:
            return {"company": company, "ats": ats, "token": tok, "jobs": n}
    return None


def cache_get(company: str) -> dict[str, Any] | None:
    row = db.kv_get(f"board:{company.strip().lower()}")
    if not row:
        return None
    from datetime import datetime, timedelta

    try:
        found = datetime.fromisoformat(row.get("at", ""))
    except ValueError:
        return None
    if datetime.now() - found > timedelta(days=_CACHE_TTL_DAYS):
        return None
    return row


def cache_put(company: str, result: dict[str, Any] | None) -> None:
    db.kv_set(
        f"board:{company.strip().lower()}",
        {**(result or {"ats": None, "token": None}), "at": db.now()},
    )


async def discover(
    companies: list[str], *, concurrency: int = 4, use_cache: bool = True
) -> list[dict[str, Any]]:
    """Resolve boards for many companies. Cached results cost nothing."""
    out: list[dict[str, Any]] = []
    todo: list[str] = []

    for c in companies:
        cached = cache_get(c) if use_cache else None
        if cached and cached.get("token"):
            out.append({
                "company": c, "ats": cached["ats"], "token": cached["token"],
                "jobs": cached.get("jobs", 0), "cached": True,
            })
        elif cached and use_cache:
            continue                     # known to have no board; do not re-probe
        else:
            todo.append(c)

    if todo:
        sem = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:

            async def one(name: str) -> None:
                async with sem:
                    res = await probe_company(client, name)
                    cache_put(name, res)
                    if res:
                        out.append({**res, "cached": False})

            await asyncio.gather(*(one(c) for c in todo))

    return out
