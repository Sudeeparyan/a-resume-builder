
"""
One turn of the resume conversation.

She types plain English; this returns a changed resume or an honest refusal.
The model is only ever asked to CHOOSE, never to write, so the walls between a
chat message and a false claim on the page are structural rather than
instructed:

  1. the schema enums are rebuilt from her live files, so an unheld skill is
     not a value the model can emit
  2. edit_ops.validate re-checks every id and keyword in Python, because those
     enums are only advisory once structured output degrades to parsing
  3. the composer copies bullets through verbatim and latex_render escapes them
  4. guards.run_all runs before the save, and a blocker means nothing is written

A turn that fails any of those returns the reason instead of a resume.
"""

from __future__ import annotations

from typing import Any

from .. import db, paths
from ..llm import registry
from ..llm.provider import Message, ProviderUnavailable, QuotaExhausted
from ..models import JDAnalysis, JobPosting
from ..services import (
    context_loader, factbank, guards, resume_rules, resume_spec,
    tectonic, workspace_sync,
)
from . import builder, edit_ops, prompts

HISTORY_TURNS = 12


# --------------------------------------------------------------------------
# transcript
# --------------------------------------------------------------------------
def history(folder: str, limit: int = 200) -> list[dict[str, Any]]:
    rows = db.connect().execute(
        "SELECT * FROM resume_chat WHERE folder = ? ORDER BY seq DESC LIMIT ?",
        (folder, limit),
    ).fetchall()
    out = [{
        "id": r["id"], "seq": r["seq"], "role": r["role"], "content": r["content"],
        "plan": db.loads(r["plan_json"], []), "refusals": db.loads(r["refusals_json"], []),
        "can_undo": bool(r["tex_before"]), "at": r["at"],
    } for r in rows]
    out.reverse()
    return out


def _messages(folder: str) -> list[Message]:
    rows = history(folder)[-HISTORY_TURNS:]
    return [
        Message(role=("user" if r["role"] == "user" else "assistant"), content=r["content"])
        for r in rows if r["content"].strip()
    ]


def _next_seq(folder: str) -> int:
    r = db.connect().execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM resume_chat WHERE folder = ?", (folder,)
    ).fetchone()
    return int(r[0])


def append(
    folder: str, role: str, content: str, *,
    plan: list | None = None, refusals: list | None = None,
    tex_before: str = "", cost_usd: float = 0.0,
) -> int:
    seq = _next_seq(folder)
    cur = db.connect().execute(
        "INSERT INTO resume_chat (folder, seq, role, content, plan_json,"
        " refusals_json, tex_before, tex_sha, cost_usd, at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (folder, seq, role, content, db.dumps(plan or []), db.dumps(refusals or []),
         tex_before, tectonic.sha_of(tex_before) if tex_before else "",
         cost_usd, db.now()),
    )
    return cur.lastrowid


def clear(folder: str) -> None:
    db.connect().execute("DELETE FROM resume_chat WHERE folder = ?", (folder,))


def undo(folder: str, turn_id: int) -> str:
    """Restore the file as it was before one turn. Returns the restored tex."""
    r = db.connect().execute(
        "SELECT tex_before FROM resume_chat WHERE id = ? AND folder = ?",
        (turn_id, folder),
    ).fetchone()
    if not r or not r["tex_before"]:
        raise ValueError("There is nothing to undo for that message.")
    return r["tex_before"]


# --------------------------------------------------------------------------
# context for a turn
# --------------------------------------------------------------------------
def _job_for(folder: str, jd_text: str) -> JobPosting:
    row = db.connect().execute(
        "SELECT j.* FROM resumes r JOIN jobs j ON j.id = r.job_id WHERE r.folder = ?",
        (folder,),
    ).fetchone()
    if row:
        return JobPosting(
            source=row["source"], source_id=row["source_id"], company=row["company"],
            role_title=row["role_title"], url=row["url"] or "",
            location=row["location"] or "", jd_text=row["jd_text"] or jd_text,
        )
    # A folder /hunt created has no jobs row. Rebuild enough of one from disk.
    meta = next((r for r in workspace_sync.list_applications() if r["folder"] == folder), {})
    return JobPosting(
        source="workspace", source_id=folder,
        company=meta.get("company") or folder, role_title=meta.get("role_title") or "",
        url=meta.get("url") or "", jd_text=jd_text,
    )


def _study_terms(study_plan: str, fb: Any) -> set[str]:
    """Terms the study plan names that she cannot claim yet."""
    return {t for t in guards.study_plan_terms(study_plan) if not fb.claimable(t)}


def build_context(folder: str) -> dict[str, Any]:
    base = paths.OUTPUT / folder
    tex = paths.read_text(base / "resume.tex")
    if not tex.strip():
        raise ValueError("No resume in that folder.")

    jd = paths.read_text(base / "job-description.txt")
    study = paths.read_text(base / "study-plan.md")
    fb = context_loader.load()
    roles, projects = factbank.load()
    spec = resume_spec.effective(folder)
    rules = resume_rules.effective(folder)

    cat = edit_ops.catalogue(
        fb=fb, roles=roles, projects=projects, tex=tex, rules=rules, spec=spec,
        study_terms=_study_terms(study, fb),
    )
    return {
        "tex": tex, "jd": jd, "study": study, "fb": fb, "spec": spec,
        "rules": rules, "catalogue": cat, "base": base,
        "job": _job_for(folder, jd),
    }


