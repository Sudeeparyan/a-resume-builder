"""Structured results each specialist agent must return.

Every agent is constrained to one of these shapes. A model never returns a score
or a decision: it returns grounded observations, and deterministic code in
``backend/assessment.py`` and ``backend/job_quality.py`` turns those into
numbers and states. Excerpt fields exist so a claim can be checked against the
saved source before it is trusted.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- Annie's posting-evaluation graph (backend/ai/agents/graph.py) --------------------

class Requirement(BaseModel):
    text: str = Field(description="The requirement as a short canonical phrase, e.g. 'Power BI'")
    category: Literal["required", "responsibility", "preferred"]
    excerpt: str = Field(description="The exact sentence from the job description, copied verbatim")
    status: Literal["met", "partial", "missing"]
    evidence_ids: list[str] = Field(default_factory=list, description="Ids from the evidence catalogue that show it; empty when missing")
    note: str = Field(default="", description="One short clause on how the evidence meets it, or what is missing")


class FitBlocker(BaseModel):
    excerpt: str = Field(description="The exact sentence from the job description, copied verbatim")
    reason: str = Field(description="Why it rules the candidate out, in a few words")


class FitAnalysis(BaseModel):
    """The requirement matrix. Code verifies every excerpt and evidence id before it is trusted (services/fit.py)."""
    requirements: list[FitRequirement]
    hard_blockers: list[FitBlocker] = Field(default_factory=list)
    summary: str = Field(default="", description="One sentence on the overall fit")


class FitRequirement(BaseModel):
    """One thing the posting asks for, and whether the candidate's registered evidence shows it."""
    text: str = Field(description="The requirement as a short canonical phrase, e.g. 'Apache Kafka' or 'stream processing'")
    category: Literal["required", "preferred", "responsibility"]
    excerpt: str = Field(description="The exact sentence from the job description, copied verbatim")
    status: Literal["met", "partial", "missing"]
    evidence_ids: list[str] = Field(default_factory=list, description="Ids from the evidence catalogue that show it; empty when missing")
    note: str = Field(default="", description="One short clause on how the evidence meets it, or what is missing")


class FitBlocker(BaseModel):
    excerpt: str = Field(description="The exact sentence from the job description, copied verbatim")
    reason: str = Field(description="Why it rules the candidate out, in a few words")


class FitAnalysis(BaseModel):
    """The requirement matrix. Code verifies every excerpt and evidence id before it is trusted (services/fit.py)."""
    requirements: list[FitRequirement]
    hard_blockers: list[FitBlocker] = Field(default_factory=list)
    summary: str = Field(default="", description="One sentence on the overall fit")


class ResumeEdit(BaseModel):
    field: Literal["summary", "skills", "project", "second_project", "font"]
    value: str = Field(description="The replacement value for this field")
    rationale: str = Field(description="Why this change suits the role, in one sentence")
    evidence_ids: list[str] = Field(description="Registered evidence IDs supporting the new wording. Empty means unsupported.")


class ResumeChangeSet(BaseModel):
    """Edits confined to registered evidence. New claims become profile proposals."""
    edits: list[ResumeEdit]
    unsupported_requests: list[str] = Field(
        description="Parts of the request needing facts not in the registered evidence"
    )
    summary: str = Field(description="One sentence describing what will change")


class ProfileProposal(BaseModel):
    action: Literal["add", "correct", "merge", "remove"]
    target_id: Optional[str] = Field(default=None, description="Existing profile entry ID, for correct/merge/remove")
    kind: Optional[str] = Field(default=None, description="skill, experience, education, project, certification or fact")
    title: Optional[str] = None
    summary: Optional[str] = None
    rationale: str


class ProfileChangeSet(BaseModel):
    proposals: list[ProfileProposal]
    summary: str


class HiringManagerReview(BaseModel):
    """Written without any candidate information. See isolation note in graph.py."""
    must_have_signals: list[str] = Field(description="What a strong application must demonstrate")
    screening_questions: list[str]
    common_rejection_reasons: list[str]


class CoverLetterDraft(BaseModel):
    body: str = Field(description="The letter body, no header or signature block")
    evidence_ids: list[str]
    unsupported_claims: list[str] = Field(description="Anything written that the evidence does not support. Should be empty.")


class UnsupportedSentence(BaseModel):
    sentence: str = Field(description="The letter's sentence, copied exactly")
    why: str = Field(description="What it says about the candidate that the evidence does not state")


