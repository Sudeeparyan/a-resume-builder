"""
The fact base: context/ loaded once per run, byte-stable.

Two jobs.

1. Give every agent the same frozen bundle of her real facts, so it can be put
   behind a prompt-cache breakpoint. Byte-stability matters more than it looks
   -- a timestamp or a run id anywhere in this text silently triples the cost of
   every run with no visible symptom.

2. Build the corpus the fabrication guard checks against. Every number, tool and
   proper noun that may legally appear on a resume comes from here. If a
   generated bullet contains a token that is not in this corpus, it was invented.

context/ is hers and is never written to, with the single exception of
QUESTIONS-FOR-YOU.md.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .. import paths

# The order is the read order from CLAUDE.md, and it is deliberate.
CONTEXT_ORDER = [
    "01-basics.md", "02-education.md", "03-experience.md", "04-projects.md",
    "05-skills.md", "06-achievements.md", "07-preferences.md", "08-voice.md",
    "09-anything-else.md",
]

# Words that look like proper nouns but are ordinary prose. Kept small on
# purpose -- a generous allow-list would defeat the fabrication guard.
_CONNECTIVE = {
    "the", "and", "for", "with", "from", "into", "over", "under", "across",
    "built", "designed", "developed", "implemented", "integrated", "applied",
    "automated", "collaborated", "supported", "performed", "achieved", "wrote",
    "led", "used", "using", "reduced", "improved", "created", "added",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "summary", "education", "experience", "projects", "skills", "coursework",
    "professional", "technical", "present", "current", "remote", "onsite",
    "university", "college", "school", "bachelor", "master", "degree",
    "intern", "internship", "engineer", "developer", "analyst", "scientist",
    "research", "assistant", "teaching", "project", "data", "software",
}

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#._/-]{1,}")
_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*\s*%?")


@dataclass
class FactBase:
    """Her real facts, plus the indexes the guards need."""
    files: dict[str, str] = field(default_factory=dict)
    bundle: str = ""
    sha: str = ""
    corpus_lower: str = ""
    numbers: set[str] = field(default_factory=set)
    tokens: set[str] = field(default_factory=set)
    skills_strong: set[str] = field(default_factory=set)
    skills_used: set[str] = field(default_factory=set)
    skills_touched: set[str] = field(default_factory=set)
    skills_gap: set[str] = field(default_factory=set)
    banned_words: set[str] = field(default_factory=set)

    def has_number(self, n: str) -> bool:
        return _norm_number(n) in self.numbers

    def has_token(self, t: str) -> bool:
        t = (t or "").strip().lower().strip(".,;:()")
        if not t or t in _CONNECTIVE or len(t) < 2:
            return True                      # not a claim, nothing to verify
        return t in self.tokens

    def skill_level(self, skill: str) -> str:
        s = (skill or "").strip().lower()
        if s in self.skills_strong:
            return "strong"
        if s in self.skills_used:
            return "used_it"
        if s in self.skills_touched:
            return "touched_it"
        if s in self.skills_gap:
            return "gap"
        return "none"

    def claimable(self, skill: str) -> bool:
        """Strong and 'Used it' may appear in a bullet. 'Touched it' may not."""
        return self.skill_level(skill) in ("strong", "used_it")

    def forbidden(self, token: str) -> bool:
        """
        A named honest gap. These words DO occur in context/ -- inside the
        do-not-claim list -- so has_token() alone would wave them through.
        """
        return (token or "").strip().lower().strip(".,;:()") in self.skills_gap


def _norm_number(n: str) -> str:
    """91.83% , 1,250 and 91.83 all normalise to a comparable form."""
    s = re.sub(r"[,\s%]", "", (n or "").strip()).rstrip(".")
    if s.endswith(".0"):
        s = s[:-2]
    return s


# Banned everywhere: the workspace defaults plus her own list from 08-voice.md.
BANNED_PHRASES = [
    "passionate about", "results-oriented", "results oriented", "proven track record",
    "leveraged", "spearheaded", "synergies", "robust", "seamless", "cutting-edge",
    "cutting edge", "dynamic professional", "think outside the box", "go-getter",
    "detail-oriented", "detail oriented", "team player", "hard worker",
    "responsible for", "worked on", "helped with", "involved in", "tasked with",
    "significantly", "greatly", "substantially", "highly motivated",
    "seeking a challenging role",
]


def _skill_names(cell: str) -> set[str]:
    """
    One table cell -> every name that skill is known by.

    'AWS (Glue, Lambda, EMR, S3)'          -> aws, glue, lambda, emr, s3
    'Apache Flink / Flink SQL'             -> apache flink, flink sql, flink
    'Computer vision / object detection'   -> computer vision, object detection
    """
    names: set[str] = set()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", cell).strip()

    inner = re.findall(r"\((.*?)\)", text)
    outer = re.sub(r"\(.*?\)", "", text).strip()

    # Keep the slashed form as written too: 05-skills.md singles out "CI/CD" by
    # name, so splitting it into "ci" and "cd" would lose the lookup that matters.
    whole = outer.strip().strip(".,;·").lower()
    if 1 < len(whole) <= 48:
        names.add(whole)
        names.add(whole.replace(" / ", "/"))

    # Cells separate aliases with either a slash ("Apache Flink / Flink SQL")
    # or a comma ("Databricks, Apache Spark, PySpark"). Both are real in 05-skills.md.
    for part in re.split(r"\s*[,/]\s*", outer):
        s = part.strip().strip(".,;·").lower()
        if 1 < len(s) <= 48:
            names.add(s)
            # 'apache flink' is also matched as 'flink'
            words = s.split()
            if len(words) == 2 and words[0] in ("apache", "microsoft", "amazon", "google"):
                names.add(words[1])

    for group in inner:
        for piece in re.split(r"[,/]", group):
            s = piece.strip().strip(".,;·").lower()
            if 1 < len(s) <= 48:
                names.add(s)
    return names


def _extract_skill_tiers(text: str) -> tuple[set[str], set[str], set[str], set[str]]:
    """
    05-skills.md grades by evidence, not self-assessment, as markdown tables:

        Strong      -> may carry a bullet, metric allowed
        Used it     -> may carry a bullet, no invented metric
        Touched it  -> skills LIST only, never a bullet
        Honest gaps -> never claimed anywhere, in any form

    The gaps set is why this returns four values. Those skill names DO appear in
    context/, inside the do-not-claim list, so a naive "is this word in the
    corpus" check would happily let Snowflake onto a resume. The guard needs the
    gaps explicitly.
    """
    strong: set[str] = set()
    used: set[str] = set()
    touched: set[str] = set()
    gaps: set[str] = set()
    bucket: set[str] | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            head = line.lstrip("# ").lower()
            if head.startswith("strong"):
                bucket = strong
            elif head.startswith("used it"):
                bucket = used
            elif head.startswith("touched it"):
                bucket = touched
            elif head.startswith(("honest gap", "gaps", "never claim")):
                bucket = gaps
            elif head.startswith(("languages", "notable")):
                bucket = None
            continue

        if bucket is None or not line:
            continue

        # Shape 1 -- a markdown table row: | **Python** | evidence |
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells or not cells[0]:
                continue
            first = cells[0]
            if set(first) <= set("-: ") or first.lower() in ("skill", "gap", "area"):
                continue          # separator or header row
            bucket |= _skill_names(first)
            continue

        # Shape 2 -- a middot-separated prose run, which is how the
        # 'Touched it' and 'Honest gaps' sections are actually written.
        # Requiring the middot keeps ordinary sentences out of the skill sets.
        if "·" in line:
            for piece in line.split("·"):
                piece = piece.strip().rstrip(",")
                if piece and not piece.endswith("."):
                    bucket |= _skill_names(piece)
            continue

        # Shape 3 -- a bullet list.
        if line.startswith(("-", "*")):
            body = re.sub(r"\*\*(.+?)\*\*", r"\1", line.lstrip("-* ").strip())
            body = body.split("—")[0].split(" - ")[0]
            if body and not body.endswith("."):
                for piece in re.split(r"[,·]| and ", body):
                    bucket |= _skill_names(piece)

    # A skill can only sit in one bucket; the strongest honest claim wins.
    used -= strong
    touched -= strong | used
    gaps -= strong | used | touched
    return strong, used, touched, gaps


@lru_cache(maxsize=1)
def _load_cached(sig: str) -> FactBase:
    fb = FactBase()
    parts: list[str] = []

    for name in CONTEXT_ORDER:
        p = paths.CONTEXT / name
        text = paths.read_text(p)
        if not text.strip():
            continue
        fb.files[name] = text
        parts.append(f"### {name}\n\n{text.strip()}")

    fb.bundle = (
        "The candidate's real facts. Everything below is verified and is the ONLY\n"
        "source of anything that may appear on a resume. If a claim is not here,\n"
        "it does not exist and must not be written.\n\n"
        + "\n\n---\n\n".join(parts)
    )
    fb.sha = hashlib.sha256(fb.bundle.encode("utf-8")).hexdigest()[:16]

    corpus = "\n".join(fb.files.values())
    fb.corpus_lower = corpus.lower()
    fb.numbers = {_norm_number(m) for m in _NUMBER_RE.findall(corpus)}
    fb.tokens = {m.lower().strip(".,;:()") for m in _TOKEN_RE.findall(corpus)}
    (
        fb.skills_strong, fb.skills_used, fb.skills_touched, fb.skills_gap
    ) = _extract_skill_tiers(fb.files.get("05-skills.md", ""))
    fb.banned_words = set(BANNED_PHRASES)

    voice = fb.files.get("08-voice.md", "")
    for m in re.finditer(r'"([^"]{3,40})"', voice):
        phrase = m.group(1).strip().lower()
        if 2 < len(phrase) < 40:
            fb.banned_words.add(phrase)
    return fb


def _signature() -> str:
    """mtime+size of every context file, so an edit invalidates the cache."""
    bits = []
    for name in CONTEXT_ORDER:
        p = paths.CONTEXT / name
        if p.exists():
            st = p.stat()
            bits.append(f"{name}:{st.st_mtime_ns}:{st.st_size}")
    return "|".join(bits)


def load(force: bool = False) -> FactBase:
    if force:
        _load_cached.cache_clear()
    return _load_cached(_signature())


def open_questions() -> list[dict[str, Any]]:
    """
    The unanswered items from QUESTIONS-FOR-YOU.md.

    Four of them block specific claims -- no years-of-experience total until Q1,
    no publication until Q3 -- so the guards need to see them.
    """
    text = paths.read_text(paths.QUESTIONS)
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = re.match(r"\s*[-*]\s*\[( |x|X)\]\s*(.+)", line)
        if not m:
            continue
        out.append({"answered": m.group(1).lower() == "x", "text": m.group(2).strip()})
    return out


def blocked_claims() -> dict[str, str]:
    """Claims that stay forbidden until an open question is answered."""
    return {
        "years_total": (
            "Never state a total years-of-experience figure: the Soliton dates are "
            "still unsettled (Q1)."
        ),
        "publication": (
            "Never claim a publication: the ICCV paper is unconfirmed and appears on "
            "none of the 14 resumes (Q3)."
        ),
    }
