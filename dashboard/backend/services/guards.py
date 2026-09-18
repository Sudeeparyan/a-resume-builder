"""
The guards: the workspace's prose rules made mechanical.

These are the checks that do not need a model and cannot be talked out of a
verdict. They run in every mode, including no-key mode -- which is why no-key
mode is actually the *safest* mode: nothing is generated, so nothing can be
invented.

Severity:
  blocker   -> strict compile fails, which means Download is disabled
  important -> shown prominently, does not block
  nice      -> a suggestion
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .. import legacy
from . import context_loader

# Numbers that are structural rather than claims: years, small counts, versions.
_INNOCENT_NUMBERS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
    "0", "100", "1000",
}
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*%?")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.]*(?:[/-][A-Za-z0-9+#.]+)*")
_FILL_RE = re.compile(r"\[FILL IN[^\]]*\]")
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
_ANCHOR_RE = re.compile(r"^\s*%\s*@b:([A-Za-z0-9._-]+)\s*$")

# Hedges that try to smuggle a study-plan skill onto the page.
_HEDGES = [
    "familiar with", "exposure to", "exposed to", "working knowledge of",
    "basic knowledge of", "some experience with", "understanding of",
    "conversant with", "aware of", "currently learning", "currently building",
    "learning ", "studying ",
]


@dataclass
class Violation:
    kind: str
    severity: str            # blocker | important | nice
    message: str
    evidence: str = ""
    block_id: str | None = None
    line: int | None = None
    token: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind, "severity": self.severity, "message": self.message,
            "evidence": self.evidence, "block_id": self.block_id,
            "line": self.line, "token": self.token,
        }


@dataclass
class GuardReport:
    violations: list[Violation] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def blockers(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "blocker"]

    @property
    def ok(self) -> bool:
        return not self.blockers

    def add(self, v: Violation) -> None:
        self.violations.append(v)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "blocker_count": len(self.blockers),
            "violation_count": len(self.violations),
            "checked": self.checked,
            "violations": [v.as_dict() for v in self.violations],
        }


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def anchor_map(tex: str) -> dict[str, int]:
    """block_id -> the 1-based line of the content it labels."""
    out: dict[str, int] = {}
    lines = tex.splitlines()
    for i, line in enumerate(lines):
        m = _ANCHOR_RE.match(line)
        if m:
            out[m.group(1)] = i + 2      # the content sits on the next line
    return out


# The trailing brace matters: \resumeItemListStart contains "\resumeItem" as a
# substring, so a plain `in` test scans the macro DEFINITION in the preamble and
# reports its 0.17in leftmargin as an invented metric.
_BULLET_RE = re.compile(r"\\(?:resumeItem|resumeProjectLine)\s*\{")


def _body_of(tex: str) -> tuple[str, int]:
    """
    Everything after \\begin{document}, plus the line offset.

    Bullets only exist in the body. The preamble is full of dimensions and
    package versions that are not claims about her.
    """
    marker = "\\begin{document}"
    idx = tex.find(marker)
    if idx == -1:
        return tex, 0
    head = tex[:idx]
    return tex[idx:], head.count("\n")


def _bullet_lines(tex: str) -> list[tuple[int, str, str | None]]:
    """(line_no, visible text, block_id) for every real bullet in the body."""
    out: list[tuple[int, str, str | None]] = []
    current: str | None = None
    body, offset = _body_of(tex)
    for i, raw in enumerate(body.splitlines(), start=1):
        m = _ANCHOR_RE.match(raw)
        if m:
            current = m.group(1)
            continue
        if _BULLET_RE.search(raw):
            out.append((i + offset, legacy.strip_latex(raw).strip(), current))
            current = None
    return out


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def _numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text or "")


# --------------------------------------------------------------------------
# 1. fabrication -- the single most important check
# --------------------------------------------------------------------------
def check_fabrication(tex: str, fb: context_loader.FactBase) -> list[Violation]:
    """
    Every number and every technology named in a bullet must already exist in
    context/. A number that is not there was invented; there is no rounding
    tolerance and no exception, because inventing a metric is the exact failure
    this whole workspace is built to prevent.
    """
    out: list[Violation] = []
    for line_no, text, block in _bullet_lines(tex):
        if not text:
            continue
        stripped = _FILL_RE.sub(" ", text)          # a marker is honest, not a claim

        for num in _numbers(stripped):
            norm = re.sub(r"[,\s%]", "", num).rstrip(".")
            if norm in _INNOCENT_NUMBERS or _YEAR_RE.match(norm):
                continue
            if not fb.has_number(num):
                out.append(Violation(
                    kind="FABRICATION_NUMBER", severity="blocker",
                    message=(
                        f"The number {num} does not appear anywhere in your context files. "
                        "Either it is wrong, or the fact behind it still needs adding."
                    ),
                    evidence=text[:200], block_id=block, line=line_no, token=num,
                ))

        for tok in _tokens(stripped):
            low = tok.lower()
            if fb.forbidden(low):
                out.append(Violation(
                    kind="HONESTY_WALL", severity="blocker",
                    message=(
                        f"'{tok}' is on your honest-gaps list. It cannot go on a resume "
                        "in any form until you have actually used it and added it to "
                        "context/05-skills.md."
                    ),
                    evidence=text[:200], block_id=block, line=line_no, token=tok,
                ))
            elif not fb.has_token(low):
                out.append(Violation(
                    kind="FABRICATION_TOKEN", severity="important",
                    message=(
                        f"'{tok}' is not mentioned anywhere in your context files. "
                        "Check it is real before sending this."
                    ),
                    evidence=text[:200], block_id=block, line=line_no, token=tok,
                ))
    return out


# --------------------------------------------------------------------------
# 2. the honesty wall against the study plan
# --------------------------------------------------------------------------
def study_plan_terms(study_plan: str) -> set[str]:
    """
    The skills a study plan names, read from the first column of its tables.

    Shared by the guard below and by the resume chat, which uses it to refuse a
    term before it can ever be proposed. One definition, so the two can never
    disagree about what is in the plan.
    """
    skills: set[str] = set()
    for raw in (study_plan or "").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        name = re.sub(r"\*\*(.+?)\*\*", r"\1", cells[0]).strip().lower()
        if name in ("skill", "item", "topic") or len(name) < 2 or len(name) > 48:
            continue
        skills.add(name)
    return skills


def check_study_plan_wall(tex: str, study_plan: str, fb: context_loader.FactBase) -> list[Violation]:
    """
    A skill in the study plan is a skill she does not have yet. It must not
    appear on the resume -- not plainly, and not hedged.
    """
    out: list[Violation] = []
    if not study_plan:
        return out

    skills = study_plan_terms(study_plan)
    body = legacy.strip_latex(tex).lower()
    for skill in sorted(skills):
        if fb.claimable(skill):
            continue                    # she really does have it; not a wall breach
        if re.search(rf"\b{re.escape(skill)}\b", body):
            out.append(Violation(
                kind="HONESTY_WALL", severity="blocker",
                message=(
                    f"'{skill}' is in this company's study plan, which means you do not "
                    "have it yet — so it cannot appear on the resume."
                ),
                evidence=skill, token=skill,
            ))

    for hedge in _HEDGES:
        for m in re.finditer(rf"{re.escape(hedge)}\s+([A-Za-z0-9+#./ -]{{2,30}})", body):
            claim = m.group(1).strip()
            if claim and not fb.claimable(claim.split(",")[0].strip()):
                out.append(Violation(
                    kind="HEDGED_CLAIM", severity="blocker",
                    message=(
                        f"'{hedge}{claim}' is a hedged claim. The rule is absolute: a skill "
                        "you have not used does not go on the page in any softened form."
                    ),
                    evidence=m.group(0)[:120], token=claim,
                ))
    return out


# --------------------------------------------------------------------------
# 3. voice
# --------------------------------------------------------------------------
def check_banned_phrases(tex: str, fb: context_loader.FactBase) -> list[Violation]:
    out: list[Violation] = []
    body, offset = _body_of(tex)
    for i, raw in enumerate(body.splitlines(), start=1 + offset):
        visible = legacy.strip_latex(raw).lower()
        if not visible.strip():
            continue
        for phrase in fb.banned_words:
            if re.search(rf"\b{re.escape(phrase)}\b", visible):
                out.append(Violation(
                    kind="BANNED_PHRASE", severity="important",
                    message=f"'{phrase}' is on your banned list — rewrite this line.",
                    evidence=visible[:160], line=i, token=phrase,
                ))
    return out


def check_blocked_claims(tex: str) -> list[Violation]:
    """Claims frozen by the open questions in QUESTIONS-FOR-YOU.md."""
    out: list[Violation] = []
    body = legacy.strip_latex(tex)

    m = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?\s+of\s+(?:professional\s+)?experience", body, re.I)
    if m:
        out.append(Violation(
            kind="BLOCKED_CLAIM", severity="blocker",
            message=(
                "This states a years-of-experience total. The Soliton dates are still "
                "unsettled (question 1), so no total may be claimed yet."
            ),
            evidence=m.group(0), token=m.group(1),
        ))

    if re.search(r"\b(ICCV|publication|published in|proceedings of)\b", body, re.I):
        out.append(Violation(
            kind="BLOCKED_CLAIM", severity="blocker",
            message=(
                "This looks like a publication claim. None of your 14 resumes mentions "
                "one and question 3 is still open, so it cannot be claimed."
            ),
            evidence=body[max(0, body.lower().find("iccv") - 40):][:160],
        ))
    return out


# --------------------------------------------------------------------------
# 4. shippability
# --------------------------------------------------------------------------
def check_markers(tex: str) -> list[Violation]:
    out: list[Violation] = []
    for i, raw in enumerate(tex.splitlines(), start=1):
        # A marker inside a comment never reaches the PDF. The LaTeX templates
        # document their own rules using the literal text "{{TOKEN}}".
        if raw.lstrip().startswith("%"):
            continue
        for m in _PLACEHOLDER_RE.finditer(raw):
            out.append(Violation(
                kind="PLACEHOLDER_LEFT", severity="blocker",
                message=f"{m.group(0)} was never filled in.",
                evidence=raw.strip()[:160], line=i, token=m.group(0),
            ))
        for m in _FILL_RE.finditer(raw):
            out.append(Violation(
                kind="FILL_IN_LEFT", severity="blocker",
                message=(
                    f"{m.group(0)} still needs a real number from you. "
                    "It was left blank on purpose rather than guessed."
                ),
                evidence=raw.strip()[:160], line=i, token=m.group(0),
            ))
    return out


def check_preamble(tex: str, expected_sha: str | None) -> list[Violation]:
    """
    Per-resume, not global. The shipped USC resume legitimately has a different
    preamble from the template, so comparing against the template would flag her
    working file as corrupt.
    """
    import hashlib

    if not expected_sha:
        return []
    head = tex.split("\\begin{document}")[0]
    sha = hashlib.sha256(head.encode("utf-8")).hexdigest()[:16]
    if sha == expected_sha:
        return []
    return [Violation(
        kind="PREAMBLE_MODIFIED", severity="important",
        message=(
            "The formatting block at the top of the file changed. That block is what "
            "makes the PDF readable by the scanners companies use."
        ),
        evidence=f"expected {expected_sha}, found {sha}",
    )]


def check_keyword_coverage(tex: str, jd_text: str, top: int = 20) -> list[Violation]:
    """
    Each must-have should appear at least twice, in different sections. Advisory:
    a real gap is a truth problem and belongs in the study plan, not forced onto
    the page.
    """
    if not jd_text.strip():
        return []
    res = legacy.ats_score(tex, jd_text, top=top)
    out: list[Violation] = []
    for row in res["rows"][:8]:
        if row["count"] == 0 and row["weight"] >= 3:
            out.append(Violation(
                kind="KEYWORD_MISSING", severity="nice",
                message=(
                    f"'{row['term']}' is a required term in this job ad and does not "
                    "appear at all. Add it only if it is genuinely true."
                ),
                evidence=row["term"], token=row["term"],
            ))
    return out


# --------------------------------------------------------------------------
# the suite
# --------------------------------------------------------------------------
def run_all(
    tex: str,
    *,
    jd_text: str = "",
    study_plan: str = "",
    preamble_sha: str | None = None,
    fb: context_loader.FactBase | None = None,
) -> GuardReport:
    fb = fb or context_loader.load()
    rep = GuardReport()
    rep.checked = [
        "fabrication", "honesty wall", "study plan wall", "banned phrases",
        "blocked claims", "placeholders", "preamble", "keyword coverage",
    ]
    for group in (
        check_fabrication(tex, fb),
        check_study_plan_wall(tex, study_plan, fb),
        check_banned_phrases(tex, fb),
        check_blocked_claims(tex),
        check_markers(tex),
        check_preamble(tex, preamble_sha),
        check_keyword_coverage(tex, jd_text),
    ):
        for v in group:
            rep.add(v)
    return rep