# --------------------------------------------------------------------------
# the turn
# --------------------------------------------------------------------------
async def turn(folder: str, message: str, *, confirm_rebuild: bool = False) -> dict[str, Any]:
    ctx = build_context(folder)
    tex, fb, spec, cat = ctx["tex"], ctx["fb"], ctx["spec"], ctx["catalogue"]

    provider = await registry.resolve()
    schema = edit_ops.plan_schema(cat)
    notes = resume_rules.notes(folder)

    payload = prompts.edit_payload(
        message, cat, spec, ctx["rules"], notes,
        jd_text=ctx["jd"], guards_summary=_guard_summary(tex, ctx),
    )

    try:
        res = await provider.complete_structured(
            system=prompts.RESUME_EDITOR,
            messages=_messages(folder) + [Message(role="user", content=payload)],
            schema=schema, tier="mid", effort="high",
            cache_prefix=prompts.fact_prefix(fb),     # her facts; byte-stable
            agent="resume_editor", max_tokens=4000,
        )
    except QuotaExhausted:
        raise
    except ProviderUnavailable as exc:
        raise ValueError(registry.skip_reason("resume_editor") or str(exc)) from None

    reply, ops, refusals, durable = edit_ops.validate(res.data, cat, fb)
    new_spec, spec_ops, tex_ops, meta_ops = edit_ops.split(spec, ops)

    # Nothing actionable: answer and stop, without touching the file.
    if not spec_ops and not tex_ops and not meta_ops:
        turn_id = _record(folder, message, reply, ops, refusals, "", res.usage.cost_usd)
        return _response(
            folder, reply, ops, refusals, changed=False, saved=False,
            turn_id=turn_id, spec=spec, tex=tex, cost=res.usage.cost_usd,
        )

    # A recompose rebuilds from context/ and would discard anything she typed in
    # the LaTeX drawer. Detect that and offer, rather than silently losing it.
    rendered_sha, _ship = resume_spec.shas(folder)
    hand_edited = bool(rendered_sha) and rendered_sha != tectonic.sha_of(tex)
    wants_rebuild = bool(spec_ops) and any(o.applied for o in spec_ops)
    if wants_rebuild and hand_edited and not confirm_rebuild:
        refusals.append(edit_ops.Refusal(
            request=message,
            reason=(
                "Rebuilding from your context files would lose the edits you made by "
                "hand in the LaTeX editor."
            ),
            what_would_make_it_true='Say "rebuild anyway" and I will do it.',
        ))
        turn_id = _record(folder, message, reply, ops, refusals, "", res.usage.cost_usd)
        return _response(
            folder, reply, ops, refusals, changed=False, saved=False,
            turn_id=turn_id, spec=spec, tex=tex, cost=res.usage.cost_usd,
        )

    new_tex = tex
    if wants_rebuild:
        jd_obj = _jd_for(folder)
        built = await builder.build(
            ctx["job"], jd=jd_obj, spec=new_spec, resume_id=f"{folder}-chat",
        )
        new_tex = built.tex or tex
        if built.short_of_target and new_spec.pages_target > 1:
            refusals.append(edit_ops.Refusal(
                request="make it longer",
                reason=(built.report or {}).get("fit", {}).get("note", "")
                or "There is not enough real material to fill that many pages.",
                what_would_make_it_true=(
                    "Add more experience or projects in the Profile tab, and ask again."
                ),
            ))

    if tex_ops:
        new_tex, tex_refusals = edit_ops.apply_tex_ops(new_tex, tex_ops, fb)
        refusals += tex_refusals

    # The last wall. A bug in any earlier one stops here.
    report = guards.run_all(new_tex, jd_text=ctx["jd"], study_plan=ctx["study"], fb=fb)
    if report.blockers:
        refusals.append(edit_ops.Refusal(
            request=message,
            reason=(
                "I did not save that: it would have put a claim on the page that your "
                "context files do not support."
            ),
        ))
        turn_id = _record(folder, message, reply, ops, refusals, "", res.usage.cost_usd)
        out = _response(folder, reply, ops, refusals, changed=False, saved=False,
                        turn_id=turn_id, spec=spec, tex=tex, cost=res.usage.cost_usd)
        out["guards"] = report.as_dict()
        return out

    compiled = await tectonic.compile_tex(
        new_tex, mode="draft", resume_id=f"{folder}-chat",
        want_pages=new_spec.pages_target, allow_fewer=new_spec.pages_target > 1,
        return_pdf=True,
    )
    if not compiled.ok:
        refusals.append(edit_ops.Refusal(
            request=message,
            reason="That change did not produce a valid PDF, so I left the resume alone.",
        ))
        turn_id = _record(folder, message, reply, ops, refusals, "", res.usage.cost_usd)
        return _response(folder, reply, ops, refusals, changed=False, saved=False,
                         turn_id=turn_id, spec=spec, tex=tex, cost=res.usage.cost_usd)

    # --- commit ---------------------------------------------------------
    workspace_sync.atomic_write(ctx["base"] / "resume.tex", new_tex)
    resume_spec.save(
        folder, new_spec,
        rendered_sha=tectonic.sha_of(new_tex) if wants_rebuild else rendered_sha,
        ship_sha="",                       # any write re-locks the download
    )

    added = _apply_meta(folder, meta_ops, message, durable, spec_ops)
    _write_rules_mirror(folder)

    turn_id = _record(folder, message, reply, ops, refusals, tex, res.usage.cost_usd)
    db.connect().execute(
        "UPDATE resumes SET pages = ?, status = 'DRAFT', updated_at = ? WHERE folder = ?",
        (compiled.pages, db.now(), folder),
    )

    out = _response(folder, reply, ops, refusals, changed=True, saved=True,
                    turn_id=turn_id, spec=new_spec, tex=new_tex, cost=res.usage.cost_usd)
    out.update({
        "ok": compiled.ok, "pages": compiled.pages, "text_chars": compiled.text_chars,
        "underfilled": compiled.underfilled, "pdf_b64": compiled.pdf_b64,
        "problems": compiled.problems, "guards": report.as_dict(),
        "rules_added": added,
    })
    return out


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _jd_for(folder: str) -> JDAnalysis | None:
    row = db.connect().execute(
        "SELECT a.jd_json FROM resumes r JOIN job_analysis a ON a.job_id = r.job_id"
        " WHERE r.folder = ?", (folder,),
    ).fetchone()
    data = db.loads(row["jd_json"], {}) if row else {}
    return JDAnalysis(**data) if data.get("must_haves") else None


