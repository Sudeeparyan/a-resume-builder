"""
The agents that need no model.

These are the whole product in no-key mode, and they are the parts that must
never be wrong: the sponsorship gate, never-re-apply, link verification, and
track classification. None of them can hallucinate, and each one reports the
evidence for its own verdict so a wrong call is visible and correctable.
"""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urlparse

import yaml

from .. import legacy, paths, settings
from ..models import (
    ExcludedJob, JobPosting, LinkStatus, SponsorVerdict, Tier, TrackId,
)
from ..services import context_loader, scoring
from ..services.sponsor_index import lookup as sponsor_lookup


# --------------------------------------------------------------------------
# dedupe
# --------------------------------------------------------------------------
def dedupe(postings: Iterable[JobPosting]) -> tuple[list[JobPosting], int]:
    """
    One posting per (company, title). Aggregators repost the same role many
    times; keeping the copy with the most JD text keeps the gate accurate,
    because the gate can only see what the text says.
    """
    best: dict[tuple[str, str], JobPosting] = {}
    dropped = 0
    for p in postings:
        key = (legacy.normalize_company(p.company), re.sub(r"\s+", " ", p.role_title.strip().lower()))
        if not key[0] or not key[1]:
            dropped += 1
            continue
        prev = best.get(key)
        if prev is None:
            best[key] = p
            continue
        dropped += 1
        # Prefer a direct ATS posting, then whichever carries more JD text.
        rank = {"greenhouse": 0, "lever": 0, "ashby": 0, "workspace": 1}
        if (rank.get(p.source, 2), -len(p.jd_text)) < (rank.get(prev.source, 2), -len(prev.jd_text)):
            best[key] = p
    return list(best.values()), dropped


# --------------------------------------------------------------------------
# hard filters, before any scoring
# --------------------------------------------------------------------------
# The four tracks she is actually targeting, from 07-preferences.md. A broad
# aggregator returns hotel porters and electricians alongside data roles, so a
# relevance test has to come before anything expensive runs.
RELEVANT_TITLE = re.compile(
    r"\b("
    r"data|analytics|analyst|etl|elt|warehouse|lakehouse|pipeline|"
    r"machine\s*learning|ml|ai|artificial\s*intelligence|deep\s*learning|nlp|"
    r"computer\s*vision|mlops|research\s*(engineer|scientist)|applied\s*scientist|"
    r"software|sde|swe|developer|programmer|backend|back-end|full[\s-]?stack|platform|"
    r"embedded|firmware|fpga|hardware|verification|validation|v&v|sdet|"
    r"test\s*(automation|engineer)|qa\s*engineer|quality\s*engineer|"
    r"python|java|c\+\+|devops|cloud|infrastructure|database|bi\b"
    r")\b",
    re.I,
)
# An engineer of the wrong kind is still the wrong kind.
IRRELEVANT_TITLE = re.compile(
    r"\b("
    r"sales|account\s*(executive|manager)|recruiter|recruiting|talent|"
    r"marketing|customer\s*success|support\s*(agent|specialist)|"
    r"attendant|housekeep|kitchen|chef|cook|server|bartender|host(ess)?|"
    r"nurse|physician|therapist|driver|warehouse\s*associate|janitor|cleaner|"
    r"electrician|plumber|welder|wireperson|mechanic|technician\s*-\s*hvac|"
    r"teacher|tutor|counselor|social\s*worker|paralegal|attorney|"
    r"civil|mechanical\s*engineer|structural|chemical\s*engineer"
    r")\b",
    re.I,
)


def title_is_relevant(title: str, department: str = "") -> tuple[bool, str]:
    t = (title or "").strip()
    if not t:
        return False, "no job title"
    m = IRRELEVANT_TITLE.search(t)
    if m:
        return False, f"'{m.group(0)}' is a different field"
    if RELEVANT_TITLE.search(t) or RELEVANT_TITLE.search(department or ""):
        return True, ""
    return False, "the title does not match any of your four target tracks"


def hard_filter(postings: list[JobPosting]) -> tuple[list[JobPosting], list[ExcludedJob]]:
    """
    The filters from _profile.md that are not about sponsorship: relevance,
    seniority, years demanded, and the US-only rule.
    """
    kept: list[JobPosting] = []
    cut: list[ExcludedJob] = []

    for p in postings:
        relevant, why = title_is_relevant(p.role_title, p.department)
        if not relevant:
            cut.append(ExcludedJob(
                company=p.company, role_title=p.role_title, url=p.url, stage="filter",
                why=f"Not one of your target roles — {why}.",
                triggering_sentence=p.role_title,
            ))
            continue

        too_senior, why = scoring.title_is_too_senior(p.role_title)
        if too_senior:
            cut.append(ExcludedJob(
                company=p.company, role_title=p.role_title, url=p.url, stage="filter",
                why=f"Above her level — {why}.",
                triggering_sentence=p.role_title,
            ))
            continue

        yrs = scoring.years_required(p.jd_text)
        if yrs is not None and yrs > 4:
            m = scoring._YEARS_RE.search(p.jd_text)
            cut.append(ExcludedJob(
                company=p.company, role_title=p.role_title, url=p.url, stage="filter",
                why=f"Asks for {yrs} years of experience (the limit is 4).",
                triggering_sentence=(m.group(0) if m else "")[:300],
            ))
            continue

        from ..services.sources.base import is_us
        if not is_us(p.location) and not p.remote:
            cut.append(ExcludedJob(
                company=p.company, role_title=p.role_title, url=p.url, stage="filter",
                why="Outside the United States.",
                triggering_sentence=p.location,
            ))
            continue

        kept.append(p)
    return kept, cut


