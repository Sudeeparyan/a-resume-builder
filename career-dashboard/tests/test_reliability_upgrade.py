"""Reliability upgrade contracts: migration, freshness, scoring, AI and chat."""

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend/scripts")]

from backend.ai.providers import AnthropicProvider, OpenAIProvider
from backend.assessment import assess, extract_requirements
from backend.chat_changes import ChatChangeService
from backend.job_quality import JobQualityService
from backend.resume_rules import canonicalize_skill_list, parse_skills
from backend.services.resume_studio import ResumeStudio
from test_career_workspace import add, workspace
from test_workspace_v2 import service


def test_numbered_migrations_preserve_jobs_and_create_recovery_manifest(service):
    job = add(service.w, "migration")
    before = service.w.get_job(job["id"])
    # Reopening is idempotent and must preserve the exact identity/status fields.
    reopened = type(service.w)(service.w.root)
    after = reopened.get_job(job["id"])
    assert after["id"] == before["id"]
    assert after["status"] == before["status"]
    with reopened.connect() as db:
        # Every declared migration must be applied, whatever the current count.
        from backend.migrations import MIGRATIONS

        applied = [row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert applied == [version for version, _name, _sql in MIGRATIONS]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    manifest = json.loads((reopened.root / "data/migrations/pre-v1-artifacts.sha256.json").read_text())
    assert manifest["database_copy"].endswith("pre-v1-career.db")


@pytest.mark.parametrize(
    "response,state",
    [
        ({"status": 404, "final_url": "https://careers.example.test/jobs/1", "text": ""}, "expired"),
        ({"status": 410, "final_url": "https://careers.example.test/jobs/1", "text": ""}, "expired"),
        ({"status": 200, "final_url": "https://careers.example.test/jobs/1", "text": "This job is no longer accepting applications."}, "expired"),
        ({"status": 403, "final_url": "https://careers.example.test/jobs/1", "text": "Access denied"}, "needs_review"),
        ({"status": None, "final_url": "https://careers.example.test/jobs/1", "text": "", "error": "TimeoutError"}, "needs_review"),
        ({"status": 200, "final_url": "https://careers.example.test/jobs/1", "text": "Data Analyst in Ireland. Apply now."}, "active"),
    ],
)
def test_posting_verification_is_conservative_and_recoverable(service, response, state):
    job = add(service.w)
    result = JobQualityService(service).verify_posting(job["id"], response)
    assert result["state"] == state
    saved = service.w.get_job(job["id"])
    assert saved["posting_state"] == state
    assert saved["id"] == job["id"]
    if state == "expired":
        assert job["id"] not in {item["id"] for item in service.w.jobs()}
        assert job["id"] in {item["id"] for item in service.w.jobs(include_deleted=True)}


def test_expired_applied_job_remains_in_history(service):
    job = add(service.w)
    service.w.update_job(job["id"], "applied", application_date="2026-09-10")
    JobQualityService(service).verify_posting(job["id"], {"status": 404, "final_url": job["url"], "text": ""})
    assert service.w.get_job(job["id"])["status"] == "applied"
    assert job["id"] in {item["id"] for item in service.w.jobs()}


def test_relevance_legitimacy_and_balanced_shortfall_are_honest(service):
    quality = JobQualityService(service)
    posting = {
        "title": "Data Engineer", "location": "Austin, TX", "url": "https://acme.example/jobs/1",
        "description": "Required Python, SQL, Apache Kafka streaming pipelines, Airflow orchestration on AWS Glue and S3, data validation and quality checks. Responsibilities include ETL, lakehouse data modeling and clinical device telemetry dashboards. PyTorch a plus.",
    }
    profile = "Python SQL Apache Kafka Flink streaming pipelines Airflow AWS Glue S3 data validation quality ETL lakehouse clinical device telemetry dashboards PyTorch"
    relevance = quality.relevance(posting, profile)
    assert relevance["eligible"] and relevance["score"] >= 70
    # US-only: the same posting in Dublin is not eligible, and a refusal sentence is a blocker with the sentence shown.
    dublin = quality.relevance({**posting, "location": "Dublin, Ireland"}, profile)
    assert not dublin["eligible"] and any("United States" in b for b in dublin["blockers"])
    refusing = quality.relevance({**posting, "description": posting["description"] + " We are unable to sponsor work visas."}, profile)
    assert not refusing["eligible"] and any("unable to sponsor" in b for b in refusing["blockers"])
    blocked = quality.assess_company("Acme", posting["url"], [{"url": "https://acme.example/about", "accessed_at": "2026-09-17"}], ["Registered legal entity"], ["Recruiter requests payment fee"])
    assert blocked["state"] == "blocked"
    result = quality.balanced_five([])
    assert not result["complete"]
    assert result["jobs"] == []
    assert {item["category"] for item in result["shortages"]} == {"startup", "mid", "large"}


def test_grounded_assessments_separate_readiness_coverage_and_fit():
    jd = "SQL and Power BI are required. You will build dashboards for stakeholders. Python is preferred."
    requirements = extract_requirements(jd)
    assert requirements and all(item["excerpt"] in jd for item in requirements)
    result = assess(
        "Annie Prasanna Manoharan\nannie@example.com +1 (479) 301-1366\nEducation\nMS Computer Engineering\nTechnical Skills\nSQL and Power BI\nProfessional Experience\nBuilt dashboards\nProjects\nReporting " + "evidence " * 260,
        jd,
        profile_entries=[{"id": "SKILL-PY", "title": "Python", "summary": "Registered academic Python", "deleted": 0}],
    )
    assert set(result) >= {"ats_readiness", "resume_coverage", "opportunity_fit", "keywords"}
    python = next(item for item in result["keywords"] if item["requirement"] == "Python")
    assert python["status"] == "supported_missing_from_pdf"
    assert result["resume_coverage"]["score"] != result["ats_readiness"]["score"]


def test_skill_parser_preserves_commas_and_capitalizes_terms():
    skills = parse_skills("power bi; sql\nPython, pandas and NumPy; rag; tfidf")
    assert skills == ["Power BI", "SQL", "Python, pandas and NumPy", "RAG", "TF-IDF"]
    assert canonicalize_skill_list("api; aws; dbscan") == "API; AWS; DBSCAN"


def test_provider_payloads_are_structured_and_secrets_are_not_disclosed(service, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret-value")
    seen = {}
    def transport(url, payload, headers):
        seen.update(url=url, payload=payload, headers=headers)
        return {"output_text": '{"ok": true}'}
    provider = OpenAIProvider(service.w.root, transport)
    result = provider.generate("test", {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}, model=provider.models[0])
    assert result == {"ok": True}
    assert seen["payload"]["text"]["format"]["type"] == "json_schema"
    assert "openai-secret-value" not in json.dumps(seen["payload"])
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(ValueError) as error:
        provider.generate("test", {}, model=provider.models[0])
    assert "secret" not in str(error.value).casefold()


def test_chat_previews_are_idempotent_and_profile_requires_confirmation(service):
    studio = ResumeStudio(service)
    chats = ChatChangeService(service, studio)
    revision = service.profile_revision()
    first = chats.profile_preview("add skill: API | Candidate-reported API skill", "req-1", revision)
    again = chats.profile_preview("ignored duplicate text", "req-1", revision)
    assert again["id"] == first["id"]
    assert not any(item["title"] == "API" for item in service.knowledge())
    applied = chats.profile_apply(first["id"], "req-1", revision)
    assert applied["state"] == "applied"
    assert any(item["title"] == "API" for item in service.knowledge())
    with pytest.raises(ValueError, match="changed"):
        chats.profile_preview("add skill: AWS", "req-2", revision)


@pytest.mark.parametrize("location,expected", [
    ("Austin, TX", True), ("Remote (US)", True), ("United States", True), ("Boston, Massachusetts", True),
    ("Dublin, OH", True), ("Dublin, CA 94568", True), ("Vancouver, WA", True), ("London, KY", True), ("Paris, TX", True),
    ("Remote - US or Canada", True), ("New York, NY or London, UK", True),
    ("Dublin, Ireland", False), ("London, UK", False), ("Vancouver, BC", False), ("Toronto, ON", False),
    ("Bengaluru, IN", False), ("Berlin, DE", False), ("Remote (EMEA)", False), ("Hyderabad, India", False), ("", False),
])
def test_us_location_handles_american_namesakes_of_foreign_cities(location, expected):
    """Cardinal Health is in Dublin, OH; that is a US posting, while Dublin, Ireland is not."""
    from backend.job_quality import is_us_location
    assert is_us_location(location) is expected, location
