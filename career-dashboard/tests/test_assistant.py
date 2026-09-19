"""The assistant chat: paste a posting, get the resume; everything else routes to the same services the tabs use."""

import shutil
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend/scripts"), str(ROOT / "tests")]

from test_career_workspace import JD, workspace  # noqa: E402,F401
from test_workspace_v2 import service  # noqa: E402,F401
import backend.ai  # noqa: E402
from backend.ai.agents import schemas  # noqa: E402
from backend.ai.agents.graph import AgentError  # noqa: E402
from backend.services.agents import AgentRunner  # noqa: E402
from backend.services.assistant import Assistant, looks_like_posting, parse_posting_fields  # noqa: E402
from backend.services.resume_studio import ResumeStudio  # noqa: E402

POSTING = """Software Engineer, Data Platform
Acme Analytics
Austin, TX (Hybrid)

About the role
We are looking for an early-career engineer to build streaming data pipelines with Apache Kafka and Flink,
orchestrate ETL with Airflow on AWS (Glue, S3), write SQL transformations and validate data quality.

Responsibilities
- Build and operate pipelines in Python and PostgreSQL
- Work with analysts on data quality

Qualifications
- Bachelor's degree in Computer Science or similar
- Experience with Python and SQL; Kafka or Flink preferred
"""
LINK = "https://careers.acme.test/jobs/1234"
REFUSAL = "Must be authorized to work in the United States without sponsorship now or in the future."


class StubTeam:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def run(self, name, payload, **_options):
        self.calls.append((name, payload))
        if self.error:
            raise AgentError(self.error)
        return self.result


def use_team(monkeypatch, team, configured=True):
    monkeypatch.setattr(backend.ai, "any_provider_configured", lambda root: configured)
    monkeypatch.setattr(backend.ai, "team_for", lambda services, on_usage=None: team)


@pytest.fixture
def assistant(service, monkeypatch):
    studio = ResumeStudio(service)
    runner = AgentRunner(service, execute=lambda *a, **k: (_ for _ in ()).throw(AssertionError("no AI here")))
    runner.studio = studio
    # In-process: replies are complete when send() returns.
    return Assistant(service, studio, runner, background=False)


def stub_fit(assistant, monkeypatch):
    """Stand in for the compile-measure-cut loop so the pipeline test needs no LaTeX run."""
    def fit(job_id, revision):
        draft = assistant.studio.get(job_id)
        return {**draft, "revision": revision,
                "preview": {"path": "applications/x/studio/preview-1", "page_count": 1, "body_font_pt": 10.5,
                            "layout": {"pages": [{"fill_percent": 96.0}]}, "ranking": {"cuts": []}, "current": True},
                "match": {"resume_coverage": {"score": 72}, "ats_readiness": {"score": 95}, "missing_unsupported": ["flink"]}}
    monkeypatch.setattr(assistant.studio, "fit", fit)


def test_posting_detection_and_free_field_extraction():
    assert looks_like_posting(POSTING)
    assert not looks_like_posting("find jobs")
    assert not looks_like_posting("what did I apply to last week?")
    fields = parse_posting_fields(POSTING + "\nApply: " + LINK + ".")
    assert fields["title"] == "Software Engineer, Data Platform"
    assert fields["location"] == "Austin, TX (Hybrid)"
    assert fields["url"] == LINK
    labelled = parse_posting_fields("Company: Acme Analytics\nJob title: Data Engineer\nLocation: Remote (US)\n")
    assert labelled == {"company": "Acme Analytics", "title": "Data Engineer", "location": "Remote (US)"}


def test_pasted_posting_without_a_link_asks_once_then_builds_the_resume(assistant, monkeypatch):
    stub_fit(assistant, monkeypatch)
    use_team(monkeypatch, StubTeam(schemas.PostingFields(company="Acme Analytics", title="Software Engineer, Data Platform", location="Austin, TX (Hybrid)")))
    first = assistant.send(POSTING, "m1")
    assert first["state"] == "needs_input" and "link" in first["response"]
    assert assistant.s.pref("assistant_pending")["kind"] == "posting_link"

    second = assistant.send("here you go " + LINK, "m2")
    assert second["state"] == "done", second["response"]
    data = second["data"]
    assert data["intent"] == "resume_ready" and data["pdf"].endswith("/resume.pdf") and data["coverage"] == 72
    assert [s["label"] for s in second["steps"]][:5] == [
        "Reading the posting", "Sponsorship gate and never-re-apply", "Opening the draft",
        "Fitting one US Letter page", "Scoring against the posting"]
    assert all(s["state"] == "done" for s in second["steps"])
    # The job is on the Dashboard like any other saved posting, with its tier, and no AI was needed to save it.
    [job] = assistant.w.jobs()
    assert job["company"] == "Acme Analytics" and job["title"] == "Software Engineer, Data Platform" and job["sponsor_tier"] in {"S", "A", "B", "C"}
    assert job["status"] == "prepared" and job["application_date"] is None
    assert assistant.s.pref("assistant_pending") is None
    assert "nothing here has been submitted" in second["response"].casefold()


