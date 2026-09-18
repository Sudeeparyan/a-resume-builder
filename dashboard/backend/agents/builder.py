"""
Build one application: select, render, fit the page, gate, and write to disk.

The auto-fit loop is the interesting part. The playbook is explicit that a thin
one-pager is exactly as bad as a two-pager, and is the failure that gets missed
more often -- so this does not just compile once and hope. It grows the content
until the page is genuinely full, then steps back the moment it spills, and the
last version that fit wins.

Growing means adding MORE REAL BULLETS from context/, never padding: the only
thing that changes between attempts is how many of her existing bullets are
shown. If her real material runs out before the page is full, that is reported
as a shortfall -- it is never papered over.

The rungs come from resume_spec.fit_ladder(spec), which is also where a two-page
target lengthens the ladder and scales the fill threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import legacy
from ..models import JDAnalysis, JobPosting, TrackId
from ..services import guards, resume_spec, tectonic, workspace_sync
from . import composer


@dataclass
class BuildResult:
    tex: str = ""
    report: dict[str, Any] = None
    compile: Any = None
    guards: Any = None
    folder: str = ""
    attempts: int = 0
    fit_note: str = ""
    spec: Any = None
    short_of_target: bool = False   # ran out of real material before filling the page


async def build(
    job: JobPosting,
    *,
    jd: JDAnalysis | None = None,
    track: TrackId | None = None,
    exclude_projects: set[str] | None = None,
    spec: Any = None,
    resume_id: str = "build",
) -> BuildResult:
    """
    Compose, then grow the page until it is full without spilling.

    Returns the best version found: at the spec's page target, as full as her
    real material allows, with every claim traced back to context/.

    Nothing mutates module state any more -- each rung is a separate Selection,
    so two concurrent builds cannot interleave and corrupt each other.
    """
    spec = spec if spec is not None else resume_spec.Spec()
    if track is not None:
        spec = spec.with_selection(track=track)
    if exclude_projects:
        spec = spec.with_selection(
            exclude_projects=set(spec.selection.exclude_projects) | set(exclude_projects)
        )

    target_pages = max(1, spec.pages_target)
    fill_target = spec.min_fill_chars
    best: BuildResult | None = None
    attempts = 0

    for selection in resume_spec.fit_ladder(spec):
        attempts += 1
        tex, report = composer.compose_tex(job, jd=jd, selection=selection)
        out = await tectonic.compile_tex(
            tex, mode="draft", resume_id=f"{resume_id}-fit{attempts}",
            return_pdf=False, want_pages=target_pages, allow_fewer=True,
        )
        if not out.ok or out.pages == 0:
            # A LaTeX failure is not a fitting problem; stop and report it.
            if best is None:
                best = BuildResult(tex=tex, report=report, compile=out, attempts=attempts)
            break

        if out.pages > target_pages:
            # Spilled. The previous rung was the fullest that fit.
            if best is None:
                best = BuildResult(
                    tex=tex, report=report, compile=out, attempts=attempts,
                    fit_note=(
                        f"Could not fit on {target_pages} page(s) even at the leanest "
                        "setting."
                    ),
                )
            break

        best = BuildResult(
            tex=tex, report=report, compile=out, attempts=attempts,
            fit_note=(
                f"{out.text_chars} characters on {out.pages} page(s)"
                + ("" if out.text_chars >= fill_target else " - still light")
            ),
        )
        if out.text_chars >= fill_target:
            break     # full enough; stop before risking a spill

    assert best is not None
    best.spec = spec

    chars = getattr(best.compile, "text_chars", 0)
    pages = getattr(best.compile, "pages", 0)
    best.short_of_target = bool(chars and chars < fill_target)
    if best.short_of_target and target_pages > 1:
        # Say it plainly rather than padding. A thin second page reads worse
        # than a full single page, and the playbook says so.
        filled = chars / float(legacy.MIN_FILL_CHARS)
        best.fit_note = (
            f"Your real material fills about {filled:.1f} pages. I did not pad it out "
            f"to {target_pages} -- a thin page reads worse than a full one."
        )

    best.guards = guards.run_all(best.tex, jd_text=job.jd_text)
    best.report = best.report or {}
    best.report["fit"] = {
        "attempts": attempts,
        "note": best.fit_note,
        "chars": chars,
        "pages": pages,
        "pages_target": target_pages,
        "target_chars": fill_target,
        "short_of_target": best.short_of_target,
    }
    best.report["spec"] = spec.as_dict()
    return best


async def build_and_save(
    job: JobPosting,
    *,
    jd: JDAnalysis | None = None,
    track: TrackId | None = None,
    exclude_projects: set[str] | None = None,
    spec: Any = None,
    research_md: str = "",
    study_plan_md: str = "",
) -> BuildResult:
    """Build, then promote into output/<folder>/ and record it in the tracker."""
    folder = workspace_sync.folder_name(job.company)
    # A brand-new folder still inherits the GLOBAL rules -- "always two pages"
    # has to apply to the very first build for a new company, not just later
    # rebuilds. effective() gives exactly that for an unknown folder.
    if spec is None:
        spec = resume_spec.effective(folder)
    res = await build(
        job, jd=jd, track=track, exclude_projects=exclude_projects,
        spec=spec, resume_id=folder,
    )
    res.folder = folder

    pdf_bytes = None
    if res.compile is not None and getattr(res.compile, "pdf_path", None):
        try:
            pdf_bytes = open(res.compile.pdf_path, "rb").read()
        except OSError:
            pdf_bytes = None

    workspace_sync.write_application(
        folder,
        tex=res.tex,
        jd_text=job.jd_text,
        research=research_md,
        study_plan=study_plan_md,
        audit=_audit_md(res),
        pdf_bytes=pdf_bytes,
    )

    workspace_sync.add_application(
        company=job.company,
        role=job.role_title,
        url=job.url,
        folder=folder,
        track=(res.report or {}).get("track", ""),
        notes=(res.report or {}).get("track_reason", ""),
    )
    workspace_sync.sync_applied_companies()

    # Record how it was shaped, and the sha of what was rendered, so a later
    # hand edit in the LaTeX drawer is detectable and a recompose can refuse
    # rather than silently discarding her work.
    resume_spec.save(
        folder, res.spec if res.spec is not None else spec,
        rendered_sha=tectonic.sha_of(res.tex), ship_sha="",
    )
    return res


def _audit_md(res: BuildResult) -> str:
    """A plain-language record of what was chosen and why."""
    rep = res.report or {}
    fit = rep.get("fit", {})
    lines = [
        "# How this resume was built",
        "",
        f"- **Track:** {rep.get('track', '?')} — {rep.get('track_reason', '')}",
        f"- **Signature project:** {rep.get('signature_project', '—')}",
        f"- **Page fit:** {fit.get('chars', 0)} characters on {fit.get('pages', '?')} page(s), "
        f"after {fit.get('attempts', 0)} attempt(s)",
        "",
        "## What went on the page",
        "",
        "| Slot | Chosen | Why |",
        "|---|---|---|",
    ]
    for r in rep.get("roles", []):
        lines.append(
            f"| Experience | {r['employer']} — {r['title']} | "
            f"relevance {r['relevance']}, using the {r['framing']} |"
        )
    for p in rep.get("projects", []):
        tag = "**signature**" if p.get("signature") else "supporting"
        lines.append(f"| Project ({tag}) | {p['id']} {p['name']} | relevance {p['relevance']} |")

    lines += ["", "## Honesty checks", ""]
    if res.guards is not None:
        rows = res.guards.as_dict()
        lines.append(f"- Blocking problems: **{rows['blocker_count']}**")
        lines.append(f"- Total notes: {rows['violation_count']}")
        for v in rows["violations"][:12]:
            lines.append(f"  - `{v['kind']}` {v['message']}")
    lines += [
        "",
        "Every bullet above is copied word for word from your context files. "
        "Nothing was rewritten, so nothing could be invented.",
        "",
    ]
    return "\n".join(lines)
