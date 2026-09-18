"""
Ranking.

Weights come from system/modes/_profile.md, which overrides _shared.md and wins:

    skill match      40%
    competition      30%
    eligibility       0%   -- converted to a HARD GATE upstream, not a weight
    company profile  15%
    recency          15%

Then the ordering rule that is not a preference: **tier first, score second**.
A tier-C role scoring 85 ranks below a tier-S role scoring 75, because a
cap-exempt employer can file for her any time of year with no lottery.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..models import (
    JDAnalysis, JobPosting, ScoreBreakdown, ScoredJob, SponsorVerdict, Tier,
    TIER_ORDER,
)
from . import context_loader

WEIGHTS = {
    "skill_match": 0.40,
    "competition": 0.30,
    "company_profile": 0.15,
    "recency": 0.15,
}

# Titles she is not eligible for. A hard filter from _profile.md.
SENIOR_WORDS = (
    "senior", "sr.", "sr ", "staff", "principal", "lead ", "manager", "head of",
    "director", "vp ", "vice president", "architect", "distinguished", "fellow",
    "chief", "president", "executive",
)
_YEARS_RE = re.compile(
    r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)[^.]{0,30}?(?:experience|exp\b)", re.I
)


def title_is_too_senior(title: str) -> tuple[bool, str]:
    low = f" {(title or '').lower()} "
    for w in SENIOR_WORDS:
        if w in low:
            return True, f"the title contains '{w.strip()}'"
    return False, ""


def years_required(jd_text: str) -> int | None:
    """Smallest stated requirement -- ranges like '3-5 years' mean 3."""
    vals = [int(m.group(1)) for m in _YEARS_RE.finditer(jd_text or "") if int(m.group(1)) < 30]
    return min(vals) if vals else None


def recency_subscore(posted: datetime | None) -> tuple[float, str]:
    """
    From _shared.md. An undated listing is treated as 30+ days old, deliberately:
    at entry level a fresh posting is worth far more, so an unknown date must not
    be rewarded.
    """
    if not posted:
        return 15.0, "no date given, treated as old"
    days = max(0, (datetime.now() - posted).days)
    if days <= 2:
        return 100.0, f"posted {days}d ago"
    if days <= 7:
        return 85.0, f"posted {days}d ago"
    if days <= 14:
        return 65.0, f"posted {days}d ago"
    if days <= 30:
        return 40.0, f"posted {days}d ago"
    return 15.0, f"posted {days}d ago — stale"


def competition_subscore(
    *, applicants: int | None = None, employees: int | None = None,
    niche_combo: bool = False, posted: datetime | None = None,
) -> tuple[float, str]:
    """
    Applicant volume predicts callbacks better than anything else at entry level,
    which is why this carries 30%. Most sources do not report it, so we fall back
    to a neutral base and apply the structural bonuses that are observable.
    """
    notes: list[str] = []
    if applicants is None:
        base = 55.0
        notes.append("applicant count unknown")
    else:
        for ceiling, value in ((10, 100.0), (25, 85.0), (50, 70.0), (100, 50.0), (200, 30.0)):
            if applicants < ceiling:
                base = value
                break
        else:
            base = 10.0
        notes.append(f"{applicants} applicants" + (" — crowded" if base <= 30 else ""))

    if employees is not None:
        if employees < 50:
            base += 15
            notes.append("under 50 employees (+15)")
        elif employees <= 200:
            base += 10
            notes.append("50-200 employees (+10)")
    if niche_combo:
        base += 15
        notes.append("niche skill combination (+15)")
    if posted and (datetime.now() - posted).total_seconds() < 48 * 3600:
        base += 10
        notes.append("posted within 48h (+10)")

    return max(0.0, min(100.0, base)), "; ".join(notes)


def company_subscore(sponsor: SponsorVerdict, posting: JobPosting) -> tuple[float, str]:
    """Cap-exempt status and sponsorship history dominate here."""
    notes: list[str] = []
    if sponsor.cap_exempt:
        score = 100.0
        notes.append("cap-exempt — files year-round, no lottery")
    elif sponsor.tier == Tier.A:
        score = 90.0
        notes.append("posting explicitly offers sponsorship")
    elif sponsor.h1b_approvals >= 50:
        score = 80.0
        notes.append(f"{sponsor.h1b_approvals} H-1B approvals on record")
    elif sponsor.h1b_approvals > 0:
        score = 70.0
        notes.append(f"{sponsor.h1b_approvals} H-1B approval(s) on record")
    else:
        score = 45.0
        notes.append("no H-1B record — normal, and not a negative")
    if sponsor.everify:
        score = min(100.0, score + 5)
        notes.append("E-Verify (needed for the STEM OPT extension)")
    return score, "; ".join(notes)


def skill_subscore_deterministic(
    jd_text: str, jd: JDAnalysis | None, fb: context_loader.FactBase
) -> tuple[float, str]:
    """
    No-LLM skill match: how many of the job's own top terms she can honestly
    claim. Deliberately conservative -- a 'Touched it' skill counts half, and an
    honest gap counts zero rather than being quietly rounded up.
    """
    from .. import legacy

    terms: list[str] = []
    if jd and jd.must_haves:
        terms = [r.keyword or r.text for r in jd.must_haves]
    if not terms:
        terms = [t for t, _w in legacy.jd_keywords(jd_text, 20)]
    if not terms:
        return 40.0, "the job ad gave nothing specific to match on"

    have = half = miss = 0
    missing: list[str] = []
    for t in terms:
        lvl = fb.skill_level(t.lower())
        if lvl in ("strong", "used_it"):
            have += 1
        elif lvl == "touched_it":
            half += 1
        else:
            if fb.has_token(t.lower()) and len(t) > 3:
                half += 1        # named somewhere in her history, just not as a skill
            else:
                miss += 1
                missing.append(t)

    total = len(terms)
    score = 100.0 * (have + 0.5 * half) / total
    note = f"{have} of {total} requirements you can claim outright"
    if missing:
        note += f"; not held: {', '.join(missing[:4])}"
    return round(score, 1), note


def score_job(
    posting: JobPosting,
    sponsor: SponsorVerdict,
    *,
    jd: JDAnalysis | None = None,
    skill_override: float | None = None,
    skill_note: str = "",
    applicants: int | None = None,
    employees: int | None = None,
    niche_combo: bool = False,
    fb: context_loader.FactBase | None = None,
) -> ScoreBreakdown:
    fb = fb or context_loader.load()
    b = ScoreBreakdown()

    if skill_override is not None:
        b.skill_match, note = float(skill_override), skill_note or "assessed by the model"
    else:
        b.skill_match, note = skill_subscore_deterministic(posting.jd_text, jd, fb)
    b.evidence["skill_match"] = note

    b.competition, b.evidence["competition"] = competition_subscore(
        applicants=applicants, employees=employees,
        niche_combo=niche_combo, posted=posting.posted_at,
    )
    b.company_profile, b.evidence["company_profile"] = company_subscore(sponsor, posting)
    b.recency, b.evidence["recency"] = recency_subscore(posting.posted_at)

    b.total = round(
        b.skill_match * WEIGHTS["skill_match"]
        + b.competition * WEIGHTS["competition"]
        + b.company_profile * WEIGHTS["company_profile"]
        + b.recency * WEIGHTS["recency"],
        1,
    )
    return b


def recommendation(score: float, competition: float, *, has_jd: bool = True) -> str:
    """
    Thresholds from _shared.md.

    A job whose ad text never loaded is NOT a low-scoring job -- it is an
    unscored one. Calling it "skip" would silently bury roles the gate rated
    tier S, which is the opposite of what she needs.
    """
    if not has_jd:
        return "open the ad to judge this one"
    if score >= 80:
        return "apply today"
    if score >= 70:
        return "apply this week"
    if score >= 55:
        return "apply only if competition is low" if competition < 60 else "borderline"
    return "skip"


GHOST_SIGNALS = [
    (r"\b(staffing|recruiting agency|talent partner|consultancy)\b",
     "posted by an agency with no named client"),
]


def ghost_flags(posting: JobPosting) -> list[str]:
    """Flag, never auto-drop -- a ghost job is a warning, not an exclusion."""
    flags: list[str] = []
    if posting.posted_at and (datetime.now() - posting.posted_at).days > 60:
        flags.append("over 60 days old with no update")
    blob = f"{posting.company} {posting.jd_text[:3000]}".lower()
    for pattern, label in GHOST_SIGNALS:
        if re.search(pattern, blob):
            flags.append(label)
    if not posting.location and "remote" not in blob:
        flags.append("no location given")
    return flags


def rank(jobs: list[ScoredJob]) -> list[ScoredJob]:
    """Tier first, then score. This ordering is a rule, not a preference."""
    return sorted(jobs, key=lambda j: (TIER_ORDER.get(j.sponsor.tier.value, 9), -j.score.total))


def resolve_tier(
    screen_result: dict[str, Any], *, cap_exempt: bool, approvals: int
) -> Tier:
    """
    screen() only ever returns A or EXCLUDED. S/B/C are resolved here:
      S cap-exempt · A says yes · B proven sponsor, silent · C silent, no record
    C is the normal case and the largest bucket -- it is never a negative.
    """
    if screen_result.get("verdict") == "EXCLUDED":
        return Tier.EXCLUDED
    if cap_exempt:
        return Tier.S
    if screen_result.get("tier") == "A":
        return Tier.A
    if approvals > 0:
        return Tier.B
    return Tier.C
