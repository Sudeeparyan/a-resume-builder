"""
Turn selected facts into a .tex file.

The model never writes LaTeX. It chooses content; this renders it. That makes
two rules structurally unbreakable rather than merely instructed:

  * The preamble is copied verbatim from the template, so margins, the document
    class and the \\pdfgentounicode line that makes the PDF machine-readable
    cannot drift.
  * Every character of content is escaped, so a stray % or & in a job title
    cannot silently delete the rest of a line.

Each bullet is preceded by a "% @b:<id>" comment. LaTeX ignores comments, they
never reach the PDF, and ats_check.strip_latex removes them before scoring -- so
they cost nothing and give the suggestions panel a stable anchor to point at.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from .. import legacy, paths
from ..models import TrackId
from . import factbank

# Order matters: a backslash must be replaced before anything that introduces one.
_ESCAPES = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
    ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
    ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
]

TEMPLATE_FOR_TRACK = {
    TrackId.A: "resume-track-a.tex",   # experience-led
    TrackId.B: "resume-track-b.tex",   # projects-led
    TrackId.C: "resume-track-a.tex",
    TrackId.D: "resume-track-a.tex",
}


def esc(s: str) -> str:
    """LaTeX-safe. A bare % in a bullet deletes the rest of the line."""
    out = s or ""
    for a, b in _ESCAPES:
        out = out.replace(a, b)
    # Keep an en dash rather than emitting a character the font may not have.
    return out.replace("–", "--").replace("—", "---")


def preamble_of(tex: str) -> str:
    """
    Everything before the real \\begin{document}.

    It must be matched at the start of a line: the template's own header comment
    contains the words "Only content between \\begin{document}...", and a plain
    substring search stops there -- producing a "preamble" of nothing but
    comments, and a document with no \\documentclass at all.
    """
    m = re.search(r"^[ \t]*\\begin\{document\}", tex, re.M)
    head = tex[: m.start()] if m else tex

    # Drop comment-only lines. The template's header block documents the rules
    # for a human and literally contains the words "{{TOKEN}}" and
    # "\begin{document}" -- which the shipping guards would then flag as an
    # unfilled placeholder in every generated resume. Every real command is
    # kept; only whole-line comments go.
    kept = [ln for ln in head.splitlines() if not ln.lstrip().startswith("%")]
    return "\n".join(kept).strip() + "\n"


def preamble_sha(tex: str) -> str:
    return hashlib.sha256(preamble_of(tex).encode("utf-8")).hexdigest()[:16]


@dataclass
class Header:
    name: str = "Annie Prasanna Manoharan"
    phone: str = ""
    email: str = ""
    portfolio: str = ""
    github: str = ""
    linkedin: str = ""


@dataclass
class Entry:
    """One experience or project block."""
    block_id: str
    title: str
    right: str = ""
    subtitle: str = ""
    sub_right: str = ""
    bullets: list[tuple[str, str]] = field(default_factory=list)   # (block_id, text)
    is_signature: bool = False


@dataclass
class ResumeDoc:
    track: TrackId = TrackId.A
    header: Header = field(default_factory=Header)
    summary: str = ""
    education: list[Entry] = field(default_factory=list)
    skills: list[tuple[str, str]] = field(default_factory=list)    # (category, list)
    experience: list[Entry] = field(default_factory=list)
    projects: list[Entry] = field(default_factory=list)
    signature_project: str = ""
    sources: dict[str, str] = field(default_factory=dict)          # block_id -> context/ ref
    # None means "use the track's own rule", which is what every existing
    # caller gets, so output is unchanged unless someone asks for an order.
    section_order: list[str] | None = None
    pages_target: int = 1


def _header_tex(h: Header) -> str:
    bits: list[str] = []
    if h.phone:
        bits.append(esc(h.phone))
    if h.email:
        bits.append(rf"\href{{mailto:{h.email}}}{{\underline{{{esc(h.email)}}}}}")
    for url in (h.portfolio, h.github, h.linkedin):
        if url:
            shown = url.replace("https://", "").replace("http://", "").rstrip("/")
            bits.append(rf"\href{{{url}}}{{\underline{{{esc(shown)}}}}}")
    line = " $|$ ".join(bits)
    return (
        "\\begin{center}\n"
        f"    \\textbf{{\\Large \\scshape {esc(h.name)}}} \\\\ \\vspace{{2pt}}\n"
        f"    \\small {line}\n"
        "\\end{center}\n"
    )


def _entry_tex(e: Entry, *, two_line: bool) -> str:
    out: list[str] = []
    if two_line and (e.subtitle or e.sub_right):
        out.append(
            f"    \\resumeSubheading\n"
            f"      {{{esc(e.title)}}}{{{esc(e.right)}}}\n"
            f"      {{{esc(e.subtitle)}}}{{{esc(e.sub_right)}}}"
        )
    else:
        out.append(f"    \\resumeSingleHeading\n      {{{esc(e.title)}}}{{{esc(e.right)}}}")
    if e.bullets:
        out.append("      \\resumeItemListStart")
        for bid, text in e.bullets:
            out.append(f"        % @b:{bid}")
            out.append(f"        \\resumeItem{{{esc(text)}}}")
        out.append("      \\resumeItemListEnd")
    return "\n".join(out)


def render(doc: ResumeDoc, *, template: str | None = None) -> str:
    """Produce the complete .tex. The preamble is copied, never generated."""
    tpl_name = template or TEMPLATE_FOR_TRACK.get(doc.track, "resume-track-a.tex")
    tpl = paths.read_text(paths.LATEX_TEMPLATES / tpl_name)
    if not tpl.strip():
        raise FileNotFoundError(f"The LaTeX template {tpl_name} is missing.")

    body: list[str] = [preamble_of(tpl).rstrip(), "", "\\begin{document}"]

    # The page target travels with the file, so system/scripts/build_pdf.py and
    # the dashboard can never disagree about how long this resume is meant to be.
    #
    # It MUST sit after \begin{document}. preamble_of() drops comment-only
    # lines, but guards.check_preamble() hashes the raw split on
    # \begin{document} -- so a comment placed above it changes that hash and
    # fires PREAMBLE_MODIFIED on every generated resume.
    body.append(f"% @pages:{max(1, int(doc.pages_target or 1))}")
    body.append("")
    body.append(_header_tex(doc.header))

    if doc.summary:
        body += ["\\section{Summary}", f"\\small{{{esc(doc.summary)}}}", ""]

    if doc.education:
        body.append("\\section{Education}")
        body.append("  \\resumeSubHeadingListStart")
        for e in doc.education:
            body.append(_entry_tex(e, two_line=True))
        body.append("  \\resumeSubHeadingListEnd")
        body.append("")

    if doc.skills:
        body.append("\\section{Technical Skills}")
        body.append(" \\begin{itemize}[leftmargin=0.15in, label={}]")
        body.append("    \\small{\\item{")
        for cat, items in doc.skills:
            body.append(f"     \\textbf{{{esc(cat)}}}{{: {esc(items)}}} \\\\")
        body.append("    }}")
        body.append(" \\end{itemize}")
        body.append("")

    def section(title: str, entries: list[Entry], two_line: bool) -> None:
        if not entries:
            return
        body.append(f"\\section{{{title}}}")
        body.append("  \\resumeSubHeadingListStart")
        for e in entries:
            body.append(_entry_tex(e, two_line=two_line))
        body.append("  \\resumeSubHeadingListEnd")
        body.append("")

    # An explicit order wins; otherwise Track B leads with projects and every
    # other track leads with experience, exactly as before.
    order = doc.section_order or (
        ["projects", "experience"] if doc.track == TrackId.B
        else ["experience", "projects"]
    )
    for name in order:
        if name == "projects":
            section("Projects", doc.projects, False)
        else:
            section("Professional Experience", doc.experience, True)

    body.append("\\end{document}")
    return "\n".join(body) + "\n"


def pages_hint(tex: str, default: int = 1) -> int:
    """
    The page target the file carries, written by render() as '% @pages:N'.

    Lets a caller compile a resume correctly without first looking up its spec
    in the database -- and lets the CLI build script agree with the dashboard.
    """
    m = re.search(r"^\s*%\s*@pages:\s*(\d+)\s*$", tex or "", re.M)
    if not m:
        return default
    try:
        return max(1, min(2, int(m.group(1))))
    except ValueError:
        return default


def anchors(tex: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, line in enumerate(tex.splitlines(), start=1):
        m = re.match(r"^\s*%\s*@b:([A-Za-z0-9._-]+)\s*$", line)
        if m:
            out[m.group(1)] = i + 1
    return out


# --------------------------------------------------------------------------
# suggestion actions -- the two safe, mechanical edits the UI can apply on her
# behalf without ever writing prose. Both are deterministic text surgery, not
# an LLM rewrite, so neither can introduce a claim that was not already true.
# --------------------------------------------------------------------------
def remove_block(tex: str, block_id: str) -> str:
    """
    Delete one anchored bullet -- its '% @b:<id>' comment and the resumeItem
    line right after it, which is always exactly how compose_tex() writes them.
    Used to apply a fabrication/banned-phrase finding by cutting the offending
    line rather than rewriting it.
    """
    pat = re.compile(rf"^\s*%\s*@b:{re.escape(block_id)}\s*$")
    lines = tex.splitlines()
    out: list[str] = []
    i = 0
    found = False
    while i < len(lines):
        if not found and pat.match(lines[i]):
            found = True
            i += 2          # the anchor comment, then the bullet line it labels
            continue
        out.append(lines[i])
        i += 1
    if not found:
        raise ValueError(f"That line is no longer in the file (block {block_id}).")
    return "\n".join(out) + "\n"


def add_skill_keyword(tex: str, keyword: str) -> str:
    """
    Append a truthful, already-omitted keyword to the first Technical Skills
    line. The caller must have already verified she can claim it -- this
    function only places text, it does not decide honesty.

    Two skill-line shapes exist on disk and both must work: the composer's own
    template writes '\\textbf{Cat}{: items} \\\\', but her real, previously
    shipped resumes (authored outside this dashboard) write the category and
    items both inside one '\\resumeItem{\\textbf{Cat}: items}'. Rather than
    matching each shape's brace layout, this finds the first skills line and
    appends just before its own trailing closing brace(s) -- true in both
    shapes, since neither ever puts a literal '{' or '}' inside the item list.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("There is no keyword to add.")

    start = tex.find("\\section{Technical Skills}")
    if start == -1:
        raise ValueError("This resume has no Technical Skills section to add to.")
    end = tex.find("\\section{", start + 1)
    if end == -1:
        end = len(tex)
    block = tex[start:end]

    if keyword.lower() in legacy.strip_latex(block).lower():
        raise ValueError(f"'{keyword}' is already on this resume.")

    lines = block.splitlines(keepends=True)
    target = next((i for i, ln in enumerate(lines) if "\\textbf{" in ln), None)
    if target is None:
        raise ValueError("Could not find a skills line to add to.")

    line = lines[target]
    ending = ""
    m = re.search(r"(\r?\n)$", line)
    if m:
        ending, line = m.group(1), line[: m.start()]

    trailer = ""
    core = line.rstrip()
    trailing_ws = line[len(core):]
    if core.endswith("\\\\"):
        trailer, core = " \\\\", core[:-2].rstrip()
    if not core.endswith("}"):
        raise ValueError("Could not find a skills line to add to.")

    lines[target] = f"{core[:-1]}, {esc(keyword)}}}{trailer}{trailing_ws}{ending}"
    new_block = "".join(lines)
    return tex[:start] + new_block + tex[end:]
