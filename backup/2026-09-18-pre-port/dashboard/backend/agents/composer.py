"""
Build a resume for one job, from her real facts only.

Works with or without a model. Without one it is pure selection: pick the track,
pick the framing, pick the projects that overlap most with what the ad asks for,
and carry every bullet through VERBATIM. Nothing is rewritten, so nothing can be
invented -- which is why no-key mode is the safest mode, not the weakest.

With a model the same structure is produced, then the recruiter audit rewrites
bullets under the Google XYZ rule and the fabrication guard re-checks every line
before anything can be downloaded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace as _dc_replace
from typing import Any

import yaml

from .. import paths
from ..models import JDAnalysis, JobPosting, TrackId
from ..services import context_loader, factbank, latex_render
from ..services.latex_render import Entry, Header, ResumeDoc
from . import deterministic as D

# How many bullets each slot gets. A one-page graduate resume should be FULL --
# a thin page reads as thin experience, which is the failure that gets missed.
BULLETS_FIRST_ROLE = 3
BULLETS_OTHER_ROLE = 2
BULLETS_SIGNATURE = 3
BULLETS_SUPPORTING = 2
MAX_ROLES = 4
MAX_PROJECTS = 3


@dataclass
class Selection:
    """
    Everything that shapes one composition, passed explicitly.

    These budgets used to be module globals that builder._apply() mutated in
    place. The fit loop awaits a compile between steps, so two concurrent builds
    -- which a chat panel makes routine -- interleaved and silently produced a
    wrongly shaped resume with no error. The defaults below ARE the old globals,
    so a caller that passes no selection gets byte-identical output.

    The include/exclude fields are how the resume chat expresses "add my MiGa
    project" or "drop the TA job" without ever writing a word of the page.
    """
    track: TrackId | None = None
    pages_target: int = 1

    # budgets
    max_roles: int = MAX_ROLES
    bullets_first_role: int = BULLETS_FIRST_ROLE
    bullets_other_role: int = BULLETS_OTHER_ROLE
    max_projects: int = MAX_PROJECTS
    bullets_signature: int = BULLETS_SIGNATURE
    bullets_supporting: int = BULLETS_SUPPORTING

    # shape
    section_order: list[str] | None = None      # None = the track's own rule
    show_coursework: bool = True
    prefer_shorter_bullets: bool = False

    # picks
    include_projects: list[str] = field(default_factory=list)   # pids, in order
    exclude_projects: set[str] = field(default_factory=set)
    signature_project: str = ""
    include_roles: list[str] = field(default_factory=list)      # employer names
    exclude_roles: set[str] = field(default_factory=set)
    framing_preference: dict[str, str] = field(default_factory=dict)

    def replace(self, **kw: Any) -> "Selection":
        return _dc_replace(self, **kw)


def _name_matches(name: str, wanted: str) -> bool:
    """
    Employer names reach us from three places -- her headings, the tracker and a
    chat message -- and rarely agree on punctuation. Match either direction so
    "Soliton" finds "Soliton Technologies".
    """
    a, b = (name or "").strip().lower(), (wanted or "").strip().lower()
    return bool(a and b and (a in b or b in a))


def _matches_any(name: str, wanted) -> bool:
    return any(_name_matches(name, w) for w in (wanted or ()))


def _pick_bullets(bullets: list, target: set[str], limit: int, shorter: bool) -> list:
    """
    Most relevant first. With shorter=True a tie breaks toward the shorter line
    -- a SELECTION between bullets she already wrote, never a rewrite of one.
    """
    if shorter:
        return sorted(
            bullets,
            key=lambda b: (-factbank.score_against(b.tokens, target), len(b.text)),
        )[:limit]
    return sorted(bullets, key=lambda b: -factbank.score_against(b.tokens, target))[:limit]


def _order_roles(ranked: list, sel: Selection) -> list:
    """Drop what she excluded, pull what she pinned to the front."""
    kept = [t for t in ranked if not _matches_any(t[0].employer, sel.exclude_roles)]
    if not sel.include_roles:
        return kept
    pinned, rest = [], []
    for t in kept:
        (pinned if _matches_any(t[0].employer, sel.include_roles) else rest).append(t)
    pinned.sort(key=lambda t: next(
        (i for i, w in enumerate(sel.include_roles) if _name_matches(t[0].employer, w)),
        len(sel.include_roles),
    ))
    return pinned + rest


def _order_projects(ranked: list, sel: Selection) -> list:
    """Signature first if she named one, then her pins, then relevance order."""
    kept = [t for t in ranked if t[0].pid not in sel.exclude_projects]
    by_pid = {t[0].pid: t for t in kept}
    head_pids: list[str] = []
    for pid in ([sel.signature_project] if sel.signature_project else []) + list(sel.include_projects):
        if pid in by_pid and pid not in head_pids:
            head_pids.append(pid)
    head = [by_pid[pid] for pid in head_pids]
    tail = [t for t in kept if t[0].pid not in set(head_pids)]
    return head + tail


def _profile_yaml() -> dict[str, Any]:
    try:
        return yaml.safe_load(paths.read_text(paths.PROFILE_YML)) or {}
    except yaml.YAMLError:
        return {}


def _header() -> Header:
    c = (_profile_yaml().get("candidate") or {})
    return Header(
        name=c.get("full_name") or "Annie Prasanna Manoharan",
        phone=c.get("phone") or "",
        email=c.get("email") or "",
        portfolio=c.get("portfolio_url") or "",
        github=c.get("github") or "",
        linkedin=c.get("linkedin") or "",
    )


def _education() -> list[Entry]:
    """
    Parsed from 02-education.md, with coursework promoted only when the ad names
    it. Every module listed there is real; which ones show is a selection.
    """
    text = paths.read_text(paths.CONTEXT / "02-education.md")
    out: list[Entry] = []
    # The file names the degree as a heading, then the school and dates beneath:
    #   ## Master of Science in Computer Engineering
    #   **University of Arkansas, Fayetteville, AR** — Aug 2024 – May 2026
    degree = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            head = line[3:].strip()
            degree = head if re.search(r"\b(bachelor|master|b\.?e\.?|m\.?s\.?|ph)", head, re.I) else ""
            continue
        if not degree or not line.startswith("**"):
            continue
        m = re.match(r"\*\*(.+?)\*\*\s*[—–-]+\s*(.+)$", line)
        if not m:
            continue
        school, dates = m.group(1).strip(), m.group(2).strip(" *")
        if not re.search(r"\b(19|20)\d{2}\b", dates):
            continue
        school_name, _, location = school.partition(",")
        out.append(Entry(
            block_id=f"edu.{len(out) + 1}",
            title=school_name.strip(), right=dates.replace("–", "--"),
            subtitle=degree, sub_right=location.strip(),
        ))
        degree = ""
        if len(out) == 2:
            break
    if not out:
        out = [
            Entry(block_id="edu.1", title="University of Arkansas",
                  right="Aug 2024 -- May 2026",
                  subtitle="M.S. in Computer Engineering", sub_right="Fayetteville, AR"),
            Entry(block_id="edu.2", title="Sri Ramakrishna Engineering College",
                  right="Aug 2019 -- May 2023",
                  subtitle="B.E. in Electronics and Communication Engineering", sub_right="India"),
        ]
    return out


def _coursework_line(target: set[str]) -> str:
    """The modules the ad actually names, from the real union list."""
    text = paths.read_text(paths.CONTEXT / "02-education.md").lower()
    modules = [
        "Algorithms", "Database Management Systems", "Advanced Database Management Systems",
        "Data Mining", "Artificial Intelligence", "Machine Learning", "Image Processing",
        "Cryptography", "Privacy Enhancing Techniques",
    ]
    picked = [m for m in modules if m.lower() in text and (
        {w for w in m.lower().split()} & target
    )]
    return ", ".join(picked[:5])


SKILL_CATEGORIES: list[tuple[str, list[str]]] = [
    ("Languages", ["python", "sql", "c++", "c#", "embedded c", "java", "verilog"]),
    ("Data Engineering", ["apache kafka", "apache flink", "flink sql", "apache airflow",
                          "clickhouse", "databricks", "apache spark", "pyspark",
                          "delta lake", "etl", "aws"]),
    ("Machine Learning", ["pytorch", "scikit-learn", "computer vision", "lstm",
                          "yolo11n-pose", "oc-sort", "langchain", "faiss", "rag"]),
    ("Cloud and Tools", ["aws", "glue", "lambda", "emr", "s3", "grafana", "docker",
                         "git", "flask", "streamlit", "postgresql", "mysql"]),
    ("Embedded and Test", ["labview", "ni teststand", "mavis", "test automation",
                           "fpga", "vivado", "microblaze", "pic16f887", "ansys hfss"]),
]


def _skills(target: set[str], fb: context_loader.FactBase) -> list[tuple[str, str]]:
    """
    Only skills she can actually claim, ordered so the ad's own terms come first.

    A 'Touched it' skill may appear in this list -- that is what the list is for --
    but it can never carry a bullet. An honest gap never appears at all.
    """
    out: list[tuple[str, str]] = []
    for category, candidates in SKILL_CATEGORIES:
        claimable = [
            s for s in candidates
            if fb.skill_level(s) in ("strong", "used_it", "touched_it")
        ]
        if not claimable:
            continue
        wanted = [s for s in claimable if s in target or any(w in target for w in s.split())]
        rest = [s for s in claimable if s not in wanted]
        ordered = wanted + rest
        if not ordered:
            continue
        pretty = ", ".join(_pretty(s) for s in ordered[:9])
        out.append((category, pretty))
    return out[:5]


_PRETTY = {
    "sql": "SQL", "c++": "C++", "c#": "C#", "aws": "AWS", "etl": "ETL",
    "rag": "RAG", "fpga": "FPGA", "s3": "S3", "emr": "EMR",
    "ni teststand": "NI TestStand", "mavis": "MAVIS", "labview": "LabVIEW",
    "pytorch": "PyTorch", "scikit-learn": "Scikit-learn", "clickhouse": "ClickHouse",
    "pyspark": "PySpark", "postgresql": "PostgreSQL", "mysql": "MySQL",
    "faiss": "FAISS", "langchain": "LangChain", "lstm": "LSTM",
    "ansys hfss": "Ansys HFSS", "pic16f887": "PIC16F887", "oc-sort": "OC-SORT",
    "yolo11n-pose": "YOLO11n-Pose", "flink sql": "Flink SQL",
}


def _pretty(s: str) -> str:
    if s in _PRETTY:
        return _PRETTY[s]
    return " ".join(w.capitalize() if w.islower() else w for w in s.split())


def compose(
    job: JobPosting,
    *,
    jd: JDAnalysis | None = None,
    track: TrackId | None = None,
    exclude_projects: set[str] | None = None,
    selection: Selection | None = None,
) -> tuple[ResumeDoc, dict[str, Any]]:
    """
    Select the true slice of her history that best answers this ad.

    Returns the document and a report explaining every choice, so the UI can
    show why a project was picked rather than asserting it.

    `track` and `exclude_projects` are kept as direct arguments because callers
    already pass them; they are folded into the selection below.
    """
    sel = selection or Selection()
    if track is not None:
        sel = sel.replace(track=track)
    if exclude_projects:
        sel = sel.replace(exclude_projects=set(sel.exclude_projects) | set(exclude_projects))

    fb = context_loader.load()
    roles, projects = factbank.load()

    extra = [r.keyword or r.text for r in (jd.must_haves if jd else [])]
    target = factbank.jd_tokens(job.jd_text, extra)

    if sel.track is None:
        chosen_track, track_note, _hits = D.classify_track(job.jd_text, job.role_title)
    else:
        chosen_track, track_note = sel.track, "chosen for you"

    doc = ResumeDoc(track=chosen_track, header=_header())
    doc.section_order = list(sel.section_order) if sel.section_order else None
    doc.pages_target = sel.pages_target
    doc.education = _education()

    course = _coursework_line(target) if sel.show_coursework else ""
    if course and doc.education:
        doc.education[0].sub_right = ""
        doc.education[0].bullets = [("edu.1.b1", f"Coursework: {course}")]

    doc.skills = _skills(target, fb)

    # -- experience --------------------------------------------------------
    ranked_roles = _order_roles(factbank.rank_roles(roles, target), sel)
    report_roles: list[dict[str, Any]] = []
    for i, (role, framing, score) in enumerate(ranked_roles[:sel.max_roles]):
        # A framing she named by hand wins over the best-scoring one, but only
        # if it is reusable -- 03-experience.md marks some as history only.
        for employer, want in sel.framing_preference.items():
            if _name_matches(role.employer, employer):
                alt = role.framing(prefer=want)
                if alt is not None:
                    framing = alt
                break

        limit = sel.bullets_first_role if i == 0 else sel.bullets_other_role
        chosen = _pick_bullets(framing.bullets, target, limit, sel.prefer_shorter_bullets)
        # A block whose heading is just the employer takes its job title from
        # the framing -- "Project Engineer bullets" means the Project Engineer
        # role. Without this the resume prints the company name as the title.
        title = role.title or role.employer
        if title.strip().lower() == role.employer.strip().lower():
            derived = re.sub(
                r"\s*(bullets|framing).*$", "", framing.name, flags=re.I
            ).strip(" :-—")
            if derived and re.search(
                r"\b(engineer|intern|assistant|developer|scientist|analyst)\b",
                derived, re.I,
            ):
                title = derived

        e = Entry(
            block_id=f"emp.{i + 1}",
            title=title,
            right=role.dates,
            subtitle=role.employer,
            sub_right=role.location,
            bullets=[(f"emp.{i + 1}.b{n + 1}", b.text) for n, b in enumerate(chosen)],
        )
        doc.experience.append(e)
        for n, b in enumerate(chosen):
            doc.sources[f"emp.{i + 1}.b{n + 1}"] = b.source
        report_roles.append({
            "employer": role.employer, "title": role.title,
            "framing": framing.name, "relevance": score,
        })

    # -- projects ----------------------------------------------------------
    ranked = _order_projects(
        factbank.rank_projects(projects, target, exclude=sel.exclude_projects), sel
    )
    report_projects: list[dict[str, Any]] = []
    for i, (proj, score) in enumerate(ranked[:sel.max_projects]):
        limit = sel.bullets_signature if i == 0 else sel.bullets_supporting
        chosen = _pick_bullets(proj.bullets, target, limit, sel.prefer_shorter_bullets)
        e = Entry(
            block_id=f"proj.{i + 1}",
            title=proj.name,
            right=proj.stack,
            bullets=[(f"proj.{i + 1}.b{n + 1}", b.text) for n, b in enumerate(chosen)],
            is_signature=(i == 0),
        )
        doc.projects.append(e)
        for n, b in enumerate(chosen):
            doc.sources[f"proj.{i + 1}.b{n + 1}"] = b.source
        report_projects.append({
            "id": proj.pid, "name": proj.name, "relevance": score,
            "signature": i == 0,
        })
        if i == 0:
            doc.signature_project = proj.pid

    report = {
        "track": chosen_track.value,
        "track_reason": track_note,
        "signature_project": doc.signature_project,
        "roles": report_roles,
        "projects": report_projects,
        "coursework_shown": course,
        "section_order": doc.section_order,
        "generated_by": "rules",
        "note": (
            "Every bullet is copied word for word from your context files. Nothing "
            "was rewritten, so nothing could be invented."
        ),
    }
    return doc, report


def compose_tex(job: JobPosting, **kw: Any) -> tuple[str, dict[str, Any]]:
    doc, report = compose(job, **kw)
    tex = latex_render.render(doc)
    report["preamble_sha"] = latex_render.preamble_sha(tex)
    report["anchors"] = latex_render.anchors(tex)
    report["sources"] = doc.sources
    return tex, report
