"""
The typed vocabulary shared by the agents, the API and the frontend.

These schemas are the contract that turns the workspace's prose rules into
something mechanically checkable. Where a field encodes a rule from CLAUDE.md,
the rule is named in the docstring so it cannot drift silently.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# sponsorship
# --------------------------------------------------------------------------
class Tier(str, Enum):
    """
    Ranking tiers from CLAUDE.md. Ordering is S -> A -> B -> C, and a job is
    ordered by TIER FIRST, score second: a tier-C role scoring 85 ranks below a
    tier-S role scoring 75, because a cap-exempt employer can file without a
    lottery.
    """
    S = "S"  # cap-exempt: no lottery, files year-round
    A = "A"  # posting explicitly offers sponsorship
    B = "B"  # proven H-1B sponsor, posting silent
    C = "C"  # silent, no record -- the normal case and the largest bucket
    EXCLUDED = "EXCLUDED"


TIER_ORDER: dict[str, int] = {"S": 0, "A": 1, "B": 2, "C": 3, "EXCLUDED": 9}

TIER_LABEL: dict[str, str] = {
    "S": "Cap-exempt — can file any time of year, no lottery",
    "A": "Says yes — the posting explicitly offers sponsorship",
    "B": "Proven sponsor — has filed before, this posting is silent",
    "C": "Silent, no record — the normal case, most offers come from here",
    "EXCLUDED": "Cannot proceed",
}


class SponsorVerdict(BaseModel):
    """
    The hard gate. Two steps: screen() the JD text, then resolve the tier from
    the company. Silence is always a KEEP.
    """
    verdict: Literal["KEEP", "EXCLUDED"]
    tier: Tier
    reason: str                       # silent | explicit_sponsorship | no_sponsorship | cannot_hire
    reason_label: str                 # plain English, shown to the user
    triggering_sentence: str | None = None   # verbatim; every exclusion must carry one
    pattern: str | None = None
    everify: bool = False             # matters for STEM OPT (+24 months), not for sponsorship
    cap_exempt: bool = False
    cap_exempt_why: str | None = None
    h1b_approvals: int = 0
    h1b_years: list[str] = Field(default_factory=list)
    h1b_matched_name: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def excluded(self) -> bool:
        return self.verdict == "EXCLUDED"


# --------------------------------------------------------------------------
# jobs
# --------------------------------------------------------------------------
class LinkStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    BROKEN = "BROKEN"
    NEEDS_CHECK = "NEEDS_CHECK"   # never counted as live without human eyes
    UNCHECKED = "UNCHECKED"


class JobPosting(BaseModel):
    """One posting, normalised across every source."""
    id: str | None = None
    source: str                       # greenhouse | lever | ashby | adzuna | remotive | workspace ...
    source_id: str
    company: str
    role_title: str
    url: str
    location: str = ""
    remote: bool = False
    posted_at: datetime | None = None
    jd_text: str = ""
    department: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = ""
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class ExcludedJob(BaseModel):
    """
    Every drop is logged with the sentence that caused it, so a wrong exclusion
    is visible and correctable rather than a silent disappearance.
    """
    company: str
    role_title: str
    url: str = ""
    why: str
    triggering_sentence: str | None = None
    stage: str                        # sponsorship | tracker | link | filter


# --------------------------------------------------------------------------
# JD understanding
# --------------------------------------------------------------------------
class Requirement(BaseModel):
    text: str
    kind: Literal["must", "nice", "domain"] = "must"
    keyword: str = ""                 # the JD's own wording, for ATS matching
    frequency: int = 1
    under_required_heading: bool = False


class JDAnalysis(BaseModel):
    company: str
    role_title: str
    team: str = ""
    location: str = ""
    work_mode: str = ""
    seniority: str = ""
    must_haves: list[Requirement] = Field(default_factory=list)      # 5-7
    nice_to_haves: list[Requirement] = Field(default_factory=list)   # 3-5
    domain_keywords: list[Requirement] = Field(default_factory=list) # 3-5
    hiring_problem: str = ""          # what broke or is growing that opened this role
    years_required: int | None = None
    source: Literal["llm", "keywords"] = "llm"


# --------------------------------------------------------------------------
# company research
# --------------------------------------------------------------------------
class DemandRow(BaseModel):
    """
    One row of the skills demand map from system/modes/deep.md.

    `destination` is the honesty wall in one field. A skill she does not have
    goes to the study plan or is named an honest gap -- it NEVER moves onto the
    resume, in any hedged form.
    """
    skill: str
    named_by: str = ""                # their blog / the JD / inferred
    centrality: Literal["core", "important", "peripheral"] = "important"
    candidate_level: Literal["strong", "used_it", "touched_it", "none"] = "none"
    destination: Literal["resume", "study_plan", "honest_gap"]
    evidence_url: str | None = None
    note: str = ""


class CompanyResearch(BaseModel):
    company: str
    what_they_do: str = ""
    engineering_reality: str = ""     # what they actually run; blog beats the JD
    current_projects: list[str] = Field(default_factory=list)
    future_direction: list[str] = Field(default_factory=list)
    team_shape: str = ""
    pressures: list[str] = Field(default_factory=list)
    day_job_months_1_3: str = ""
    day_job_month_12: str = ""
    demand_map: list[DemandRow] = Field(default_factory=list)
    fit_narrative: str = ""
    questions_to_ask: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)   # URLs backing the claims
    confirmed_vs_inferred: dict[str, str] = Field(default_factory=dict)


class SkillPrediction(BaseModel):
    """
    What they must and should see, and an honest read on the odds.

    `probability` is a calibrated estimate from must-have coverage, not a
    promise. `lift_if_learned` names what would actually move it.
    """
    must_have: list[str] = Field(default_factory=list)
    should_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    she_has: list[str] = Field(default_factory=list)
    she_lacks: list[str] = Field(default_factory=list)
    must_have_coverage: float = 0.0   # 0..1
    probability: float = 0.0          # 0..1, interview probability
    probability_band: Literal["high", "moderate", "low", "long_shot"] = "low"
    rationale: str = ""
    lift_if_learned: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------
class ScoreBreakdown(BaseModel):
    """
    Weights from system/modes/_profile.md, which overrides _shared.md and wins.
    Eligibility is 0% here because it was converted to a hard gate upstream.
    """
    skill_match: float = 0.0          # weight 40
    competition: float = 0.0          # weight 30
    company_profile: float = 0.0      # weight 15
    recency: float = 0.0              # weight 15
    total: float = 0.0
    evidence: dict[str, str] = Field(default_factory=dict)

    WEIGHTS: dict[str, float] = Field(
        default_factory=lambda: {
            "skill_match": 0.40, "competition": 0.30,
            "company_profile": 0.15, "recency": 0.15,
        },
        exclude=True,
    )


class ScoredJob(BaseModel):
    job: JobPosting
    sponsor: SponsorVerdict
    link_status: LinkStatus = LinkStatus.UNCHECKED
    jd: JDAnalysis | None = None
    research: CompanyResearch | None = None
    prediction: SkillPrediction | None = None
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    recommendation: str = ""          # apply today | this week | only if low competition | skip
    ghost_flags: list[str] = Field(default_factory=list)
    research_path: str | None = None

    @property
    def rank_key(self) -> tuple[int, float]:
        """Tier first, then score. This ordering is a rule, not a preference."""
        return (TIER_ORDER.get(self.sponsor.tier.value, 9), -self.score.total)


# --------------------------------------------------------------------------
# resume
# --------------------------------------------------------------------------
class TrackId(str, Enum):
    A = "track_a"   # Data / Analytics
    B = "track_b"   # ML / AI
    C = "track_c"   # Software
    D = "track_d"   # Embedded / Test automation


class AuditComponent(BaseModel):
    name: str
    weight: int
    score: float                      # 0..100 within the component
    note: str = ""


class MissingKeyword(BaseModel):
    """
    The distinction that is the whole game: a keyword she HAS but did not write
    is a writing problem and gets fixed. A keyword she does not have is a truth
    problem and goes to the study plan -- never onto the page.
    """
    term: str
    frequency_in_jd: int = 1
    under_required_heading: bool = False
    status: Literal["in_profile_not_on_page", "not_held"]
    where_to_add: str = ""


class RecruiterAudit(BaseModel):
    score_before: float = 0.0
    score_after: float = 0.0
    components: list[AuditComponent] = Field(default_factory=list)
    missing_keywords: list[MissingKeyword] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    strong_sections: list[str] = Field(default_factory=list)
    weak_sections: list[str] = Field(default_factory=list)
    pile: Literal["yes", "maybe", "no"] = "maybe"
    one_change_to_move_up: str = ""
    fixed: list[str] = Field(default_factory=list)
    still_open: list[str] = Field(default_factory=list)
    fill_ins: list[str] = Field(default_factory=list)   # asked as plain questions
    comparison_to_strong_candidate: str = ""


class Suggestion(BaseModel):
    """Binds to source lines so the editor can highlight and patch in place."""
    id: str
    kind: Literal["keyword", "phrasing", "evidence", "length", "banned_word", "fill_in", "honesty"]
    severity: Literal["blocker", "important", "nice"] = "important"
    message: str
    line_start: int | None = None
    line_end: int | None = None
    before: str | None = None
    after: str | None = None


class CompileResult(BaseModel):
    ok: bool
    mode: Literal["preview", "ship"] = "preview"
    pages: int = 0
    pdf_b64: str | None = None
    log: str = ""
    errors: list[dict[str, Any]] = Field(default_factory=list)
    placeholders: list[str] = Field(default_factory=list)
    fill_ins: list[str] = Field(default_factory=list)
    text_chars: int = 0
    underfilled: bool = False
    blocking: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class ResumeDoc(BaseModel):
    id: str
    job_id: str
    company: str
    role_title: str
    folder: str                       # output/Annie_Manoharan_<Company>_<NN>
    track: TrackId = TrackId.A
    track_reason: str = ""
    signature_project: str = ""       # P1..P10
    signature_reason: str = ""
    tex: str = ""
    audit: RecruiterAudit | None = None
    ats: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[Suggestion] = Field(default_factory=list)
    compile: CompileResult | None = None
    honesty: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None


# --------------------------------------------------------------------------
# runs
# --------------------------------------------------------------------------
class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_QUOTA = "WAITING_QUOTA"   # rate limited; checkpointed, will resume
    PAUSED = "PAUSED"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    SKIPPED = "SKIPPED"               # e.g. no LLM provider configured
    FAILED = "FAILED"


class StageState(BaseModel):
    key: str
    label: str                        # plain English, shown to a non-developer
    status: StageStatus = StageStatus.PENDING
    items_total: int = 0
    items_done: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str | None = None
    note: str = ""


class RunState(BaseModel):
    id: str
    kind: Literal["scan", "build", "hunt"] = "scan"
    status: RunStatus = RunStatus.QUEUED
    params: dict[str, Any] = Field(default_factory=dict)
    stages: list[StageState] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    eta_seconds_p50: int | None = None
    eta_seconds_p80: int | None = None
    elapsed_seconds: int = 0
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    message: str = ""
    error: str | None = None
    resume_after: datetime | None = None   # set when WAITING_QUOTA


class RunEvent(BaseModel):
    run_id: str
    seq: int = 0
    type: Literal[
        "run_started", "stage_started", "stage_progress", "stage_finished",
        "log", "eta", "artifact", "run_finished", "error", "quota_wait",
    ]
    at: datetime
    stage: str | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