def test_the_parser_cannot_invent_an_employer(assistant, monkeypatch):
    """A value that is not in the pasted text is dropped, and the chat asks instead."""
    stub_fit(assistant, monkeypatch)
    body = "\n".join(POSTING.splitlines()[3:])  # no title line, no company line
    use_team(monkeypatch, StubTeam(schemas.PostingFields(company="Globex", title="Wizard")))
    reply = assistant.send(body + "\n" + LINK, "m1")
    assert reply["state"] == "needs_input" and "Company | Job title | Location" in reply["response"]
    answer = assistant.send("Acme Analytics | Data Engineer | Austin, TX", "m2")
    assert answer["state"] == "done" and answer["data"]["intent"] == "resume_ready"
    [job] = assistant.w.jobs()
    assert (job["company"], job["title"], job["location"]) == ("Acme Analytics", "Data Engineer", "Austin, TX")


def test_a_refusing_posting_is_excluded_with_its_sentence_and_never_drafted(assistant, monkeypatch):
    use_team(monkeypatch, StubTeam(error="must not be called: the fields are labelled"), configured=False)
    reply = assistant.send("Company: Acme Analytics\nTitle: Data Engineer\nLocation: Austin, TX\n" + LINK + "\n" + POSTING + "\n" + REFUSAL, "m1")
    assert reply["state"] == "done" and "without sponsorship" in reply["response"]
    assert reply["data"]["intent"] == "posting_excluded"
    assert assistant.w.jobs() == [] and len(assistant.s.excluded()) == 1
    assert reply["steps"][1]["state"] == "failed"


def test_same_role_again_is_blocked_and_the_same_link_reuses_the_record(assistant, monkeypatch):
    stub_fit(assistant, monkeypatch)
    use_team(monkeypatch, StubTeam(error="not needed"), configured=False)
    labelled = "Company: Acme Analytics\nTitle: Data Engineer\nLocation: Austin, TX\n" + POSTING + "\n"
    assert assistant.send(labelled + LINK, "m1")["data"]["intent"] == "resume_ready"
    again = assistant.send(labelled + "https://careers.acme.test/jobs/9999", "m2")
    assert again["data"]["intent"] == "posting_blocked" and again["data"]["rule"] == "same_role"
    same = assistant.send(labelled + LINK, "m3")
    assert same["data"]["intent"] == "resume_ready" and same["data"]["duplicate"] is True
    assert len(assistant.w.jobs()) == 1


def test_applied_is_recorded_only_after_yes_and_keeps_her_date(assistant, monkeypatch):
    stub_fit(assistant, monkeypatch)
    use_team(monkeypatch, StubTeam(error="not needed"), configured=False)
    assistant.send("Company: Acme Analytics\nTitle: Data Engineer\nLocation: Austin, TX\n" + POSTING + "\n" + LINK, "m1")
    ask = assistant.send("applied to Acme on 2026-09-10", "m2")
    assert ask["state"] == "needs_input" and "2026-09-10" in ask["response"]
    assert assistant.w.jobs()[0]["application_date"] is None
    assert assistant.send("no", "m3")["state"] == "done"
    assert assistant.w.jobs()[0]["application_date"] is None
    assistant.send("I applied to Acme on 2026-09-10", "m4")
    done = assistant.send("yes", "m5")
    assert done["data"]["intent"] == "mark_applied"
    job = assistant.w.jobs()[0]
    assert job["status"] == "applied" and job["application_date"] == "2026-09-10"


def test_ambiguous_company_asks_which_posting(assistant, monkeypatch):
    stub_fit(assistant, monkeypatch)
    use_team(monkeypatch, StubTeam(error="not needed"), configured=False)
    for n, title in enumerate(("Data Engineer", "Machine Learning Engineer"), 1):
        assistant.send(f"Company: Acme Analytics\nTitle: {title}\nLocation: Austin, TX\n{POSTING}\nhttps://careers.acme.test/jobs/{n}", f"m{n}")
    which = assistant.send("study plan for Acme", "m3")
    assert which["state"] == "needs_input" and "1. Acme Analytics — Data Engineer" in which["response"]
    # The runner is asked for a real study_plan run for the chosen job.
    queued = []
    monkeypatch.setattr(assistant.runner, "enqueue", lambda kind, job_id=None, *a, **k: queued.append((kind, job_id)) or {"id": "run1234abcd", "state": "queued"})
    picked = assistant.send("2", "m4")
    assert picked["state"] == "done" and picked["data"]["run_id"] == "run1234abcd"
    assert queued == [("study_plan", [j for j in assistant.w.jobs() if j["title"] == "Machine Learning Engineer"][0]["id"])]


