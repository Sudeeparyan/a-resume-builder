"""
The whitelist that lets a chat message change a resume without being able to lie.

The model NEVER writes LaTeX, and no operation here takes prose that reaches the
page. It chooses which of her existing blocks appear and in what order; the
composer copies bullet text verbatim from context/; latex_render escapes every
character and copies the preamble; guards run before the save. A fabricated
claim is not forbidden here, it is unrepresentable.

Two deliberate absences, because both are rewriting by another name:
  * no set_bullet_text / write_summary -- shortening a verbatim bullet IS
    rewriting it. "Shorter bullets" is served by set_bullet_budget,
    prefer_shorter_bullets and set_role_framing, which pick between lines she
    already wrote.
  * no add_project(name=...) -- a project that is not in 04-projects.md does not
    exist, in any tense.

The enums in plan_schema() are rebuilt from the live workspace on every request.
That is what makes "add Kubernetes" impossible rather than merely refused: the
value is not in the schema, and validate() re-checks it in Python anyway because
the enum is only advisory on the prompt-and-parse path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import TrackId
from ..services import latex_render

# op -> which layer it acts on
SPEC_OPS = {
    "set_pages", "set_density", "set_bullet_budget", "set_entry_counts",
    "prefer_shorter_bullets", "set_section_order", "set_track",
    "include_project", "exclude_project", "set_signature_project",
    "include_role", "exclude_role", "set_role_framing", "show_coursework",
}
TEX_OPS = {"remove_block", "add_skill_keyword"}
META_OPS = {"add_rule", "remove_rule"}
ALL_OPS = SPEC_OPS | TEX_OPS | META_OPS

BULLET_SLOTS = ("first_role", "other_roles", "signature_project", "other_projects")
_SLOT_FIELD = {
    "first_role": "bullets_first_role",
    "other_roles": "bullets_other_role",
    "signature_project": "bullets_signature",
    "other_projects": "bullets_supporting",
}


@dataclass
class Op:
    """One validated operation, plus the human label the UI shows."""
    op: str
    args: dict[str, Any] = field(default_factory=dict)
    why: str = ""
    label: str = ""
    applied: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "op": self.op, "args": self.args, "why": self.why,
            "label": self.label, "applied": self.applied,
        }


@dataclass
class Refusal:
    request: str
    reason: str
    what_would_make_it_true: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request, "reason": self.reason,
            "what_would_make_it_true": self.what_would_make_it_true,
        }


class OpError(ValueError):
    """A rejected operation. Its message is shown to her verbatim."""


def _int_arg(args: dict[str, Any], key: str, lo: int, hi: int) -> int:
    try:
        n = int(args.get(key))
    except (TypeError, ValueError):
        raise OpError(f"{key} needs to be a whole number.") from None
    if not (lo <= n <= hi):
        raise OpError(f"{key} has to be between {lo} and {hi}.")
    return n


# --------------------------------------------------------------------------
# spec layer
# --------------------------------------------------------------------------
def apply_spec_op(spec: Any, op: str, args: dict[str, Any], *, strict: bool = True) -> Any:
    """
    Fold one spec operation into a Spec, returning a new one.

    strict=False is used when replaying a stored rule: a rule whose target has
    since been renamed in context/ must not break the build, it must simply stop
    matching (and be surfaced as stale elsewhere).
    """
    args = args or {}
    try:
        if op == "set_pages":
            return spec.replace(pages_target=_int_arg(args, "pages", 1, 2))

        if op == "set_density":
            d = str(args.get("level") or "balanced")
            if d not in ("lean", "balanced", "full"):
                raise OpError("Density has to be lean, balanced or full.")
            return spec.replace(density=d)

        if op == "set_bullet_budget":
            slot = str(args.get("slot") or "")
            if slot not in BULLET_SLOTS:
                raise OpError(f"There is no bullet slot called {slot!r}.")
            return spec.with_selection(**{_SLOT_FIELD[slot]: _int_arg(args, "count", 1, 6)})

        if op == "set_entry_counts":
            kw: dict[str, Any] = {}
            if "roles" in args:
                kw["max_roles"] = _int_arg(args, "roles", 1, 7)
            if "projects" in args:
                kw["max_projects"] = _int_arg(args, "projects", 1, 5)
            if not kw:
                raise OpError("Say how many roles or projects to show.")
            return spec.with_selection(**kw)

        if op == "prefer_shorter_bullets":
            return spec.with_selection(prefer_shorter_bullets=bool(args.get("on", True)))

        if op == "show_coursework":
            return spec.with_selection(show_coursework=bool(args.get("on", True)))

        if op == "set_section_order":
            order = list(args.get("order") or [])
            if sorted(order) != ["experience", "projects"]:
                raise OpError(
                    "Section order has to list both experience and projects, once each."
                )
            return spec.with_selection(section_order=order)

        if op == "set_track":
            raw = str(args.get("track") or "")
            try:
                track = TrackId(raw)
            except ValueError:
                raise OpError(f"There is no track called {raw!r}.") from None
            return spec.with_selection(track=track)

        if op == "include_project":
            pid = str(args.get("project_id") or "").strip()
            sel = spec.selection
            keep = [p for p in sel.include_projects if p != pid] + [pid]
            return spec.with_selection(
                include_projects=keep,
                exclude_projects={p for p in sel.exclude_projects if p != pid},
            )

        if op == "exclude_project":
            pid = str(args.get("project_id") or "").strip()
            sel = spec.selection
            return spec.with_selection(
                exclude_projects=set(sel.exclude_projects) | {pid},
                include_projects=[p for p in sel.include_projects if p != pid],
                signature_project=("" if sel.signature_project == pid else sel.signature_project),
            )

        if op == "set_signature_project":
            pid = str(args.get("project_id") or "").strip()
            sel = spec.selection
            return spec.with_selection(
                signature_project=pid,
                exclude_projects={p for p in sel.exclude_projects if p != pid},
            )

        if op == "include_role":
            emp = str(args.get("employer") or "").strip()
            sel = spec.selection
            keep = [e for e in sel.include_roles if e != emp] + [emp]
            return spec.with_selection(
                include_roles=keep,
                exclude_roles={e for e in sel.exclude_roles if e != emp},
            )

        if op == "exclude_role":
            emp = str(args.get("employer") or "").strip()
            sel = spec.selection
            return spec.with_selection(
                exclude_roles=set(sel.exclude_roles) | {emp},
                include_roles=[e for e in sel.include_roles if e != emp],
            )

        if op == "set_role_framing":
            emp = str(args.get("employer") or "").strip()
            fr = str(args.get("framing") or "").strip()
            if not emp or not fr:
                raise OpError("Naming a framing needs both an employer and a framing.")
            pref = dict(spec.selection.framing_preference)
            pref[emp] = fr
            return spec.with_selection(framing_preference=pref)

    except OpError:
        if strict:
            raise
        return spec

    if strict:
        raise OpError(f"{op} is not something I can do to a resume.")
    return spec


# --------------------------------------------------------------------------
# the catalogue: what is actually available, rebuilt every request
# --------------------------------------------------------------------------
def catalogue(
    *, fb: Any, roles: list, projects: list, tex: str, rules: list,
    spec: Any, study_terms: set[str] | None = None,
) -> dict[str, Any]:
    """
    Every legal value for every argument, read from the live workspace.

    This goes in the USER message, never in the cached prefix: it changes
    whenever she edits context/, and putting it behind the cache breakpoint
    would invalidate the prompt cache on every call with no visible symptom.
    """
    # rank_projects skips coursework projects, so pinning one would silently do
    # nothing. Keep them out of the enum and name them in the refusal instead.
    usable = [p for p in projects if not p.coursework and p.bullets]
    coursework = [p for p in projects if p.coursework]

    framings: dict[str, list[str]] = {}
    for r in roles:
        names = [f.name for f in r.framings if f.reusable and f.bullets]
        if names:
            framings[r.employer] = names

    claimable = sorted(
        {s for s in (set(fb.skills_strong) | set(fb.skills_used)) if s}
    )

    return {
        "projects": [
            {"id": p.pid, "name": p.name, "stack": p.stack} for p in usable
        ],
        "project_ids": [p.pid for p in usable],
        "coursework_project_ids": [p.pid for p in coursework],
        "employers": list(framings.keys()),
        "framings": framings,
        "skills": claimable,
        "gaps": sorted({s for s in fb.skills_gap if s}),
        "touched": sorted({s for s in fb.skills_touched if s}),
        "block_ids": sorted(latex_render.anchors(tex).keys()),
        "rule_ids": [r.id for r in rules],
        "study_terms": sorted(study_terms or set()),
        "current": {
            "pages_target": spec.pages_target,
            "density": spec.density,
            "section_order": spec.selection.section_order,
            "track": spec.selection.track.value if spec.selection.track else None,
            "signature_project": spec.selection.signature_project,
            "max_roles": spec.selection.max_roles,
            "max_projects": spec.selection.max_projects,
        },
    }


def _obj(op_name: str, props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    p = {"op": {"const": op_name}, "why": {"type": "string"}}
    p.update(props)
    return {
        "type": "object", "additionalProperties": False,
        "required": ["op"] + required, "properties": p,
    }


def plan_schema(cat: dict[str, Any]) -> dict[str, Any]:
    """
    The edit-plan schema, with every enum populated from the catalogue.

    An empty enum is invalid JSON Schema, so an op with nothing to offer is
    dropped from the union entirely -- which is the correct behaviour anyway:
    if she has no claimable skill missing from the page, add_skill_keyword is
    not an available move.
    """
    variants: list[dict[str, Any]] = [
        _obj("set_pages", {"pages": {"enum": [1, 2]}}, ["pages"]),
        _obj("set_density", {"level": {"enum": ["lean", "balanced", "full"]}}, ["level"]),
        _obj("set_bullet_budget", {
            "slot": {"enum": list(BULLET_SLOTS)},
            "count": {"type": "integer", "minimum": 1, "maximum": 6},
        }, ["slot", "count"]),
        _obj("set_entry_counts", {
            "roles": {"type": "integer", "minimum": 1, "maximum": 7},
            "projects": {"type": "integer", "minimum": 1, "maximum": 5},
        }, []),
        _obj("prefer_shorter_bullets", {"on": {"type": "boolean"}}, ["on"]),
        _obj("show_coursework", {"on": {"type": "boolean"}}, ["on"]),
        _obj("set_section_order", {
            "order": {
                "type": "array", "minItems": 2, "maxItems": 2,
                "items": {"enum": ["experience", "projects"]},
            },
        }, ["order"]),
        _obj("set_track", {
            "track": {"enum": [t.value for t in TrackId]},
        }, ["track"]),
    ]

    pids = cat.get("project_ids") or []
    if pids:
        variants += [
            _obj("include_project", {"project_id": {"enum": pids}}, ["project_id"]),
            _obj("exclude_project", {"project_id": {"enum": pids}}, ["project_id"]),
            _obj("set_signature_project", {"project_id": {"enum": pids}}, ["project_id"]),
        ]

    employers = cat.get("employers") or []
    if employers:
        variants += [
            _obj("include_role", {"employer": {"enum": employers}}, ["employer"]),
            _obj("exclude_role", {"employer": {"enum": employers}}, ["employer"]),
        ]
        all_framings = sorted({n for v in (cat.get("framings") or {}).values() for n in v})
        if all_framings:
            variants.append(_obj("set_role_framing", {
                "employer": {"enum": employers},
                "framing": {"enum": all_framings},
            }, ["employer", "framing"]))

    if cat.get("block_ids"):
        variants.append(_obj(
            "remove_block", {"block_id": {"enum": cat["block_ids"]}}, ["block_id"]
        ))

    # The honesty wall, expressed as a closed set of legal values.
    if cat.get("skills"):
        variants.append(_obj(
            "add_skill_keyword", {"keyword": {"enum": cat["skills"]}}, ["keyword"]
        ))

    variants.append(_obj("add_rule", {
        "text": {"type": "string",
                 "description": "Her instruction in her own words, as it will be shown."},
        "scope": {"enum": ["folder", "global"]},
        "rule_op": {"enum": sorted(SPEC_OPS | TEX_OPS)},
        "rule_args": {"type": "object"},
    }, ["text"]))
    if cat.get("rule_ids"):
        variants.append(_obj(
            "remove_rule", {"rule_id": {"enum": cat["rule_ids"]}}, ["rule_id"]
        ))

    return {
        "type": "object", "additionalProperties": False,
        "required": ["reply", "ops"],
        "properties": {
            "reply": {
                "type": "string",
                "description": (
                    "Two sentences to her, plain English. Say what changed, not how. "
                    "If you refused something, say so here too."
                ),
            },
            "ops": {"type": "array", "maxItems": 8, "items": {"oneOf": variants}},
            "refusals": {
                "type": "array", "maxItems": 4,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["request", "reason"],
                    "properties": {
                        "request": {"type": "string"},
                        "reason": {"type": "string"},
                        "what_would_make_it_true": {"type": "string"},
                    },
                },
            },
            "durable": {
                "type": "boolean",
                "description": (
                    "True when this should apply to every future rebuild of this "
                    "resume, not just now."
                ),
            },
        },
    }


# --------------------------------------------------------------------------
# validation: the enums are advisory, this is not
# --------------------------------------------------------------------------
def _label_for(op: str, args: dict[str, Any], cat: dict[str, Any]) -> str:
    names = {p["id"]: p["name"] for p in (cat.get("projects") or [])}
    pid = str(args.get("project_id") or "")
    if op in ("include_project", "exclude_project", "set_signature_project"):
        verb = {"include_project": "Add", "exclude_project": "Drop",
                "set_signature_project": "Lead with"}[op]
        return f"{verb} {pid} {names.get(pid, '')}".strip()
    if op == "set_pages":
        n = args.get("pages")
        return f"Make it {n} page" + ("" if n == 1 else "s")
    if op == "set_section_order":
        order = args.get("order") or []
        return "Lead with " + (order[0] if order else "?")
    if op in ("include_role", "exclude_role"):
        verb = "Show" if op == "include_role" else "Drop"
        return f"{verb} {args.get('employer', '')}"
    if op == "add_skill_keyword":
        return f"Add {args.get('keyword', '')} to Technical Skills"
    if op == "remove_block":
        return f"Remove the line {args.get('block_id', '')}"
    if op == "set_bullet_budget":
        slot = str(args.get("slot", "")).replace("_", " ")
        return f"{args.get('count')} bullets for {slot}"
    if op == "set_track":
        return f"Use the {args.get('track', '')} layout"
    if op == "add_rule":
        return f"Remember: {args.get('text', '')}"
    return op.replace("_", " ")


def _refuse_skill(term: str, fb: Any, cat: dict[str, Any]) -> Refusal:
    """
    Written here, in Python, so it can never over-promise.

    A model-authored refusal is free to soften this into "I could add it as
    familiar with", which is the exact hedge the honesty wall forbids.
    """
    if fb.forbidden(term):
        return Refusal(
            request=f"add {term}",
            reason=(
                f"I cannot put {term} on this resume. It is on your honest-gaps list "
                "in context/05-skills.md, which means it cannot appear in any form -- "
                "not even as a hedge like familiar with, or exposure to."
            ),
            what_would_make_it_true=(
                f"If you have genuinely used {term} since, move it to Used it in the "
                "Profile tab and ask me again."
            ),
        )
    if term.lower() in {t.lower() for t in (cat.get("study_terms") or [])}:
        return Refusal(
            request=f"add {term}",
            reason=(
                f"{term} is in this company's study plan, which means it is something "
                "to learn before the interview -- not something this page can claim yet."
            ),
            what_would_make_it_true=(
                "Learn it, record it in the Profile tab, and it becomes claimable."
            ),
        )
    if term.lower() in {t.lower() for t in (cat.get("touched") or [])}:
        return Refusal(
            request=f"add {term}",
            reason=(
                f"{term} is recorded as Touched it in context/05-skills.md. It may sit in "
                "the skills list, but it cannot carry a bullet and I will not promote it."
            ),
            what_would_make_it_true=(
                f"Move {term} up to Used it in the Profile tab, if that is true."
            ),
        )
    return Refusal(
        request=f"add {term}",
        reason=(
            f"{term} is not in your context files, so as far as this resume is concerned "
            "it does not exist. Nothing reaches the page that is not already recorded."
        ),
        what_would_make_it_true=f"Add {term} in the Profile tab first.",
    )


def validate(
    data: dict[str, Any] | None, cat: dict[str, Any], fb: Any,
) -> tuple[str, list[Op], list[Refusal], bool]:
    """
    Re-check everything the model returned. Nothing here is trusted.

    The schema enums already make most of this unrepresentable, but structured
    output degrades to prompt-and-parse whenever web search is on, and a parsed
    object is only as good as this function.
    """
    data = data or {}
    reply = str(data.get("reply") or "").strip()
    durable = bool(data.get("durable"))

    refusals: list[Refusal] = []
    for r in data.get("refusals") or []:
        if isinstance(r, dict) and r.get("reason"):
            refusals.append(Refusal(
                request=str(r.get("request") or ""),
                reason=str(r.get("reason") or ""),
                what_would_make_it_true=str(r.get("what_would_make_it_true") or ""),
            ))

    pids = set(cat.get("project_ids") or [])
    coursework = set(cat.get("coursework_project_ids") or [])
    employers = set(cat.get("employers") or [])
    blocks = set(cat.get("block_ids") or [])
    rule_ids = set(cat.get("rule_ids") or [])

    ops: list[Op] = []
    for raw in data.get("ops") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("op") or "")
        if name not in ALL_OPS:
            continue
        args = {k: v for k, v in raw.items() if k not in ("op", "why")}
        why = str(raw.get("why") or "")

        if name in ("include_project", "exclude_project", "set_signature_project"):
            pid = str(args.get("project_id") or "").strip()
            if pid in coursework:
                refusals.append(Refusal(
                    request=f"{name} {pid}",
                    reason=(
                        f"{pid} is marked coursework in context/04-projects.md, and "
                        "coursework never leads a resume as the signature project."
                    ),
                ))
                continue
            if pid not in pids:
                refusals.append(Refusal(
                    request=f"{name} {pid}",
                    reason=(
                        f"There is no project {pid} in context/04-projects.md. I can only "
                        "use projects already written down there."
                    ),
                    what_would_make_it_true="Add the project in the Profile tab first.",
                ))
                continue

        if name in ("include_role", "exclude_role", "set_role_framing"):
            emp = str(args.get("employer") or "").strip()
            if emp not in employers:
                refusals.append(Refusal(
                    request=f"{name} {emp}",
                    reason=f"{emp} is not one of the employers in context/03-experience.md.",
                ))
                continue
            if name == "set_role_framing":
                allowed = set((cat.get("framings") or {}).get(emp) or [])
                fr = str(args.get("framing") or "").strip()
                if fr not in allowed:
                    refusals.append(Refusal(
                        request=f"use the {fr} framing of {emp}",
                        reason=(
                            f"{emp} has no reusable framing by that name. Your context file "
                            "marks some framings as a historical record only, and those "
                            "cannot be put back onto a page."
                        ),
                    ))
                    continue

        if name == "remove_block" and str(args.get("block_id") or "") not in blocks:
            refusals.append(Refusal(
                request="remove a line",
                reason="That line is no longer in the file -- it may already be gone.",
            ))
            continue

        if name == "add_skill_keyword":
            term = str(args.get("keyword") or "").strip()
            study = {t.lower() for t in (cat.get("study_terms") or [])}
            if (not term or not fb.claimable(term) or fb.forbidden(term)
                    or term.lower() in study):
                refusals.append(_refuse_skill(term, fb, cat))
                continue

        if name == "remove_rule":
            try:
                rid = int(args.get("rule_id"))
            except (TypeError, ValueError):
                continue
            if rid not in rule_ids:
                continue
            args = {"rule_id": rid}

        ops.append(Op(op=name, args=args, why=why, label=_label_for(name, args, cat)))

    return reply, ops, refusals, durable


# --------------------------------------------------------------------------
# applying
# --------------------------------------------------------------------------
def split(spec: Any, ops: list[Op]) -> tuple[Any, list[Op], list[Op], list[Op]]:
    """
    Fold the spec ops into a new Spec; hand back the tex and meta ops untouched.

    Returns (new_spec, spec_ops, tex_ops, meta_ops). A spec op that fails
    validation here is dropped rather than aborting the turn, and its Op keeps
    applied=False so the UI can show it struck through.
    """
    new_spec = spec
    spec_ops: list[Op] = []
    tex_ops: list[Op] = []
    meta_ops: list[Op] = []

    for op in ops:
        if op.op in SPEC_OPS:
            try:
                new_spec = apply_spec_op(new_spec, op.op, op.args, strict=True)
                op.applied = True
            except OpError:
                op.applied = False
            spec_ops.append(op)
        elif op.op in TEX_OPS:
            tex_ops.append(op)
        else:
            meta_ops.append(op)

    return new_spec, spec_ops, tex_ops, meta_ops


def apply_tex_ops(tex: str, ops: list[Op], fb: Any) -> tuple[str, list[Refusal]]:
    """
    The surgical layer, shared with POST .../apply-suggestion so the honesty
    check for a keyword lives in exactly one place.
    """
    refusals: list[Refusal] = []
    out = tex
    for op in ops:
        try:
            if op.op == "remove_block":
                out = latex_render.remove_block(out, str(op.args.get("block_id")))
                op.applied = True
            elif op.op == "add_skill_keyword":
                term = str(op.args.get("keyword") or "").strip()
                # Checked in validate() too. Repeated here because this function
                # is also called from the non-chat suggestion route.
                if not fb.claimable(term) or fb.forbidden(term):
                    refusals.append(_refuse_skill(term, fb, {}))
                    continue
                out = latex_render.add_skill_keyword(out, term)
                op.applied = True
        except ValueError as exc:
            refusals.append(Refusal(request=op.label or op.op, reason=str(exc)))
    return out, refusals


def stale_rules(rules: list, cat: dict[str, Any]) -> list[int]:
    """
    Rule ids whose target no longer exists in context/.

    A renamed heading in 03-experience.md silently orphans a rule. Surfacing it
    is the difference between a rule that stopped working and a rule she thinks
    is still holding.
    """
    pids = set(cat.get("project_ids") or [])
    employers = set(cat.get("employers") or [])
    skills = {s.lower() for s in (cat.get("skills") or [])}
    out: list[int] = []
    for r in rules:
        if not getattr(r, "mechanical", False):
            continue
        a = r.args or {}
        if r.op in ("include_project", "exclude_project", "set_signature_project"):
            if str(a.get("project_id") or "") not in pids:
                out.append(r.id)
        elif r.op in ("include_role", "exclude_role", "set_role_framing"):
            if str(a.get("employer") or "") not in employers:
                out.append(r.id)
        elif r.op == "add_skill_keyword":
            if str(a.get("keyword") or "").lower() not in skills:
                out.append(r.id)
    return out
