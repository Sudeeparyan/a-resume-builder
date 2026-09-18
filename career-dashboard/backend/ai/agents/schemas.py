"""Structured results each specialist agent must return.

Every agent is constrained to one of these shapes. A model never returns a score
or a decision: it returns grounded observations, and deterministic code in
``backend/assessment.py`` and ``backend/job_quality.py`` turns those into
numbers and states. Excerpt fields exist so a claim can be checked against the
saved source before it is trusted.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Requirement(BaseModel):
    text: str = Field(description="The requirement as a short canonical phrase, e.g. 'Power BI'")
    category: Literal["required", "responsibility", "preferred"]
    excerpt: str = Field(description="The exact sentence from the job description, copied verbatim")


class RequirementSet(BaseModel):
    """Grounded requirements. Any excerpt absent from the saved JD is discarded."""
    requirements: list[Requirement]


class RelevanceVerdict(BaseModel):
    role_family_matches: bool = Field(description="Is this an analyst/BI/data role the candidate targets?")
    seniority_suitable: bool = Field(description="Is it open to early-career candidates (0-3 years)?")
    location_matches: bool = Field(description="Is it in the United States, or explicitly US-remote?")
    hard_blockers: list[str] = Field(description="Stated conditions that disqualify the candidate outright, e.g. a required active security clearance")
    reasons: list[str] = Field(description="Short factual reasons for the verdict, each traceable to the posting")


class CompanyFinding(BaseModel):
    claim: str
    source_url: str = Field(description="A public URL supporting this claim")


class CompanyAssessment(BaseModel):
    """Public-record research only. Never a guarantee, always cited."""
    legal_presence: bool = Field(description="Is there a company register or legal-entity record?")
    size_category: Literal["startup", "mid", "large", "unknown"]
    employee_estimate: Optional[int] = None

    @field_validator("employee_estimate", mode="before")
    @classmethod
    def _blank_when_unknown(cls, value):
        """Models answer 'unknown' here rather than omitting the field."""
        if isinstance(value, str):
            digits = "".join(c for c in value if c.isdigit())
            return int(digits) if digits else None
        return value
    sponsorship_evidence: Literal["stated", "documented", "none", "unknown"] = Field(
        description="'stated' if this posting says so, 'documented' if the employer publishes a sponsorship policy"
    )
    red_flags: list[str] = Field(description="Fraud signals: upfront payment, identity documents, personal-email-only contact, impersonation")
    findings: list[CompanyFinding]


class PostingVerdict(BaseModel):
    state: Literal["active", "expired", "needs_review"]
    evidence: str = Field(description="The wording on the page that justifies this state, quoted")


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


class MailVerdict(BaseModel):
    kind: Literal["application_receipt", "rejection", "interview_invite", "offer", "unrelated"]
    company: Optional[str] = None
    role: Optional[str] = None
    states_submission_date: Optional[str] = Field(default=None, description="ISO date only if the message states when the application was submitted")
    confidence: Literal["high", "medium", "low"]
    excerpt: str