def test_find_jobs_starts_discovery_and_status_reads_the_workspace(assistant, monkeypatch):
    queued = []
    monkeypatch.setattr(assistant.runner, "enqueue", lambda kind, job_id=None, provider=None, model=None, preset="default": queued.append((kind, preset)) or {"id": "d1", "state": "queued"})
    assistant.s.set_pref("discovery_preferences", {"preset": "portals"})
    found = assistant.send("find me some jobs", "m1")
    assert found["state"] == "done" and queued == [("discovery", "portals")]
    status = assistant.send("status", "m2")
    assert status["state"] == "done" and "This week" in status["response"]
    assert assistant.send("help", "m3")["data"]["intent"] == "help"


def test_open_questions_go_to_the_agent_with_the_snapshot_and_the_tools(assistant, monkeypatch):
    """A question needs no tool: the agent reads the snapshot and replies, changing nothing."""
    team = StubTeam(schemas.AgentTurn(thought="Nothing is applied yet; answering from the snapshot.", action="reply",
                                      reply="You have nothing applied yet.", suggestions=["status", "find jobs"]))
    use_team(monkeypatch, team)
    before = assistant.w.jobs()
    reply = assistant.send("what did I apply to last week?", "m1")
    assert reply["state"] == "done" and reply["response"] == "You have nothing applied yet."
    assert reply["data"]["suggestions"] == ["status", "find jobs"] and reply["data"]["intent"] == "agent"
    [(name, payload)] = team.calls
    assert name == "workspace_agent" and payload["task"] == [{"role": "user", "content": "what did I apply to last week?"}]
    assert set(payload["workspace"]) >= {"jobs", "goals", "counts", "active_runs", "profile_has_unreviewed_edits"}
    assert {t["name"] for t in payload["tools"]} >= {"list_jobs", "build_resume", "run_agent", "search_profile", "set_goals"}
    assert assistant.w.jobs() == before
    # The model's decision is the one step, with its thought as the detail.
    assert [(s["label"], s["state"], s["agent"]) for s in reply["steps"]] == [("Thinking", "done", "assistant")]


def test_without_a_provider_the_chat_still_runs_the_exact_commands(assistant, monkeypatch):
    use_team(monkeypatch, StubTeam(error="unreachable"), configured=False)
    reply = assistant.send("what did I apply to last week?", "m1")
    assert reply["state"] == "done" and "No AI runtime" in reply["response"]


def test_api_returns_at_once_and_the_reply_fills_in(service, monkeypatch):
    from backend.dashboard.app import create_app

    use_team(monkeypatch, StubTeam(error="not needed"), configured=False)
    app = create_app(service.w.root)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        posted = client.post("/api/v2/assistant/messages", json={"message": "status", "request_id": "r1"})
        assert posted.status_code == 202
        for _ in range(200):
            row = client.get("/api/v2/assistant/messages/r1").json()
            if row["state"] != "processing":
                break
            import time
            time.sleep(0.05)
        assert row["state"] == "done" and "This week" in row["response"]
        overview = client.get("/api/v2/assistant").json()
        assert [m["id"] for m in overview["messages"]] == ["r1"] and overview["busy"] is False
        # The same request ID is idempotent.
        assert client.post("/api/v2/assistant/messages", json={"message": "status", "request_id": "r1"}).json()["id"] == "r1"
        assert client.post("/api/v2/assistant/messages", json={"message": "help", "request_id": "r1"}).status_code == 400


def test_real_compile_end_to_end(assistant, monkeypatch):
    """The whole path with the real fitter: one US Letter page and a PDF on disk."""
    if not shutil.which("tectonic"):
        pytest.skip("PDF runtime unavailable")
    use_team(monkeypatch, StubTeam(error="not needed"), configured=False)
    reply = assistant.send("Company: Acme Analytics\nTitle: Data Engineer\nLocation: Austin, TX\n" + POSTING + "\n" + LINK, uuid.uuid4().hex)
    assert reply["state"] == "done", reply["response"]
    data = reply["data"]
    pdf = assistant.w.root / "data/output" / data["pdf"]
    assert pdf.exists() and (assistant.w.root / "data/output" / data["preview_png"]).exists()
    draft = assistant.studio.get(data["job_id"])
    assert draft["preview"]["page_count"] == 1 and draft["preview"]["current"]