# --------------------------------------------------------------------------
# the sponsorship gate -- the rule that governs everything
# --------------------------------------------------------------------------
def sponsorship_gate(posting: JobPosting) -> SponsorVerdict:
    """
    Two steps, because screen() only ever returns A or EXCLUDED:
      1. screen the JD text for an explicit refusal or a cannot-hire requirement
      2. resolve S/B/C from the company -- cap-exempt, then H-1B history

    Silence is a KEEP. "Must be authorized to work in the United States" is not
    a refusal: she is authorized. Absence of an H-1B record never excludes.
    """
    result = legacy.screen_jd(posting.jd_text)

    domain = ""
    try:
        domain = urlparse(posting.url).netloc.lower()
    except ValueError:
        pass

    is_cap, cap_why = legacy.cap_exempt(posting.company, domain)
    if not is_cap and posting.raw.get("cap_exempt"):
        is_cap, cap_why = True, "listed as cap-exempt in the tracked-company list"

    history = sponsor_lookup(posting.company)
    approvals = int(history.get("approvals") or 0)

    tier = scoring.resolve_tier(result, cap_exempt=is_cap, approvals=approvals)

    return SponsorVerdict(
        verdict=result.get("verdict", "KEEP"),
        tier=tier,
        reason=result.get("reason", "silent"),
        reason_label=result.get("reason_label", ""),
        triggering_sentence=result.get("sentence"),
        pattern=result.get("pattern"),
        everify=bool(result.get("everify")),
        cap_exempt=is_cap,
        cap_exempt_why=cap_why or None,
        h1b_approvals=approvals,
        h1b_years=list(history.get("years") or []),
        h1b_matched_name=history.get("matched_name"),
        evidence=result.get("evidence") or [],
    )


# --------------------------------------------------------------------------
# never re-apply
# --------------------------------------------------------------------------
class TrackerGate:
    """
    Same company + same role -> never surfaced again, at any status.
    A company that rejected her -> suppressed 180 days.
    Ghosted -> the company is eligible again after 90 days for a DIFFERENT role.
    """

    def __init__(self) -> None:
        legacy.refresh_today()
        self.pairs, self.companies, self.reasons = legacy.exclusions()
        self._why: dict[str, str] = {}
        for r in self.reasons:
            name, _, rest = r.partition(":")
            self._why[legacy.track.norm(name)] = rest.strip()

    def blocked(self, company: str, role: str) -> tuple[bool, str]:
        c = legacy.track.norm(company)
        r = legacy.track.norm(role)
        if (c, r) in self.pairs:
            return True, "You have already applied to this exact role here."
        if c in self.companies:
            return True, self._why.get(c, "This company is in a cooldown period.")
        return False, ""

    def split(self, postings: list[JobPosting]) -> tuple[list[JobPosting], list[ExcludedJob]]:
        kept, cut = [], []
        for p in postings:
            is_blocked, why = self.blocked(p.company, p.role_title)
            if is_blocked:
                cut.append(ExcludedJob(
                    company=p.company, role_title=p.role_title, url=p.url,
                    stage="tracker", why=why, triggering_sentence=None,
                ))
            else:
                kept.append(p)
        return kept, cut


# --------------------------------------------------------------------------
# link verification
# --------------------------------------------------------------------------
# Hosts that refuse non-browser traffic. A failed fetch here says nothing about
# whether the job is open, so calling it BROKEN would silently drop real roles --
# and the Indeed short links in SUMMARY.md point at exactly these. The honest
# status is "open it yourself", which is kept and labelled rather than dropped.
BOT_BLOCKING_HOSTS = (
    "indeed.com", "to.indeed.com", "linkedin.com", "glassdoor.com",
    "ziprecruiter.com", "dice.com", "monster.com", "myworkdayjobs.com",
)


