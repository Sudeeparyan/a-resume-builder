"""Never apply twice: the rules that keep an already-seen company out of the lists.

- Same company + same role: never surfaced again, at any status (including removed
  and excluded rows).
- Company REJECTED: suppressed for `reject_cooldown_days` (180) for every role.
- APPLIED with no reply for `ghost_after_days` (21): flipped to GHOSTED; the company
  becomes eligible again after `ghost_cooldown_days` (90) for a *different* role only.

Numbers live in data/config/profile.yml under `reapply`. This module only reads the
jobs table the dashboard already keeps; it adds no store of its own.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

DEFAULTS = {"ghost_after_days": 21, "reject_cooldown_days": 180, "ghost_cooldown_days": 90}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").casefold())


def _day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def settings(profile: dict[str, Any] | None) -> dict[str, int]:
    raw = (profile or {}).get("reapply") or {}
    return {key: int(raw.get(key, default)) for key, default in DEFAULTS.items()}


def check(company: str, title: str, jobs: Iterable[dict[str, Any]], excluded: Iterable[dict[str, Any]] = (),
          profile: dict[str, Any] | None = None, today: date | None = None) -> dict[str, Any]:
    """Return {blocked, rule, note}. `jobs` should include removed rows (deleted_at set)."""
    rules = settings(profile)
    today = today or datetime.now(timezone.utc).date()
    company_key, title_key = normalize(company), normalize(title)
    notes: list[str] = []
    for row in list(jobs) + list(excluded):
        if normalize(row.get("company")) != company_key:
            continue
        same_role = normalize(row.get("title") or row.get("role")) == title_key
        status = str(row.get("status") or "").lower()
        changed = _day(row.get("updated_at")) or _day(row.get("created_at")) or _day(row.get("excluded_at"))
        if same_role and (status or row.get("excluded_at")):
            label = "excluded" if row.get("excluded_at") else status
            return {"blocked": True, "rule": "same_role", "note": f"Same company and role already {label} ({row.get('url') or row.get('id')})."}
        if status == "rejected" and changed and (today - changed).days < rules["reject_cooldown_days"]:
            left = rules["reject_cooldown_days"] - (today - changed).days
            return {"blocked": True, "rule": "rejected_180", "note": f"{company} rejected you {(today - changed).days} days ago; suppressed for {left} more days."}
        if status == "ghosted" and changed and (today - changed).days < rules["ghost_cooldown_days"]:
            left = rules["ghost_cooldown_days"] - (today - changed).days
            return {"blocked": True, "rule": "ghosted_90", "note": f"{company} went quiet {(today - changed).days} days ago; wait {left} more days before a different role."}
        if status == "ghosted":
            notes.append(f"{company} ghosted an earlier application; a different role is allowed.")
    return {"blocked": False, "rule": None, "note": " ".join(notes)}


def due_for_ghosting(jobs: Iterable[dict[str, Any]], profile: dict[str, Any] | None = None,
                     today: date | None = None) -> list[dict[str, Any]]:
    """Applied rows with no status change for `ghost_after_days`. The caller flips them."""
    rules = settings(profile)
    today = today or datetime.now(timezone.utc).date()
    due = []
    for row in jobs:
        if str(row.get("status") or "").lower() != "applied" or row.get("deleted_at"):
            continue
        anchor = _day(row.get("application_date")) or _day(row.get("updated_at"))
        if anchor and (today - anchor).days >= rules["ghost_after_days"]:
            due.append({**row, "quiet_days": (today - anchor).days})
    return due


def quiet_days(row: dict[str, Any], today: date | None = None) -> int | None:
    """How long an open application has waited, for the Pipeline view."""
    today = today or datetime.now(timezone.utc).date()
    anchor = _day(row.get("application_date")) or _day(row.get("updated_at"))
    return (today - anchor).days if anchor else None
