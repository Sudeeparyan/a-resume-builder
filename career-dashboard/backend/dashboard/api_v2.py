"""Versioned API for the four-tab React application."""

from typing import Any, Optional
from contextlib import asynccontextmanager
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from backend.services.workspace_v2 import CareerServices, AGENTS
from backend.services.agents import AgentRunner


class StudioSave(BaseModel):
    revision: int = Field(ge=1)
    source: Optional[str] = Field(default=None, max_length=150000)
    fields: Optional[dict[str, str]] = None
    project_id: Optional[str] = None
    second_project_id: Optional[str] = None
    restore_revision: Optional[int] = None


class StudioPreview(BaseModel):
    revision: int = Field(ge=1)


class InstructionInput(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    job_id: Optional[str] = None
    revision: Optional[int] = None
    request_id: str = Field(min_length=1, max_length=100)


class AIPolicyInput(BaseModel):
    daily_call_limit: int = Field(ge=0, le=50)


class GoalInput(BaseModel):
    weekly_target: int = Field(ge=1, le=200)
    workdays: list[int]
    start_date: str


class KnowledgeInput(BaseModel):
    kind: str
    title: str = Field(min_length=1, max_length=250)
    summary: str = Field(default="", max_length=30000)
    data: dict[str, Any] = Field(default_factory=dict)
    revision: Optional[int] = None


class ReconcileInput(BaseModel):
    ids: Optional[list[str]] = None


class PostingInput(BaseModel):
    company: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=150)
    url: str = Field(min_length=8, max_length=2500)
    description: str = Field(min_length=80, max_length=100000)
    requisition_id: str = ""


class MailResolution(BaseModel):
    job_id: Optional[str] = None
    action: str = "confirm"
    create_application: bool = False


class JobRemoval(BaseModel):
    reason: str = Field(default="Not suitable", max_length=500)


class AgentInput(BaseModel):
    kind: str
    job_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    preset: str = "default"


class TierChoice(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(min_length=1, max_length=120)


class AISettingsInput(BaseModel):
    tiers: dict[str, TierChoice]


class ChatPreviewInput(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    request_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)


class ChatApplyInput(BaseModel):
    change_set_id: str = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)


class AIPreferencesInput(BaseModel):
    default: dict[str, str]
    actions: dict[str, dict[str, str]] = Field(default_factory=dict)
    fallback: Optional[dict[str, str]] = None


