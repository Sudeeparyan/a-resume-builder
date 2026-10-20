"""What only Annie can do now: one list for the Dashboard and the Assistant.

Each item says what to do and where, in plain words. Nothing is done for her:

* no AI app or key set up on this PC;
* an AI app that has signed out (its last call failed with a sign-in error), which would leave
  tailoring and study plans undone every morning until she signs in again;
* pending profile entries, which new resumes wait for;
* suggested (predicted) resume items still waiting for her keep/remove in Assurance;
* open questions in QUESTIONS-FOR-YOU.md, which sharpen every future resume.

Ported from the Template (October 2026); its Irish permit-expiry, salary-floor and overnight-hunt
items do not apply to Annie's US search.
"""

from __future__ import annotations

import re

QUESTIONS_FILE = "data/context/QUESTIONS-FOR-YOU.md"
SIGNED_OUT = re.compile(r"not signed in|kimi login|sign in|authentication required|no credentials? configured", re.I)


def items(services) -> list[dict]:
    """[{id, text, where, job_ids?}], most urgent first; ``where`` is the dashboard page that resolves it."""
    root = services.w.root
    out: list[dict] = []
    from backend.ai import any_provider_configured, provider_label

    if not any_provider_configured(root):
        out.append({"id": "ai_setup", "where": "settings",
                    "text": "Set up an AI app (Kimi Code, Codex, Claude Code or Antigravity) or a key in Settings; "
                            "tailoring resumes and study plans need one."})
    else:
        signed_out = _signed_out(root)
        if signed_out:
            names = " and ".join(provider_label(p) for p in signed_out)
            fix = "open Kimi Code, or run `kimi login`" if "kimi_cli" in signed_out else "open the app and sign in"
            out.append({"id": "ai_signed_out", "where": "settings",
                        "text": f"{names} {'is' if len(signed_out) == 1 else 'are'} signed out, so tailoring and study "
                                f"plans cannot run on {'it' if len(signed_out) == 1 else 'them'}. Sign in again ({fix}), "
                                "then use Test in Settings."})
    if services.profile_dirty():
        out.append({"id": "profile_pending", "where": "profile",
                    "text": "Confirm the pending entries in Profile; new resumes wait for them."})
    with services.w.connect() as db:
        rows = db.execute(
            "SELECT r.job_id, j.company, COUNT(*) AS n FROM resume_items r JOIN jobs j ON j.id = r.job_id "
            "WHERE r.origin='predicted' AND r.decision='pending' AND j.status IN ('saved','prepared') "
            "GROUP BY r.job_id, j.company ORDER BY j.company").fetchall()
    if rows:
        total = sum(row["n"] for row in rows)
        companies = ", ".join(dict.fromkeys(row["company"] for row in rows[:3]))
        out.append({"id": "assurance_pending", "where": "assurance", "job_ids": [row["job_id"] for row in rows],
                    "text": f"{total} suggested resume item{'s' if total != 1 else ''} wait{'' if total != 1 else 's'} for "
                            f"your keep or remove in Assurance ({companies}{'…' if len(rows) > 3 else ''}) before "
                            "those resumes are ready to send."})
    try:
        open_count = open_questions((root / QUESTIONS_FILE).read_text(encoding="utf-8"))
    except OSError:
        open_count = 0
    if open_count:
        out.append({"id": "open_questions", "where": "profile",
                    "text": f"{open_count} question{'s' if open_count != 1 else ''} in your profile still "
                            f"need{'' if open_count != 1 else 's'} your answer; each one makes future resumes sharper."})
    return out


def open_questions(text: str) -> int:
    """Questions (### headings) with at least one part still unanswered (an unticked box)."""
    sections = re.split(r"^###\s", text, flags=re.M)[1:]
    return sum(1 for section in sections if re.search(r"^- \[ \]", section, re.M))


def _signed_out(root) -> list[str]:
    """Free plans whose latest call failed with a sign-in error and has not succeeded since."""
    from backend.ai import limits, ready_providers, router

    try:
        health = limits.HealthBook(root).status()
        ready = ready_providers(root)
    except Exception:  # noqa: BLE001 - this list is advice; it must never stop the Dashboard
        return []
    out = []
    for provider in router.FREE:
        entry = health.get(provider) or {}
        error, failed_at, ok_at = entry.get("last_error") or "", entry.get("last_error_at") or "", entry.get("last_ok") or ""
        if ready.get(provider) and error and SIGNED_OUT.search(error) and failed_at > ok_at:
            out.append(provider)
    return out