def _guard_summary(tex: str, ctx: dict[str, Any]) -> str:
    try:
        rep = guards.run_all(tex, jd_text=ctx["jd"], study_plan=ctx["study"], fb=ctx["fb"])
        d = rep.as_dict()
        if not d["violation_count"]:
            return "nothing outstanding"
        return f"{d['blocker_count']} blocking, {d['violation_count']} note(s)"
    except Exception:  # noqa: BLE001
        return ""


def _apply_meta(
    folder: str, meta_ops: list, message: str, durable: bool, spec_ops: list,
) -> list[dict[str, Any]]:
    added: list[dict[str, Any]] = []
    for op in meta_ops:
        if op.op == "add_rule":
            r = resume_rules.add(
                text=str(op.args.get("text") or message)[:300],
                op=str(op.args.get("rule_op") or ""),
                args=op.args.get("rule_args") or {},
                scope=str(op.args.get("scope") or "folder"),
                folder=folder, source="chat",
            )
            op.applied = True
            added.append(r.as_dict())
        elif op.op == "remove_rule":
            try:
                resume_rules.delete(int(op.args["rule_id"]))
                op.applied = True
            except (KeyError, TypeError, ValueError):
                op.applied = False

    # "always two pages" -- she said always, but the model only sent the op.
    if durable and not added:
        for op in spec_ops:
            if op.applied:
                r = resume_rules.add(
                    text=message[:300], op=op.op, args=op.args,
                    scope="folder", folder=folder, source="chat",
                )
                added.append(r.as_dict())
                break
    return added


def _write_rules_mirror(folder: str) -> None:
    """A copy on disk, so a Claude Code session sees the same constraints."""
    try:
        lines = ["# Rules for this resume", "",
                 "<!-- GENERATED from the Rules box. Edit it there, not here. -->", ""]
        for r in resume_rules.effective(folder):
            kind = "enforced" if r.mechanical else "guidance"
            scope = "everywhere" if r.scope == "global" else "this resume"
            lines.append(f"- {r.text}  _({kind}, {scope})_")
        if len(lines) == 4:
            lines.append("_No rules set._")
        workspace_sync.atomic_write(
            paths.OUTPUT / folder / "rules.md", "\n".join(lines) + "\n"
        )
    except Exception:  # noqa: BLE001 -- the mirror is a convenience
        pass


def _record(
    folder: str, message: str, reply: str, ops: list, refusals: list,
    tex_before: str, cost: float,
) -> int:
    append(folder, "user", message)
    return append(
        folder, "assistant", reply,
        plan=[o.as_dict() for o in ops],
        refusals=[r.as_dict() for r in refusals],
        tex_before=tex_before, cost_usd=cost,
    )


def _response(
    folder: str, reply: str, ops: list, refusals: list, *,
    changed: bool, saved: bool, turn_id: int, spec: Any, tex: str, cost: float,
) -> dict[str, Any]:
    return {
        "reply": reply or ("Done." if changed else "I did not change anything."),
        "plan": [o.as_dict() for o in ops],
        "refusals": [r.as_dict() for r in refusals],
        "changed": changed,
        "saved": saved,
        "ship_ok_reset": changed,
        "turn_id": turn_id,
        "spec": spec.as_dict(),
        "pages_target": spec.pages_target,
        "tex": tex,
        "rules": [r.as_dict() for r in resume_rules.effective(folder)],
        "cost_usd": round(cost, 4),
    }