def _blocks_bots(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return any(host == h or host.endswith("." + h) for h in BOT_BLOCKING_HOSTS)


async def verify_links(
    postings: list[JobPosting], *, concurrency: int = 4, per_host_delay: float = 2.0,
    progress=None,
) -> dict[str, LinkStatus]:
    """
    verify_job_url.check() is synchronous and its CLI sleeps 6s globally, which
    would be four minutes for forty links. Running it in a thread pool with a
    per-host delay is both faster and more polite: the courtesy that matters is
    per host, not overall.
    """
    out: dict[str, LinkStatus] = {}
    sem = asyncio.Semaphore(concurrency)
    host_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    done = 0

    async def one(p: JobPosting) -> None:
        nonlocal done
        if not p.url:
            out[p.source_id] = LinkStatus.BROKEN
            return
        host = urlparse(p.url).netloc.lower()
        if _blocks_bots(p.url):
            out[p.source_id] = LinkStatus.NEEDS_CHECK
            done += 1
            if progress:
                progress(done, len(postings))
            return
        async with sem, host_locks[host]:
            try:
                res = await asyncio.to_thread(legacy.check_url, p.url)
                status = LinkStatus(res.get("status", "NEEDS_CHECK"))
            except Exception:  # noqa: BLE001
                status = LinkStatus.NEEDS_CHECK
            out[p.source_id] = status
            await asyncio.sleep(per_host_delay)
        done += 1
        if progress:
            progress(done, len(postings))

    await asyncio.gather(*(one(p) for p in postings))
    return out


# --------------------------------------------------------------------------
# track classification
# --------------------------------------------------------------------------
def _archetypes() -> list[dict[str, Any]]:
    try:
        data = yaml.safe_load(paths.read_text(paths.PROFILE_YML)) or {}
    except yaml.YAMLError:
        return []
    return [a for a in (data.get("archetypes") or []) if isinstance(a, dict)]


def classify_track(jd_text: str, title: str = "") -> tuple[TrackId, str, dict[str, int]]:
    """
    Count each archetype's `signals` in the JD, highest wins. Within 20% is a
    hybrid, and a tie breaks toward the track with lower competition.
    """
    blob = f"{title}\n{jd_text}".lower()
    hits: dict[str, int] = {}
    track_of: dict[str, str] = {}

    for arch in _archetypes():
        name = arch.get("name") or "?"
        track_of[name] = arch.get("track") or "track_a"
        n = 0
        for sig in arch.get("signals") or []:
            s = str(sig).strip().lower()
            if s and re.search(rf"\b{re.escape(s)}\b", blob):
                n += 1
        hits[name] = n

    if not hits or max(hits.values()) == 0:
        return TrackId.A, "no strong signals in the ad; defaulting to Data/Analytics", hits

    ranked = sorted(hits.items(), key=lambda kv: -kv[1])
    top, top_n = ranked[0]
    track = TrackId(track_of.get(top, "track_a"))

    note = f"{top} — {top_n} signal hits"
    if len(ranked) > 1:
        second, second_n = ranked[1]
        if second_n and (top_n - second_n) / max(top_n, 1) < 0.20:
            note += f"; close to {second} ({second_n}), treated as a hybrid"
    return track, note, hits


# --------------------------------------------------------------------------
# keyword-only JD analysis (the no-key fallback for jd_parser)
# --------------------------------------------------------------------------
def parse_jd_keywords(posting: JobPosting) -> Any:
    from ..models import JDAnalysis, Requirement

    rows = legacy.jd_keywords(posting.jd_text, 24)
    must = [
        Requirement(text=t, keyword=t, kind="must", frequency=w, under_required_heading=w >= 3)
        for t, w in rows if w >= 3
    ][:7]
    nice = [
        Requirement(text=t, keyword=t, kind="nice", frequency=w) for t, w in rows if w < 3
    ][:5]
    return JDAnalysis(
        company=posting.company,
        role_title=posting.role_title,
        location=posting.location,
        work_mode="Remote" if posting.remote else "",
        must_haves=must,
        nice_to_haves=nice,
        years_required=scoring.years_required(posting.jd_text),
        hiring_problem="",
        source="keywords",
    )


# --------------------------------------------------------------------------
# JD backfill
# --------------------------------------------------------------------------
async def backfill_jd(
    postings: list[JobPosting], *, concurrency: int = 4, min_chars: int = 200
) -> int:
    """
    Fetch the ad text for postings that arrived without it.

    Roles imported from SUMMARY.md carry a link but no text, and they are often
    the cap-exempt ones -- exactly the jobs that rank highest. Without the text
    the gate cannot screen them and the scorer has nothing to match on, so they
    surface as "open the ad to judge this one" when they deserve a real score.
    """
    import httpx
    from ..services.sources.base import HEADERS, html_to_text

    targets = [p for p in postings if p.url and len(p.jd_text.strip()) < min_chars]
    if not targets:
        return 0

    sem = asyncio.Semaphore(concurrency)
    filled = 0

    async with httpx.AsyncClient(
        headers=HEADERS, timeout=20.0, follow_redirects=True
    ) as client:

        async def one(p: JobPosting) -> None:
            nonlocal filled
            async with sem:
                try:
                    r = await client.get(p.url)
                    if r.status_code != 200:
                        return
                    ctype = r.headers.get("content-type", "")
                    if "html" not in ctype and "text" not in ctype:
                        return
                    text = html_to_text(r.text)
                    if len(text) > min_chars:
                        p.jd_text = text[:40000]
                        # A whole careers page includes navigation, footers and
                        # cookie banners. That is fine for the sponsorship gate,
                        # which looks for specific sentences, but it poisons
                        # keyword extraction -- so mark it rather than pretend
                        # it is a clean job ad.
                        p.raw["jd_fetched"] = True
                        filled += 1
                except Exception:  # noqa: BLE001 -- a fetch failure is not fatal
                    return

        await asyncio.gather(*(one(p) for p in targets))
    return filled
