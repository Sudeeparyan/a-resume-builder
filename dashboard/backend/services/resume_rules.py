"""
The Rules box: durable instructions re-applied on every rebuild.

A rule is either MECHANICAL or ADVISORY, and the difference is visible in the
UI because pretending otherwise would mislead her:

  op != ''   mechanical -- folded into the composer Selection on every rebuild,
                           so it genuinely cannot be forgotten.
  op == ''   advisory   -- passed to the editor agent as guidance. It shapes
                           what the agent proposes; it does not enforce itself.

Scope is 'folder' (this resume) or 'global' (every resume, now and future).
Global rules are applied first so a folder rule can refine them, and both are
applied AFTER the stored spec so a rule always wins over a one-off change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .. import db


@dataclass
class Rule:
    id: int
    scope: str = "folder"
    folder: str = ""
    text: str = ""
    op: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    position: int = 0
    source: str = "chat"
    created_at: str = ""
    stale: bool = False          # its target no longer exists in context/

    @property
    def mechanical(self) -> bool:
        return bool(self.op)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "scope": self.scope, "folder": self.folder,
            "text": self.text, "op": self.op, "args": self.args,
            "enabled": self.enabled, "position": self.position,
            "source": self.source, "created_at": self.created_at,
            "mechanical": self.mechanical, "stale": self.stale,
        }


def _row(r) -> Rule:
    return Rule(
        id=r["id"], scope=r["scope"], folder=r["folder"], text=r["text"],
        op=r["op"] or "", args=db.loads(r["args_json"], {}) or {},
        enabled=bool(r["enabled"]), position=r["position"],
        source=r["source"], created_at=r["created_at"],
    )


def add(
    *, text: str, op: str = "", args: dict[str, Any] | None = None,
    scope: str = "folder", folder: str = "", source: str = "chat",
) -> Rule:
    scope = "global" if scope == "global" else "folder"
    if scope == "global":
        folder = ""
    text = (text or "").strip()
    if not text:
        raise ValueError("A rule needs some words.")

    c = db.connect()
    nxt = c.execute(
        "SELECT COALESCE(MAX(position), 0) + 1 FROM resume_rules WHERE scope = ? AND folder = ?",
        (scope, folder),
    ).fetchone()[0]
    cur = c.execute(
        "INSERT INTO resume_rules (scope, folder, text, op, args_json, enabled, "
        "position, source, created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
        (scope, folder, text, op, db.dumps(args or {}), nxt, source, db.now()),
    )
    return get(cur.lastrowid)


def get(rule_id: int) -> Rule:
    r = db.connect().execute("SELECT * FROM resume_rules WHERE id = ?", (rule_id,)).fetchone()
    if r is None:
        raise KeyError(f"No rule {rule_id}.")
    return _row(r)


def update(rule_id: int, **fields: Any) -> Rule:
    allowed = {"text", "enabled", "position", "op", "args"}
    sets, vals = [], []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "args":
            sets.append("args_json = ?")
            vals.append(db.dumps(v))
        elif k == "enabled":
            sets.append("enabled = ?")
            vals.append(1 if v else 0)
        else:
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        vals.append(rule_id)
        db.connect().execute(
            f"UPDATE resume_rules SET {', '.join(sets)} WHERE id = ?", vals
        )
    return get(rule_id)


def delete(rule_id: int) -> None:
    db.connect().execute("DELETE FROM resume_rules WHERE id = ?", (rule_id,))


def for_folder(folder: str) -> list[Rule]:
    rows = db.connect().execute(
        "SELECT * FROM resume_rules WHERE scope = 'folder' AND folder = ? "
        "ORDER BY position, id",
        (folder,),
    ).fetchall()
    return [_row(r) for r in rows]


def globals_() -> list[Rule]:
    rows = db.connect().execute(
        "SELECT * FROM resume_rules WHERE scope = 'global' ORDER BY position, id"
    ).fetchall()
    return [_row(r) for r in rows]


def effective(folder: str) -> list[Rule]:
    """
    Global rules first, then this folder's -- so a folder rule refines a global
    one rather than being overwritten by it. Disabled rules are dropped here, so
    no caller has to remember to check.
    """
    return [r for r in (globals_() + for_folder(folder)) if r.enabled]


def notes(folder: str) -> list[str]:
    """The advisory rules, as plain lines for the editor agent's prompt."""
    return [r.text for r in effective(folder) if not r.mechanical]


def clear_folder(folder: str) -> None:
    db.connect().execute("DELETE FROM resume_rules WHERE scope = 'folder' AND folder = ?", (folder,))
