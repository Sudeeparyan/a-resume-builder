"""
Her real experience and projects, parsed into selectable blocks.

context/ is prose written for a human. To build a resume the system has to pick
from it, so this turns those files into structured entries WITHOUT changing a
single word: every bullet is carried through verbatim. Selection is allowed,
invention is not, and the renderer downstream can only emit what appears here.

Two files are parsed:
  03-experience.md -- one block per employer, with alternative "framings" of the
                      same work. Only one framing is ever used, chosen by track.
  04-projects.md   -- P1..P10, each with a stack line, track tags and bullets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .. import paths
from . import context_loader

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
_PID = re.compile(r"^##\s*(P\d+)\s*[—–-]\s*(.+)$")


def _clean(s: str) -> str:
    """Strip markdown emphasis and backticks, keep the words exactly."""
    s = _BOLD.sub(r"\1", s or "")
    s = s.replace("`", "")
    # "**Stack:** Kafka" split on its colon leaves a dangling "**" on the value,
    # and a bold run that wrapped across source lines leaves an unmatched pair.
    s = s.replace("**", "")
    s = s.strip().strip("*").strip()
    return re.sub(r"\s+", " ", s).strip()


def _unwrap(lines: list[str]) -> list[str]:
    """
    Join wrapped bullets back into one line each.

    context/ is hand-written prose wrapped at about 100 columns, so a single
    bullet routinely spans three source lines. Treating each line as its own
    bullet truncates every one of them mid-sentence -- and splits bold runs so
    the "**" markers survive into the PDF.
    """
    out: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        is_continuation = (
            out
            and stripped
            and raw[:1] in (" ", "\t")
            and not _BULLET.match(line)
            and not stripped.startswith(("#", "|", ">", "---"))
            and _BULLET.match(out[-1] or "")
        )
        if is_continuation:
            out[-1] = out[-1].rstrip() + " " + stripped
        else:
            out.append(line)
    return out


@dataclass
class Bullet:
    text: str
    source: str                    # which context/ file and section it came from

    @property
    def tokens(self) -> set[str]:
        return {w.lower().strip(".,;:()") for w in re.findall(r"[A-Za-z][\w+#./-]*", self.text)}


@dataclass
class Framing:
    """One way of describing the same real work. Never merge two of them."""
    name: str
    bullets: list[Bullet] = field(default_factory=list)
    reusable: bool = True


@dataclass
class Role:
    employer: str
    location: str = ""
    title: str = ""
    dates: str = ""
    framings: list[Framing] = field(default_factory=list)
    notes: str = ""
    cap_exempt_note: str = ""
    contested: bool = False        # dates or title still unsettled by an open question

    def framing(self, prefer: str = "") -> Framing | None:
        usable = [f for f in self.framings if f.reusable and f.bullets]
        if not usable:
            return None
        if prefer:
            for f in usable:
                if prefer.lower() in f.name.lower():
                    return f
        return usable[0]


@dataclass
class Project:
    pid: str
    name: str
    stack: str = ""
    tracks: list[str] = field(default_factory=list)
    bullets: list[Bullet] = field(default_factory=list)
    note: str = ""
    coursework: bool = False

    @property
    def tokens(self) -> set[str]:
        base = {w.lower() for w in re.findall(r"[A-Za-z][\w+#./-]*", f"{self.name} {self.stack}")}
        for b in self.bullets:
            base |= b.tokens
        return base


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def _parse_experience(text: str) -> list[Role]:
    roles: list[Role] = []
    current: Role | None = None
    framing: Framing | None = None

    for raw in _unwrap(text.splitlines()):
        line = raw.rstrip()

        if line.startswith("## "):
            head = _clean(line[3:])
            if head.lower().startswith(("concurrency", "what this", "notes")):
                current = None
                framing = None
                continue
            employer, _, location = head.partition("—")
            current = Role(employer=employer.strip(), location=location.strip())
            framing = None
            roles.append(current)
            continue

        if current is None:
            continue

        if line.startswith("### "):
            name = _clean(line[4:])
            low = name.lower()
            # A framing kept only as a historical record must never be reused --
            # 03-experience.md says so explicitly for the _DS data-science text.
            reusable = not low.startswith(("additional detail", "two conflicting"))
            framing = Framing(name=name, reusable=reusable)
            current.framings.append(framing)
            if "conflicting" in low or "version" in low:
                current.contested = True
            continue

        m = _BULLET.match(line)
        if m:
            body = _clean(m.group(1))
            if not body:
                continue
            if framing is None:
                framing = Framing(name="default")
                current.framings.append(framing)
            framing.bullets.append(Bullet(text=body, source=f"03-experience.md § {current.employer}"))
            continue

        # The title/date line sits immediately under the employer heading. A
        # bold line further down is something else entirely -- "Cap-exempt
        # relevance:" or "Version A -- single role" -- and taking it as a job
        # title produces nonsense on the page.
        if line.startswith("**") and framing is None and not current.title and not current.dates:
            parts = [_clean(p) for p in line.split("—")]
            if len(parts) >= 2:
                current.title, current.dates = parts[0], parts[1]
            else:
                blob = _clean(line)
                if re.search(r"\b(19|20)\d{2}\b", blob):
                    current.dates = blob
                else:
                    current.title = blob
            continue

        if "cap-exempt" in line.lower():
            current.cap_exempt_note = _clean(line)

        if line.strip() and not line.startswith((">", "#")):
            current.notes = (current.notes + " " + _clean(line)).strip()

    # Honour a "do not reuse" instruction written in the prose.
    #
    # 03-experience.md says the data-science framing of the InsOps role "is kept
    # only as a historical record of what _DS once said, not for reuse". That is
    # a real constraint on what may appear on a resume, and it lives in a
    # sentence rather than a heading, so it has to be read from the prose.
    for r in roles:
        notes = (r.notes or "").lower()
        # Scope the match to the sentence carrying the instruction. Searching the
        # whole note would also hit "use the data-ENGINEERING framing on every
        # resume" -- the opposite instruction, in a neighbouring clause.
        banned_sentences = [
            s for s in re.split(r"[.;]", notes)
            if any(k in s for k in ("not for reuse", "historical record", "never for reuse"))
        ]
        if not banned_sentences:
            continue
        for f in r.framings:
            head = re.split(r"[ /(]", f.name.lower().strip())[0]
            if head and len(head) > 3 and any(head in s for s in banned_sentences):
                f.reusable = False

    # Some headings ARE the job title -- "## Teaching Assistant — Dept. of CSE,
    # University of Arkansas" names the role first and the employer second.
    # Without this the resume shows an employer and no title.
    # ...but only when the first half really is a job title. "Soliton
    # Technologies — India" is employer and country; swapping it would print
    # "Soliton Technologies" as the role and "India" as the employer.
    role_word = re.compile(
        r"\b(assistant|engineer|intern|developer|scientist|analyst|manager|"
        r"consultant|associate|researcher|technician|lead|architect)\b",
        re.I,
    )
    for r in roles:
        if r.title:
            continue
        if r.location and role_word.search(r.employer):
            r.title, r.employer, r.location = r.employer, r.location, ""
        else:
            r.title = r.employer
    return [r for r in roles if r.employer and any(f.bullets for f in r.framings)]


def _parse_projects(text: str) -> list[Project]:
    projects: list[Project] = []
    cur: Project | None = None
    in_bullets = False

    for raw in _unwrap(text.splitlines()):
        line = raw.rstrip()
        m = _PID.match(line)
        if m:
            cur = Project(pid=m.group(1), name=_clean(m.group(2)))
            projects.append(cur)
            in_bullets = False
            continue
        if cur is None:
            continue
        if line.startswith("## "):
            cur = None
            continue

        low = line.lower()
        if low.startswith("**stack:**"):
            cur.stack = _clean(line.split(":", 1)[1])
            continue
        if low.startswith("**tracks:**"):
            cur.tracks = [t.strip() for t in _clean(line.split(":", 1)[1]).split(",")]
            continue
        if low.startswith(("**appears on:**", "**status:**")):
            continue

        m2 = _BULLET.match(line)
        if m2:
            body = _clean(m2.group(1))
            if body:
                cur.bullets.append(Bullet(text=body, source=f"04-projects.md § {cur.pid}"))
                in_bullets = True
            continue

        if not line.strip() or line.startswith(("---", "#")):
            continue

        # P9 describes its two sub-projects as bold-led paragraphs rather than a
        # bullet list. Without this it parses to zero bullets and disappears.
        if line.startswith("**") and "**" in line[2:] and not in_bullets:
            body = _clean(line)
            if len(body) > 30:
                cur.bullets.append(Bullet(text=body, source=f"04-projects.md § {cur.pid}"))
                continue

        # Trailing prose is a note wherever it appears -- P10's "Label this as
        # coursework" sits AFTER its bullets, and it is the line that matters.
        cur.note = (cur.note + " " + _clean(line)).strip()

    for p in projects:
        blob = f"{p.name} {p.note}".lower()
        if "coursework" in blob or "never a signature" in blob:
            p.coursework = True
    return [p for p in projects if p.bullets]


@lru_cache(maxsize=1)
def _load(sig: str) -> tuple[list[Role], list[Project]]:
    return (
        _parse_experience(paths.read_text(paths.CONTEXT / "03-experience.md")),
        _parse_projects(paths.read_text(paths.CONTEXT / "04-projects.md")),
    )


def load(force: bool = False) -> tuple[list[Role], list[Project]]:
    if force:
        _load.cache_clear()
    sig = ""
    for name in ("03-experience.md", "04-projects.md"):
        p = paths.CONTEXT / name
        if p.exists():
            sig += f"{name}:{p.stat().st_mtime_ns}|"
    return _load(sig)


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------
def score_against(tokens: set[str], target: set[str]) -> int:
    return len(tokens & target)


# Words that appear in every job ad and every resume, so matching on them tells
# us nothing about fit.
_NOISE = {
    "the", "and", "for", "with", "you", "our", "will", "work", "team", "role",
    "experience", "years", "strong", "using", "used", "use", "data", "systems",
    "engineer", "engineering", "software", "development", "developer", "new",
    "including", "across", "within", "ability", "skills", "knowledge", "such",
}


def jd_tokens(jd_text: str, extra: list[str] | None = None) -> set[str]:
    """
    What this job actually asks for, as single comparable words.

    jd_keywords returns weighted PHRASES ("apache kafka", "real-time streaming").
    Intersecting a phrase against the single words of a project bullet matches
    nothing, so each phrase is also split into its words. Without this every
    project scores the same and the ranking is noise.
    """
    from .. import legacy

    out: set[str] = set()
    for term, _weight in legacy.jd_keywords(jd_text, 30):
        low = term.lower()
        out.add(low)
        out |= {w for w in re.findall(r"[a-z][\w+#./-]*", low) if len(w) > 2}

    # jd_keywords needs requirement-style lines and returns nothing for a short
    # or unstructured ad, which would leave every project tied. Always add the
    # raw words too, so ranking degrades gracefully instead of going silent.
    out |= {
        w for w in re.findall(r"[a-z][\w+#./-]*", (jd_text or "").lower())
        if len(w) > 2
    }

    for term in extra or []:
        low = term.lower()
        out.add(low)
        out |= {w for w in re.findall(r"[a-z][\w+#./-]*", low) if len(w) > 2}
    return out - _NOISE


def rank_projects(
    projects: list[Project], target: set[str], *, exclude: set[str] | None = None,
) -> list[tuple[Project, int]]:
    """
    Rank by real overlap with what the job asks for.

    Ties break toward the project with a recorded outcome number, because
    evidence strength is 20% of the recruiter score and a metric is the
    difference between a claim and a proof.
    """
    exclude = exclude or set()
    scored: list[tuple[Project, int]] = []
    for p in projects:
        if p.pid in exclude or p.coursework:
            continue
        n = score_against(p.tokens, target)
        has_metric = any(re.search(r"\d", b.text) for b in p.bullets)
        scored.append((p, n * 10 + (3 if has_metric else 0)))
    return sorted(scored, key=lambda kv: -kv[1])


def rank_roles(roles: list[Role], target: set[str]) -> list[tuple[Role, Framing, int]]:
    out: list[tuple[Role, Framing, int]] = []
    for r in roles:
        best: tuple[Framing, int] | None = None
        for f in r.framings:
            if not f.reusable or not f.bullets:
                continue
            n = sum(score_against(b.tokens, target) for b in f.bullets)
            if best is None or n > best[1]:
                best = (f, n)
        if best:
            out.append((r, best[0], best[1]))
    return sorted(out, key=lambda t: -t[2])
