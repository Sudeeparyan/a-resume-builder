"""Shell routes for building a new profile from documents (the onboarding page).

    GET    /api/profiles/{id}/intake                 progress, files, and the draft to review
    POST   /api/profiles/{id}/intake/files?name=...  upload one document (the raw file as the body)
    DELETE /api/profiles/{id}/intake/files/{name}    remove one
    POST   /api/profiles/{id}/intake/start           read the documents with the AI
    POST   /api/profiles/{id}/intake/stop            stop reading after the current sections
    PUT    /api/profiles/{id}/intake/draft           the person's corrections on the review card
    POST   /api/profiles/{id}/intake/build           write the workspace, then open the profile

The setup chat (interview.py) drives the same intake from the Assistant page:

    GET    /api/profiles/{id}/intake/chat                  the conversation, the open question, progress
    POST   /api/profiles/{id}/intake/chat                  {text}: a message, a typed answer or pasted notes
    POST   /api/profiles/{id}/intake/chat/answer           {question_id, choices, other, skip}
    POST   /api/profiles/{id}/intake/chat/files?name=...   attach one document (the raw file as the body)

Uploads are the raw file in the request body (no multipart), so no extra
dependency is needed. Every route works only inside that profile's own folder.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Request
from pydantic import BaseModel, Field

from backend.paths import APP_ROOT
from backend.profiles import ProfileError
from backend.services.intake.extract import MAX_BYTES
from backend.services.intake.interview import SetupChat
from backend.services.intake.job import IntakeJob, safe_name


class DraftChanges(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=200)
    preferred_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=200)
    linkedin: Optional[str] = Field(default=None, max_length=200)
    github: Optional[str] = Field(default=None, max_length=200)
    portfolio_url: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, max_length=200)
    country_pack: Optional[str] = Field(default=None, max_length=10)
    roles: Optional[list[str]] = None
    authorization: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=120000)


class ChatAnswer(BaseModel):
    question_id: str = Field(min_length=1, max_length=40)
    choices: list[str] = Field(default_factory=list, max_length=20)
    other: str = Field(default="", max_length=4000)
    skip: bool = False


def _legacy_preferences(profiles) -> dict:
    """The machine's saved AI choices (kept in the backup profile's database), read-only."""
    path = profiles.legacy_root / "data/career.db"
    found = {}
    if not path.is_file():
        return found
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5) as db:
            for key in ("ai_preferences", "ai_policy"):
                row = db.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
                if row:
                    found[key] = json.loads(row[0])
    except sqlite3.Error:
        pass
    return found


def team_factory(profiles):
    """An AgentTeam on the machine's AI (the same main choice the backup profile uses).

    Nothing about the intake is recorded in any other profile's database: usage goes
    to the intake's own state file through `on_usage`.
    """

    def make(on_usage):
        from backend.ai import _default_model, ready_providers, resolve_tiers
        from backend.ai.agents.graph import AgentTeam

        ready = ready_providers(APP_ROOT)
        if not any(ready.values()):
            raise ValueError("No AI is set up on this PC to read the documents. Add an API key or sign in to "
                             "Claude Code or Codex in Settings (on any profile), then try again.")
        preferences = _legacy_preferences(profiles).get("ai_preferences") or {}
        tiers, _moved = resolve_tiers(APP_ROOT, preferences, ready)
        backup = preferences.get("fallback") or {}
        fallback = None
        if backup.get("provider") and ready.get(backup["provider"]):
            fallback = (backup["provider"], backup.get("model") or _default_model(backup["provider"], "strong"))
        return AgentTeam(APP_ROOT, tiers, on_usage, fallback=fallback)

    return make


def review(job: IntakeJob) -> dict:
    """Everything the review card shows."""
    from backend.countries import available

    state = job.state()
    draft = job.draft()
    out = {**state, "packs": [{"code": p.code, "name": p.name, "paper": p.paper_label} for p in available()]}
    if draft:
        out["draft"] = {
            "contact": draft.get("contact") or {},
            "authorization": draft.get("authorization") or {},
            "targets": draft.get("targets") or {},
            "country_pack": draft.get("country_pack") or "us",
            "counts": {
                "education": len(draft.get("education") or []),
                "experience": len(draft.get("experience") or []),
                "projects": len(draft.get("projects") or []),
                "skills": sum(len(g.get("skills") or []) for g in draft.get("skills") or []),
                "certifications": len(draft.get("certifications") or []),
                "statements": len(draft.get("statements") or []),
                "interview_answers": len(draft.get("interview_answers") or []),
            },
            "education": [{"degree": e.get("degree"), "field": e.get("field"), "institution": e.get("institution"),
                           "start": e.get("start"), "end": e.get("end"), "grade": e.get("grade")} for e in draft.get("education") or []],
            "experience": [{"title": r.get("title"), "employer": r.get("employer"), "start": r.get("start"), "end": r.get("end"),
                            "bullets": len(r.get("bullets") or [])} for r in draft.get("experience") or []],
            "projects": [{"name": p.get("name"), "kind": p.get("kind"), "facts": len(p.get("facts") or []),
                          "metrics": len(p.get("metrics") or [])} for p in draft.get("projects") or []],
            "skills": [{"name": g.get("name"), "skills": g.get("skills") or []} for g in draft.get("skills") or []],
            "certifications": [{"name": c.get("name"), "issuer": c.get("issuer"), "date": c.get("date")} for c in draft.get("certifications") or []],
            "questions": draft.get("questions") or [],
            "coverage": {k: v for k, v in (draft.get("coverage") or {}).items() if k != "verbatim"}
                        | {"verbatim": len((draft.get("coverage") or {}).get("verbatim") or [])},
        }
    return out


def attach_intake(api, profiles, apps) -> dict:
    jobs: dict[str, IntakeJob] = {}
    guard = threading.Lock()
    make_team = team_factory(profiles)

    def job_for(profile_id: str, onboarding_only: bool = True) -> IntakeJob:
        profile = profiles.get(profile_id)
        if profile.get("legacy"):
            raise ProfileError(f"{profile['name']} is the backup profile; its facts are edited on the Profile page.")
        if onboarding_only and profile["state"] != "onboarding":
            raise ProfileError("This profile is already built. Add new facts from the Assistant or the Profile page.")
        with guard:
            if profile_id not in jobs:
                jobs[profile_id] = IntakeJob(profiles.root_for(profile_id), make_team)
            return jobs[profile_id]

    @api.get("/api/profiles/{profile_id}/intake")
    def intake_state(profile_id: str):
        profile = profiles.get(profile_id)
        if profile.get("legacy"):
            return {"state": "built", "legacy": True, "files": [], "steps": []}
        return review(job_for(profile_id, onboarding_only=False))

    @api.post("/api/profiles/{profile_id}/intake/files")
    async def intake_upload(profile_id: str, request: Request, name: str):
        job = job_for(profile_id)
        data = await request.body()
        if len(data) > MAX_BYTES:
            raise ValueError("That file is larger than 20 MB. Upload a smaller copy.")
        job.add_file(name, data)
        return review(job)

    @api.delete("/api/profiles/{profile_id}/intake/files/{name}")
    def intake_remove(profile_id: str, name: str):
        job = job_for(profile_id)
        job.remove_file(name)
        return review(job)

    @api.post("/api/profiles/{profile_id}/intake/start")
    def intake_start(profile_id: str):
        job = job_for(profile_id)
        job.start()
        return review(job)

    @api.post("/api/profiles/{profile_id}/intake/stop")
    def intake_stop(profile_id: str):
        job = job_for(profile_id)
        job.cancel()
        return review(job)

    @api.put("/api/profiles/{profile_id}/intake/draft")
    def intake_update(profile_id: str, data: DraftChanges):
        job = job_for(profile_id)
        job.update(data.model_dump(exclude_none=True))
        return review(job)

    @api.post("/api/profiles/{profile_id}/intake/build")
    def intake_build(profile_id: str):
        job = job_for(profile_id)
        summary = job.build()
        finish(profile_id, job, summary)
        return {**review(job), "profile": profiles.get(profile_id)}

    # ---- the setup chat (interview.py): the same job, driven from the Assistant page ----
    chats: dict[str, SetupChat] = {}

    def chat_for(profile_id: str, onboarding_only: bool = True) -> SetupChat:
        job = job_for(profile_id, onboarding_only)
        with guard:
            chat = chats.get(profile_id)
            if chat is None or chat.job is not job:  # a reset profile gets a new job, so a new chat
                from backend.countries import available

                packs = [{"code": p.code, "name": p.name, "paper": p.paper_label} for p in available()]
                chat = chats[profile_id] = SetupChat(
                    job, profiles.get(profile_id)["name"], packs, make_team, review,
                    lambda: build_and_open(profile_id, job))
            return chat

    def build_and_open(profile_id: str, job: IntakeJob) -> dict:
        summary = job.build()
        finish(profile_id, job, summary)
        return summary

    @api.get("/api/profiles/{profile_id}/intake/chat")
    def chat_view(profile_id: str):
        if profiles.get(profile_id).get("legacy"):
            raise ProfileError("The backup profile is already built; use its Assistant.")
        return chat_for(profile_id, onboarding_only=False).view()

    @api.post("/api/profiles/{profile_id}/intake/chat")
    def chat_message(profile_id: str, data: ChatMessage):
        return chat_for(profile_id).message(data.text)

    @api.post("/api/profiles/{profile_id}/intake/chat/answer")
    def chat_answer(profile_id: str, data: ChatAnswer):
        return chat_for(profile_id).answer(data.question_id, data.choices, data.other, data.skip)

    @api.post("/api/profiles/{profile_id}/intake/chat/files")
    async def chat_upload(profile_id: str, request: Request, name: str):
        chat = chat_for(profile_id)
        data = await request.body()
        if len(data) > MAX_BYTES:
            raise ValueError("That file is larger than 20 MB. Upload a smaller copy.")
        chat.job.add_file(name, data)
        return chat.uploaded([safe_name(name)])

    def finish(profile_id: str, job: IntakeJob, summary: dict) -> None:
        """Open the built profile, give it the machine's AI choices, its base resume and its daily task."""
        draft = job.draft() or {}
        profiles.update(profile_id, state="ready", country=summary["pack"], built_at=summary["built_at"])
        app = apps.app(profile_id)  # first open seeds the profile database from the new files
        service = app.state.career
        for key, value in _legacy_preferences(profiles).items():
            service.set_pref(key, value)
        with service.w.connect() as db:
            service.w.record_event(db, "profile_built_from_documents", files=[f["name"] for f in job.files()],
                                   coverage=(draft.get("coverage") or {}).get("accounted"))
        service.w.export_tracking()
        threading.Thread(target=base_resume, args=(job, service.w), name="profile-base-resume", daemon=True).start()
        from backend.services import schedule_tasks

        schedule_tasks.install_for(profiles, profile_id)

    def base_resume(job: IntakeJob, workspace) -> None:
        """Compile and validate the new base resume; the result shows on the Profile and in the intake state."""
        from backend.pdf_compiler import tectonic_executable

        name = str(workspace.profile()["candidate"].get("full_name") or "Candidate").split()
        stem = f"{name[0]}_{name[-1]}_Resume" if name else "Resume"
        base = workspace.root / "data/output/base"
        base.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(APP_ROOT / "backend/scripts/validate_resume.py"),
                   str(workspace.root / "data/templates/resume-base.tex"), "--workspace", str(workspace.root),
                   "--qa-json", str(base / "qa.json")]
        if tectonic_executable():
            command += ["--compile", "--output", str(base / f"{stem}.pdf"), "--render-dir", str(base / "resume-preview")]

        def check() -> dict:
            (base / "qa.json").unlink(missing_ok=True)
            run = subprocess.run(command, capture_output=True, text=True, timeout=240)
            qa = json.loads((base / "qa.json").read_text(encoding="utf-8")) if (base / "qa.json").exists() else {}
            return {"status": qa.get("status") or ("PASS" if run.returncode == 0 else "FAIL"),
                    "page_count": qa.get("page_count"), "compiled": bool(qa.get("compile_ok")),
                    "failures": (qa.get("failures") or [])[:8], "warnings": (qa.get("warnings") or [])[:8],
                    "pdf": f"base/{stem}.pdf" if (base / f"{stem}.pdf").exists() else None}

        try:
            result = check()
            # Long documents can run past one page: render it again with fewer bullets until it fits.
            for trim in (1, 2, 3):
                if not (result["compiled"] and (result["page_count"] or 1) > 1):
                    break
                import yaml

                from backend.services.intake.resume_base import render

                evidence = yaml.safe_load((workspace.root / "data/context/evidence.yml").read_text(encoding="utf-8"))
                (workspace.root / "data/templates/resume-base.tex").write_text(
                    render(workspace.profile(), evidence, trim), encoding="utf-8")
                result = {**check(), "trimmed": trim}
        except Exception as error:  # noqa: BLE001 - reported, never fatal to the profile
            result = {"status": "FAIL", "failures": [f"{type(error).__name__}: {error}"]}
        result["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        job._save(base_resume=result)

    return jobs
