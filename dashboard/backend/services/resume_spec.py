"""
How one resume is shaped, and the ladder that fills its page.

A Spec is a page target plus a composer Selection. It is the single place the
Rules box, the chat agent and the fit loop meet: routes load the stored spec,
the rules are folded on top, and the result drives both composition and the
page-count check.

Rules are applied LAST and therefore win. That is what "applies to every
rebuild" has to mean mechanically -- otherwise a one-off "just this once make it
one page" would quietly outlive the standing instruction that says otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as _dc_replace
from typing import Any

from .. import db, legacy
from ..models import TrackId
from ..agents.composer import Selection
from . import resume_rules

DENSITIES = ("lean", "balanced", "full")

# Each rung shows MORE of her real experience. Growing means adding more real
# bullets from context/, never padding.
_LADDER_1: list[dict[str, int]] = [
    {"max_roles": 3, "bullets_first_role": 3, "bullets_other_role": 2,
     "max_projects": 2, "bullets_signature": 3, "bullets_supporting": 2},
    {"max_roles": 3, "bullets_first_role": 3, "bullets_other_role": 2,
     "max_projects": 3, "bullets_signature": 3, "bullets_supporting": 2},
    {"max_roles": 4, "bullets_first_role": 3, "bullets_other_role": 2,
     "max_projects": 3, "bullets_signature": 3, "bullets_supporting": 2},
    {"max_roles": 4, "bullets_first_role": 4, "bullets_other_role": 2,
     "max_projects": 3, "bullets_signature": 3, "bullets_supporting": 2},
    {"max_roles": 4, "bullets_first_role": 4, "bullets_other_role": 3,
     "max_projects": 3, "bullets_signature": 4, "bullets_supporting": 2},
    {"max_roles": 4, "bullets_first_role": 4, "bullets_other_role": 3,
     "max_projects": 3, "bullets_signature": 4, "bullets_supporting": 3},
    {"max_roles": 5, "bullets_first_role": 5, "bullets_other_role": 3,
     "max_projects": 3, "bullets_signature": 4, "bullets_supporting": 3},
    {"max_roles": 5, "bullets_first_role": 5, "bullets_other_role": 4,
     "max_projects": 3, "bullets_signature": 5, "bullets_supporting": 3},
]

# A second page needs genuinely more material, not looser spacing. If her real
# history runs out before the ladder does, the honest answer is a refusal --
# builder reports the shortfall and the chat agent says so.
_LADDER_2_EXTRA: list[dict[str, int]] = [
    {"max_roles": 5, "bullets_first_role": 5, "bullets_other_role": 4,
     "max_projects": 4, "bullets_signature": 5, "bullets_supporting": 4},
    {"max_roles": 6, "bullets_first_role": 6, "bullets_other_role": 4,
     "max_projects": 4, "bullets_signature": 5, "bullets_supporting": 4},
    {"max_roles": 6, "bullets_first_role": 6, "bullets_other_role": 5,
     "max_projects": 5, "bullets_signature": 6, "bullets_supporting": 4},
    {"max_roles": 7, "bullets_first_role": 6, "bullets_other_role": 5,
     "max_projects": 5, "bullets_signature": 6, "bullets_supporting": 5},
]

_DENSITY_START = {"lean": 0, "balanced": 0, "full": 3}


@dataclass
class Spec:
    pages_target: int = 1
    density: str = "balanced"
    selection: Selection = field(default_factory=Selection)

    # ---- serialisation -------------------------------------------------
    def as_dict(self) -> dict[str, Any]:
        s = self.selection
        return {
            "pages_target": self.pages_target,
            "density": self.density,
            "track": s.track.value if s.track else None,
            "max_roles": s.max_roles,
            "bullets_first_role": s.bullets_first_role,
            "bullets_other_role": s.bullets_other_role,
            "max_projects": s.max_projects,
            "bullets_signature": s.bullets_signature,
            "bullets_supporting": s.bullets_supporting,
            "section_order": s.section_order,
            "show_coursework": s.show_coursework,
            "prefer_shorter_bullets": s.prefer_shorter_bullets,
            "include_projects": list(s.include_projects),
            "exclude_projects": sorted(s.exclude_projects),
            "signature_project": s.signature_project,
            "include_roles": list(s.include_roles),
            "exclude_roles": sorted(s.exclude_roles),
            "framing_preference": dict(s.framing_preference),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "Spec":
        d = d or {}
        track = None
        raw_track = d.get("track")
        if raw_track:
            try:
                track = TrackId(raw_track)
            except ValueError:
                track = None
        base = Selection()
        sel = Selection(
            track=track,
            max_roles=int(d.get("max_roles", base.max_roles)),
            bullets_first_role=int(d.get("bullets_first_role", base.bullets_first_role)),
            bullets_other_role=int(d.get("bullets_other_role", base.bullets_other_role)),
            max_projects=int(d.get("max_projects", base.max_projects)),
            bullets_signature=int(d.get("bullets_signature", base.bullets_signature)),
            bullets_supporting=int(d.get("bullets_supporting", base.bullets_supporting)),
            section_order=d.get("section_order") or None,
            show_coursework=bool(d.get("show_coursework", True)),
            prefer_shorter_bullets=bool(d.get("prefer_shorter_bullets", False)),
            include_projects=list(d.get("include_projects") or []),
            exclude_projects=set(d.get("exclude_projects") or []),
            signature_project=d.get("signature_project") or "",
            include_roles=list(d.get("include_roles") or []),
            exclude_roles=set(d.get("exclude_roles") or []),
            framing_preference=dict(d.get("framing_preference") or {}),
        )
        pages = int(d.get("pages_target") or 1)
        density = d.get("density") if d.get("density") in DENSITIES else "balanced"
        return cls(pages_target=max(1, min(2, pages)), density=density, selection=sel)

    def replace(self, **kw: Any) -> "Spec":
        return _dc_replace(self, **kw)

    def with_selection(self, **kw: Any) -> "Spec":
        return _dc_replace(self, selection=self.selection.replace(**kw))

    @property
    def min_fill_chars(self) -> int:
        """MIN_FILL_CHARS is a ONE-page number; a two-page target must scale it
        or the fit loop stops with a half-empty second page."""
        return legacy.MIN_FILL_CHARS * max(1, self.pages_target)


def fit_ladder(spec: Spec) -> list[Selection]:
    """The rungs to try, leanest first, as full Selections."""
    rungs = list(_LADDER_1)
    if spec.pages_target >= 2:
        rungs = rungs + _LADDER_2_EXTRA
    start = _DENSITY_START.get(spec.density, 0)
    rungs = rungs[start:] or rungs[-1:]
    return [
        spec.selection.replace(pages_target=spec.pages_target, **rung)
        for rung in rungs
    ]


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def load(folder: str) -> Spec:
    r = db.connect().execute(
        "SELECT spec_json, pages_target FROM resume_specs WHERE folder = ?", (folder,)
    ).fetchone()
    if r is None:
        return Spec()
    spec = Spec.from_dict(db.loads(r["spec_json"], {}))
    spec.pages_target = max(1, min(2, int(r["pages_target"] or 1)))
    return spec


def save(
    folder: str, spec: Spec, *,
    rendered_sha: str | None = None, ship_sha: str | None = None,
) -> None:
    c = db.connect()
    row = c.execute(
        "SELECT rendered_sha, ship_sha FROM resume_specs WHERE folder = ?", (folder,)
    ).fetchone()
    keep_rendered = row["rendered_sha"] if row else ""
    keep_ship = row["ship_sha"] if row else ""
    c.execute(
        "INSERT INTO resume_specs (folder, spec_json, pages_target, rendered_sha, "
        "ship_sha, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(folder) DO UPDATE SET spec_json = excluded.spec_json, "
        "pages_target = excluded.pages_target, rendered_sha = excluded.rendered_sha, "
        "ship_sha = excluded.ship_sha, updated_at = excluded.updated_at",
        (
            folder, db.dumps(spec.as_dict()), spec.pages_target,
            keep_rendered if rendered_sha is None else rendered_sha,
            keep_ship if ship_sha is None else ship_sha,
            db.now(),
        ),
    )


def shas(folder: str) -> tuple[str, str]:
    r = db.connect().execute(
        "SELECT rendered_sha, ship_sha FROM resume_specs WHERE folder = ?", (folder,)
    ).fetchone()
    return ((r["rendered_sha"] or ""), (r["ship_sha"] or "")) if r else ("", "")


def clear_ship(folder: str) -> None:
    """Any write to the file invalidates the Download gate. Called from every
    write path, so an AI edit can never inherit an earlier ship approval."""
    db.connect().execute(
        "UPDATE resume_specs SET ship_sha = '', updated_at = ? WHERE folder = ?",
        (db.now(), folder),
    )


def set_ship(folder: str, tex_sha: str) -> None:
    db.connect().execute(
        "UPDATE resume_specs SET ship_sha = ?, updated_at = ? WHERE folder = ?",
        (tex_sha, db.now(), folder),
    )


# --------------------------------------------------------------------------
# rules -> spec
# --------------------------------------------------------------------------
def apply_rule(spec: Spec, rule: Any) -> Spec:
    """Fold one mechanical rule into the spec. Advisory rules pass through."""
    if not getattr(rule, "mechanical", False):
        return spec
    from ..agents import edit_ops
    return edit_ops.apply_spec_op(spec, rule.op, rule.args, strict=False)


def effective(folder: str) -> Spec:
    """Stored spec, then global rules, then folder rules. Rules win."""
    spec = load(folder)
    for r in resume_rules.effective(folder):
        try:
            spec = apply_rule(spec, r)
        except Exception:  # noqa: BLE001 -- a stale rule must never break a build
            continue
    return spec
