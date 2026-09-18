"""
The Manager Agent must never learn who the candidate is.

Its whole value is that it is an outside view. An agent that has read her
profile writes a bar she happens to clear, which is worse than useless -- it
looks objective and is not.

These tests are the enforcement. The prompt asking nicely is not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agents import manager, prompts                      # noqa: E402
from backend.models import CompanyResearch, DemandRow, JobPosting  # noqa: E402
from backend.services import context_loader                       # noqa: E402


def _job() -> JobPosting:
    return JobPosting(
        source="test", source_id="1", company="Acme Robotics",
        role_title="Data Engineer", url="https://acme.example/jobs/1",
        location="Austin, TX",
        jd_text=(
            "Required: strong Python and SQL. You will build and own Kafka "
            "streaming pipelines feeding a ClickHouse warehouse. "
            "Nice to have: Airflow, dbt."
        ),
    )


def _research() -> CompanyResearch:
    """Research WITH a demand map, because that is the leak vector."""
    return CompanyResearch(
        company="Acme Robotics",
        what_they_do="Warehouse robots.",
        engineering_reality="Kafka and ClickHouse, Go services.",
        current_projects=["Realtime fleet telemetry"],
        future_direction=["On-device inference"],
        team_shape="Six engineers, one manager.",
        pressures=["Telemetry volume doubled"],
        day_job_months_1_3="Own the ingest path.",
        day_job_month_12="Design the next warehouse.",
        demand_map=[
            # Every field below is derived from HER profile.
            DemandRow(skill="Apache Kafka", candidate_level="strong",
                      destination="resume", note="she has this"),
            DemandRow(skill="dbt", candidate_level="none",
                      destination="study_plan", note="she lacks this"),
        ],
        fit_narrative="She would be a strong fit for this team.",
        sources=["https://acme.example/blog"],
    )


def test_payload_excludes_the_demand_map():
    """
    DemandRow carries candidate_level and destination, both computed from her
    profile. predict_payload already leaks them into a job-shaped payload; this
    asserts manager_payload does not repeat that mistake.
    """
    text = prompts.manager_payload(_job(), _research())
    assert "candidate_level" not in text
    assert "destination" not in text
    assert "she has this" not in text
    assert "she lacks this" not in text
    assert "strong fit" not in text          # fit_narrative is about her too
    # But the genuinely company-side research is still there.
    assert "Warehouse robots" in text
    assert "Realtime fleet telemetry" in text


def test_payload_contains_no_candidate_identity():
    text = prompts.manager_payload(_job(), _research())
    low = text.lower()
    for term in manager._leak_terms():
        assert term.lower() not in low, f"{term} leaked into the manager payload"


def test_assembled_request_carries_none_of_her_facts():
    """The whole request, exactly as it would be sent."""
    fb = context_loader.load()
    system = prompts.MANAGER_AGENT
    user = prompts.manager_payload(_job(), _research())
    blob = (system + "\n" + user).lower()

    assert fb.bundle[:300].strip().lower() not in blob
    for skill in list(fb.skills_gap)[:25]:
        # A gap term may coincide with a word in the ad; what must not appear is
        # the framing that says it is HER gap.
        assert f"she does not have {skill}" not in blob
    # And no rulebook: it ends with _profile.md, which is her weights.
    assert "signature project" not in blob
    assert "honesty wall" not in blob


def test_assert_blind_catches_a_leak():
    leaked = prompts.manager_payload(_job()) + "\n\nCANDIDATE: Annie Prasanna Manoharan"
    with pytest.raises(manager.ProfileLeak):
        manager.assert_blind(prompts.MANAGER_AGENT, leaked)


def test_assert_blind_catches_a_project_id():
    leaked = prompts.manager_payload(_job()) + "\n\nHer best match is P2."
    with pytest.raises(manager.ProfileLeak):
        manager.assert_blind(prompts.MANAGER_AGENT, leaked)


def test_assert_blind_catches_the_fact_bundle():
    fb = context_loader.load()
    leaked = prompts.manager_payload(_job()) + "\n\n" + fb.bundle[:400]
    with pytest.raises(manager.ProfileLeak):
        manager.assert_blind(prompts.MANAGER_AGENT, leaked, fb=fb)


def test_clean_payload_passes():
    manager.assert_blind(
        prompts.MANAGER_AGENT, prompts.manager_payload(_job(), _research()),
        fb=context_loader.load(),
    )


def test_fallback_never_invents_a_project():
    """
    Without a model there is nothing behind a project recommendation, so the
    honest output is none at all rather than a confident guess.
    """
    v = manager.fallback_verdict(_job())
    assert v["perfect_projects"] == []
    assert v["mandatory"], "the ad's own repeated requirements are still real"
    assert v["degraded_note"]


def test_fallback_quotes_the_ad_for_each_requirement():
    v = manager.fallback_verdict(_job())
    ad = _job().jd_text
    for row in v["mandatory"]:
        if row.get("evidence_quote"):
            assert row["evidence_quote"] in ad


def test_manager_prompt_speaks_as_the_manager_not_about_her():
    p = prompts.MANAGER_AGENT.lower()
    assert "you are the hiring manager" in p
    assert "you have not seen any candidate" in p