class LetterAudit(BaseModel):
    unsupported: list[UnsupportedSentence] = Field(
        description="Sentences about the candidate that the evidence does not support; empty when all are supported")


class MailVerdict(BaseModel):
    kind: Literal["application_receipt", "rejection", "interview_invite", "offer", "unrelated"]
    company: Optional[str] = None
    role: Optional[str] = None
    states_submission_date: Optional[str] = Field(default=None, description="ISO date only if the message states when the application was submitted")
    confidence: Literal["high", "medium", "low"]
    excerpt: str


class PostingFields(BaseModel):
    """The four facts a pasted posting must yield before it can be saved.

    Every value must appear in the pasted text; the assistant discards anything
    it cannot find there, so a wrong guess costs nothing but an empty field.
    """
    company: str = Field(default="", description="Employer name exactly as the posting writes it; empty if not stated")
    title: str = Field(default="", description="Job title exactly as the posting writes it; empty if not stated")
    location: str = Field(default="", description="City and state or country, 'Remote (US)', 'Remote (Ireland)' or similar, as the posting states it; empty if not stated")
    url: str = Field(default="", description="The application or posting link if the text contains one; empty otherwise")


class TailoredProject(BaseModel):
    """One project slot in a per-job resume plan.

    'verified' entries are copied unchanged from the registry and carry its
    evidence id; 'predicted' entries are proposed wording aligned to the
    employer's stack and must be reviewed before they can reach a resume.
    """
    title: str
    context: str = Field(description="The stack line printed beside the title, e.g. 'Apache Kafka, Python'")
    bullets: list[str]
    origin: Literal["verified", "predicted"]
    evidence_id: str = Field(default="", description="Registry project id for verified items; empty for predicted")


class TailoredSkill(BaseModel):
    name: str = Field(description="One skill name, e.g. 'Apache Spark'; no commas, semicolons or parentheses")
    origin: Literal["verified", "predicted"]
    evidence_id: str = Field(default="", description="Registry claim id for verified items; empty for predicted")


class BulletRewrite(BaseModel):
    """New wording for one registered project bullet, in the posting's vocabulary.

    It states the same facts: the same numbers, and only names and tools that the registered
    bullet, the evidence in `cited_ids` or the registered skills hold. services/rewrite_guard.py
    checks it word by word; one that fails keeps the registered wording.
    """
    evidence_id: str = Field(description="The kept verified project's registry id")
    bullet: int = Field(description="Which of its registered bullets this rewords: 1, 2 or 3")
    text: str = Field(description="The new wording, one resume line")
    cited_ids: list[str] = Field(default_factory=list,
                                 description="Other registered evidence ids (for example a skill) whose words it uses")


class TailoringResult(BaseModel):
    """A per-job Projects + Skills plan. Experience, Education and personal sections are never part of it."""
    projects: list[TailoredProject]
    skills: list[TailoredSkill]
    rewrites: list[BulletRewrite] = Field(default_factory=list,
                                          description="Optional rewordings of kept verified project bullets; empty when the registered wording fits")
    rationale: str = Field(description="One short paragraph on why this mix fits the role")


class ToolCall(BaseModel):
    """One more read-only tool the agent runs in the same turn."""
    tool: str = Field(description="The tool name, exactly as listed in tools")
    arguments: str = Field(default="{}", description="The tool's arguments as one JSON object")


class AgentTurn(BaseModel):
    """One decision of the workspace agent: call a tool, ask the person something, or reply.

    The loop in services/assistant.py runs the chosen tool, appends its result
    to the task transcript and asks for the next turn, until the agent replies.
    """
    thought: str = Field(description="One short sentence, written to her as 'you', on what you are doing now and why; she sees it as progress")
    action: Literal["call", "ask", "reply"] = Field(description="call = run one tool; ask = you need something only she can supply; reply = the task is finished or cannot proceed")
    tool: str = Field(default="", description="For call: the tool name, exactly as listed in tools")
    arguments: str = Field(default="{}", description="For call: the tool's arguments as one JSON object, using the parameter names listed")
    reply: str = Field(default="", description="For ask or reply: what to say to her, in plain sentences; **bold** for a job name is fine")
    suggestions: list[str] = Field(
        default_factory=list,
        description="For reply: up to four short messages she could send next; for ask: the likely answers, e.g. yes / no",
    )
    more_calls: list[ToolCall] = Field(
        default_factory=list,
        description="For call: up to five more tools that only read (never change anything) to run in this same "
                    "turn, when you already know you need them all, e.g. get_job for three jobs. Leave empty otherwise.",
    )