class AIMainInput(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    model: str = Field(min_length=1, max_length=200)


class AIKeyInput(BaseModel):
    value: str = Field(min_length=1, max_length=500)


class AITestInput(BaseModel):
    provider: str
    model: str
    action: str = "requirement_extraction"


class CompanyCheckInput(BaseModel):
    sources: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    size_category: str = "unknown"
    employee_min: Optional[int] = None
    employee_max: Optional[int] = None
    sponsorship_state: str = "unknown"
    override_reason: str = ""


class DiscoveryPreferencesInput(BaseModel):
    preset: str = "default"


class ScheduleInput(BaseModel):
    enabled: bool
    hours: int = Field(ge=1, le=24)


class AssistantInput(BaseModel):
    message: str = Field(min_length=1, max_length=120000)
    request_id: str = Field(min_length=1, max_length=100)


def attach(app, workspace, schedule: bool = False):
    service = CareerServices(workspace)
    runner = AgentRunner(service)
    from backend.services.resume_studio import ResumeStudio
    studio = ResumeStudio(service)
    runner.studio = studio
    from backend.services.instruction_tracker import InstructionTracker
    from backend.job_quality import JobQualityService
    from backend.chat_changes import ChatChangeService
    tracker = InstructionTracker(service, studio)
    quality = JobQualityService(service)
    chats = ChatChangeService(service, studio)
    from backend.services.assistant import Assistant
    from backend.services.assistant_tools import Toolbox
    assistant = Assistant(service, studio, runner, quality, tools=Toolbox(service, studio, runner, quality, chats))
    app.state.assistant = assistant
    app.state.tracker = tracker
    app.state.studio = studio
    app.state.career = service
    app.state.agents = runner
    router = APIRouter(prefix="/api/v2")

    @router.get("/summary")
    def summary():
        return service.summary()

    @router.get("/goals")
    def goals():
        return service.goals()

    @router.put("/goals")
    def save_goals(data: GoalInput):
        return service.save_goals(data.model_dump())

    @router.get("/profile")
    def profile():
        sources = {}
        # Every readable file in data/context is a source: Annie's own 01-09 files, the
        # readable profile, the questions ledger, pending updates and sources/*.md.
        context = workspace.root / "data/context"
        for path in sorted(list(context.glob("*.md")) + list((context / "sources").glob("*.md"))):
            sources[str(path.relative_to(workspace.root))] = path.read_text(encoding="utf-8")
        return {
            "items": service.knowledge(),
            "removed": sum(i["deleted"] for i in service.knowledge(True)),
            "registry": workspace.evidence(),
            "configuration": workspace.profile(),
            "sources": sources,
            "agents": AGENTS,
            "profile_dirty": service.profile_dirty(),
            "pending": service.pending_knowledge(),
            "revision": service.profile_revision(),
            "skills": [
                {
                    "name": "Evidence registry",
                    "purpose": "Approved candidate wording and evidence IDs",
                    "path": "data/context/evidence.yml",
                },
                {
                    "name": "Company-research playbook",
                    "purpose": "Public company and role investigation",
                    "path": "backend/workflows/agents/company-researcher.md",
                },
                {
                    "name": "Independent hiring review",
                    "purpose": "Role expectations without candidate context",
                    "path": "backend/workflows/agents/hiring-manager.md",
                },
                {
                    "name": "Verify job URL",
                    "purpose": "Checks specific posting URLs; browser review may still be required",
                    "path": ".agents/skills/verify-job-url/SKILL.md",
                },
                {
                    "name": "Resume validation",
                    "purpose": "Evidence, one-page PDF and visual-review gates",
                    "path": "backend/scripts/validate_resume.py",
                },
            ],
        }

    @router.post("/profile/items", status_code=201)
    def add_item(data: KnowledgeInput):
        return service.save_knowledge(data.model_dump())

    @router.put("/profile/items/{id}")
    def edit_item(id: str, data: KnowledgeInput):
        return service.save_knowledge(data.model_dump(), id)

    @router.delete("/profile/items/{id}")
    def remove_item(id: str):
        return service.delete_knowledge(id)

    @router.post("/profile/reconcile")
    def reconcile_items(data: ReconcileInput):
        return service.reconcile_knowledge(data.ids)

    @router.post("/jobs")
    def add_posting(data: PostingInput):
        """Save a posting, and report how well it matches rather than refusing it.

        Discovery applies the relevance gate before saving; a manually-added job
        had no check at all. Saving is still the user's call, so this warns.
        """
        posting = data.model_dump()
        result = service.add_posting(posting, source="manual")
        if result.get("excluded") or result.get("blocked"):
            # Not saved. The UI shows the exact sentence (or the never-re-apply rule) and the
            # posting sits in Excluded roles where a wrong call can be restored.
            return result
        try:
            relevance = quality.relevance(
                posting,
                "\n".join(item["title"] + " " + item["summary"] for item in service.profile_context()),
            )
        except Exception:
            return result
        return {**result, "relevance": relevance}

    @router.get("/excluded")
    def excluded_postings(include_restored: bool = False):
        return {"items": service.excluded(include_restored)}

    @router.post("/excluded/{excluded_id}/restore")
    def restore_excluded(excluded_id: str):
        return service.restore_excluded(excluded_id)

    @router.post("/jobs/{job_id}/sponsorship")
    def recheck_sponsorship(job_id: str):
        return service.reevaluate_sponsorship(job_id)

    @router.post("/jobs/age")
    def age_applications():
        return {"ghosted": service.age_applications()}

    @router.delete("/jobs/{job_id}")
    def remove_job(job_id: str, data: Optional[JobRemoval] = None):
        return service.remove_job(job_id, data.reason if data else "Not suitable")

    @router.post("/jobs/{job_id}/restore")
    def restore_job(job_id: str):
        return service.restore_job(job_id)

    @router.post("/jobs/verify-due")
    def verify_due_jobs():
        return quality.verify_due()

    @router.post("/jobs/{job_id}/verify")
    def verify_job(job_id: str):
        return quality.verify_posting(job_id)

    @router.get("/jobs/{job_id}/verification")
    def job_verification(job_id: str):
        return quality.posting_history(job_id)

    @router.post("/companies/{job_id}/check")
    def check_company(job_id: str, data: CompanyCheckInput):
        job = workspace.get_job(job_id)
        return quality.assess_company(job["company"], job["url"], **data.model_dump())

    @router.post("/jobs/{job_id}/cover-letter")
    def generate_cover_letter(job_id: str):
        return service.generate_cover_letter(job_id)

    @router.get("/mail")
    def mail():
        return service.mail()

    @router.post("/mail/{id}/resolve")
    def resolve_mail(id: str, data: MailResolution):
        return service.resolve_mail(id, **data.model_dump())

    @router.get("/email-schedule")
    def schedule():
        return service.pref("email_schedule", {"enabled": False, "hours": 6})

    @router.put("/email-schedule")
    def save_schedule(data: ScheduleInput):
        service.set_pref("email_schedule", data.model_dump())
        with workspace.connect() as db:
            workspace.record_event(
                db, "email_schedule_updated", settings=data.model_dump()
            )
        workspace.export_tracking()
        service.export_state()
        return data.model_dump()

    @router.get("/agents")
    def agents():
        return {"agents": AGENTS, "runs": service.runs()}

    @router.post("/agents/run", status_code=202)
    def run(data: AgentInput):
        return runner.enqueue(data.kind, data.job_id, data.provider, data.model, data.preset)

    @router.get("/ai/providers")
    def ai_providers(action: Optional[str] = None):
        return runner.gateway.catalog(action)

    @router.put("/ai/preferences")
    def ai_preferences(data: AIPreferencesInput):
        return runner.gateway.save_preferences(data.model_dump())

    @router.post("/ai/test")
    def ai_test(data: AITestInput):
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
        result = runner.gateway.generate(data.action, "Return {\"ok\": true} to verify structured generation.", schema, provider=data.provider, model=data.model, web=False)
        return {"ok": result.get("ok") is True, "provider": data.provider, "model": data.model}

    @router.get("/ai/settings")
    def ai_settings(refresh: bool = False):
        from backend.ai import settings as ai_settings

        return ai_settings.overview(service, refresh=refresh, gateway=runner.gateway)

    @router.put("/ai/main")
    def choose_main_ai(data: AIMainInput):
        from backend.ai import settings as ai_settings

        return ai_settings.choose_main(service, runner.gateway, data.provider, data.model)

    @router.put("/ai/keys/{provider}")
    def save_ai_key(provider: str, data: AIKeyInput):
        from backend.ai import settings as ai_settings

        return ai_settings.save_key(service, provider, data.value)

    @router.delete("/ai/keys/{provider}")
    def remove_ai_key(provider: str):
        from backend.ai import settings as ai_settings

        return ai_settings.remove_key(service, provider)

    @router.put("/ai/settings")
    def save_ai_settings(data: AISettingsInput):
        from backend.ai import settings as ai_settings

        return ai_settings.save(service, {
            "tiers": {tier: choice.model_dump() for tier, choice in data.tiers.items()}
        })

    @router.post("/ai/settings/test")
    def test_ai_settings(data: AITestInput):
        from backend.ai import settings as ai_settings

        return ai_settings.test_provider(service, data.provider, data.model)

    @router.get("/discovery/preferences")
    def discovery_preferences():
        return service.pref("discovery_preferences", {"preset": "default"})

    @router.put("/discovery/preferences")
    def save_discovery_preferences(data: DiscoveryPreferencesInput):
        if data.preset not in {"default", "balanced_five", "portals"}:
            raise ValueError("Choose default, balanced_five or portals")
        service.set_pref("discovery_preferences", data.model_dump())
        service.sync_projections()
        return data.model_dump()

    @router.post("/studio/{job_id}/open")
    def open_studio(job_id: str):
        # Opening a document never spends AI credits.
        return studio.open(job_id)

    @router.get("/studio/{job_id}")
    def get_studio(job_id: str):
        return studio.get(job_id)

    @router.put("/studio/{job_id}")
    def save_studio(job_id: str, data: StudioSave):
        return studio.save(job_id, **data.model_dump())

    @router.post('/studio/{job_id}/sync-profile')
    def sync_profile_studio(job_id: str, data: StudioPreview):
        return studio.sync_profile(job_id, data.revision)

    @router.get('/studio/{job_id}/assessment')
    def studio_assessment(job_id: str):
        return studio.assessment(job_id)

    @router.get('/studio/{job_id}/download')
    def studio_download(job_id: str, format: str):
        path, filename = studio.download(job_id, format)
        return FileResponse(path, filename=filename, media_type='application/pdf' if format == 'pdf' else 'application/x-tex')

    @router.post('/studio/{job_id}/chat/preview')
    def resume_chat_preview(job_id: str, data: ChatPreviewInput):
        return chats.resume_preview(job_id, data.message, data.request_id, data.expected_revision)

    @router.post('/studio/{job_id}/chat/apply')
    def resume_chat_apply(job_id: str, data: ChatApplyInput):
        return chats.resume_apply(job_id, data.change_set_id, data.request_id, data.expected_revision)

    @router.post('/studio/{job_id}/chat/undo')
    def resume_chat_undo(job_id: str, data: ChatApplyInput):
        return chats.resume_undo(job_id, data.change_set_id, data.request_id, data.expected_revision)

    @router.post('/profile/chat/preview')
    def profile_chat_preview(data: ChatPreviewInput):
        return chats.profile_preview(data.message, data.request_id, data.expected_revision)

    @router.post('/profile/chat/apply')
    def profile_chat_apply(data: ChatApplyInput):
        return chats.profile_apply(data.change_set_id, data.request_id, data.expected_revision)

    @router.post("/studio/{job_id}/fill")
    def fill_studio(job_id: str, data: StudioPreview):
        return studio.fill(job_id, data.revision)

    @router.post("/studio/{job_id}/preview")
    def preview_studio(job_id: str, data: StudioPreview):
        return studio.preview(job_id, data.revision)

    @router.get('/agents/activity')
    def agent_activity(limit: int = 60):
        from backend.services.observability import activity

        return activity(service, runner, max(1, min(limit, 200)))

    @router.get('/agent-control')
    def agent_control():
        return {'budget': runner.cache.stats(), 'runs': service.runs(), 'agents': AGENTS}

    @router.put('/agent-control/budget')
    def ai_budget(data: AIPolicyInput):
        return runner.cache.configure(data.daily_call_limit)

    @router.get('/instructions')
    def instructions(job_id: Optional[str] = None):
        return tracker.history(job_id)

    @router.post('/instructions')
    def instruction(data: InstructionInput):
        return tracker.send(**data.model_dump())

    @router.post('/studio/{job_id}/score')
    def score_studio(job_id: str):
        return studio.score(job_id)

    @router.get('/assistant')
    def assistant_overview():
        return assistant.overview()

    @router.post('/assistant/messages', status_code=202)
    def assistant_send(data: AssistantInput):
        # Returns at once; the reply and its steps fill in on the worker thread.
        return assistant.send(data.message, data.request_id)

    @router.get('/assistant/messages/{message_id}')
    def assistant_message(message_id: str):
        return assistant.get(message_id)

    @router.post('/assistant/messages/{message_id}/stop')
    def assistant_stop(message_id: str):
        # The worker ends the reply at its next step; the row reads "Stopping…" until then.
        return assistant.stop(message_id)

    @router.get('/assistant/conversations')
    def assistant_conversations():
        return assistant.conversations()

    @router.post('/assistant/conversations', status_code=201)
    def assistant_new_conversation():
        assistant.new_conversation()
        return assistant.overview()

    @router.delete('/assistant/conversations')
    def assistant_clear_history():
        assistant.clear_history()
        return assistant.overview()

    @router.put('/assistant/conversations/{conversation_id}')
    def assistant_open_conversation(conversation_id: str):
        assistant.open_conversation(conversation_id)
        return assistant.overview()

    @router.delete('/assistant/conversations/{conversation_id}')
    def assistant_delete_conversation(conversation_id: str):
        assistant.delete_conversation(conversation_id)
        return assistant.overview()

    app.include_router(router)

    @asynccontextmanager
    async def lifespan(app):
        runner.recover()
        # Background work (Gmail sync, posting liveness sweep) reaches the network,
        # so it starts only for a real server run, never for a constructed app.
        if schedule:
            runner.start_schedule()
        yield
        runner.stop.set()
        runner.pool.shutdown(wait=False, cancel_futures=True)
        if assistant.pool:
            assistant.pool.shutdown(wait=False, cancel_futures=True)

    app.router.lifespan_context = lifespan
    return service
