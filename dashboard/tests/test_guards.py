"""
The guards are the honesty wall in code. If these tests pass, the dashboard
cannot ship an invented metric or a study-plan skill, in any mode.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import paths  # noqa: E402
from backend.services import context_loader, guards  # noqa: E402

FB = context_loader.load()


def tex(*bullets: str) -> str:
    body = "\n".join(f"% @b:emp.1.b{i}\n\\resumeItem{{{b}}}" for i, b in enumerate(bullets, 1))
    return (
        "\\documentclass[letterpaper,10pt]{article}\n"
        "\\begin{document}\n" + body + "\n\\end{document}\n"
    )


# -- fabrication -----------------------------------------------------------

def test_invented_metric_is_a_blocker():
    r = guards.run_all(tex("Cut latency by 47.3\\% across the fleet"))
    kinds = [v.kind for v in r.blockers]
    assert "FABRICATION_NUMBER" in kinds
    assert not r.ok


def test_real_metric_from_context_passes():
    """91.83 is her real mAP figure and must not be flagged."""
    r = guards.run_all(tex("Reached 91.83\\% mAP on the pose model"))
    nums = [v for v in r.violations if v.kind == "FABRICATION_NUMBER"]
    assert nums == [], [v.token for v in nums]


def test_years_in_dates_are_not_treated_as_claims():
    r = guards.run_all(tex("Built pipelines from 2024 to 2026"))
    assert [v for v in r.violations if v.kind == "FABRICATION_NUMBER"] == []


def test_fill_in_marker_is_not_a_fabrication_but_blocks_shipping():
    r = guards.run_all(tex("Processed [FILL IN: approx. records per day] records"))
    kinds = [v.kind for v in r.violations]
    assert "FILL_IN_LEFT" in kinds
    assert "FABRICATION_NUMBER" not in kinds


# -- the honesty wall ------------------------------------------------------

def test_honest_gap_skill_is_blocked_even_though_the_word_is_in_context():
    """
    Snowflake appears in context/05-skills.md -- inside the never-claim list.
    A naive corpus check would wave it through. This is the regression that
    matters most.
    """
    r = guards.run_all(tex("Modelled the warehouse in Snowflake with dbt"))
    wall = [v for v in r.blockers if v.kind == "HONESTY_WALL"]
    assert wall, [v.kind for v in r.violations]
    assert {v.token.lower() for v in wall} & {"snowflake", "dbt"}


def test_kubernetes_is_blocked():
    r = guards.run_all(tex("Deployed services on Kubernetes"))
    assert any(v.kind == "HONESTY_WALL" for v in r.blockers)


def test_study_plan_skill_cannot_appear_on_the_resume():
    plan = "| Skill | Why |\n|---|---|\n| Kubernetes | they run it |\n"
    r = guards.run_all(tex("Ran workloads on Kubernetes"), study_plan=plan)
    assert any(v.kind == "HONESTY_WALL" for v in r.blockers)


def test_hedged_form_is_blocked_too():
    r = guards.run_all(tex("Familiar with Terraform and infrastructure as code"))
    assert any(v.kind in ("HONESTY_WALL", "HEDGED_CLAIM") for v in r.blockers)


def test_a_real_strong_skill_is_allowed():
    r = guards.run_all(tex("Built streaming jobs in Apache Flink over Kafka topics"))
    assert r.ok, [v.message for v in r.blockers]


# -- blocked claims --------------------------------------------------------

def test_years_of_experience_total_is_blocked():
    r = guards.run_all(tex("Data engineer with 3 years of professional experience"))
    assert any(v.kind == "BLOCKED_CLAIM" for v in r.blockers)


def test_publication_claim_is_blocked():
    r = guards.run_all(tex("Published in ICCV 2025 on pose estimation"))
    assert any(v.kind == "BLOCKED_CLAIM" for v in r.blockers)


# -- voice and shippability ------------------------------------------------

def test_banned_phrase_is_flagged():
    r = guards.run_all(tex("Responsible for the data platform"))
    assert any(v.kind == "BANNED_PHRASE" for v in r.violations)


def test_placeholder_blocks():
    r = guards.run_all(tex("Hired at {{COMPANY}}"))
    assert any(v.kind == "PLACEHOLDER_LEFT" for v in r.blockers)


def test_preamble_change_is_important_not_blocking():
    doc = tex("Built Flink jobs")
    good = guards.check_preamble(doc, None)
    assert good == []
    import hashlib
    sha = hashlib.sha256(doc.split("\\begin{document}")[0].encode()).hexdigest()[:16]
    assert guards.check_preamble(doc, sha) == []
    bad = guards.check_preamble(doc, "0000000000000000")
    assert len(bad) == 1
    assert bad[0].severity == "important"    # she owns the file; warn, never block


# -- anchors ---------------------------------------------------------------

def test_anchor_map_points_at_the_content_line():
    doc = "line1\n% @b:emp.1.b1\n\\resumeItem{X}\n"
    assert guards.anchor_map(doc)["emp.1.b1"] == 3


# -- the real shipped resume ----------------------------------------------

def test_the_shipped_usc_resume_has_no_blockers():
    """Her one finished application must survive its own guards."""
    p = paths.OUTPUT / "Annie_Manoharan_USC_01" / "resume.tex"
    if not p.exists():
        return
    r = guards.run_all(paths.read_text(p))
    blockers = [f"{v.kind}: {v.token} — {v.evidence[:60]}" for v in r.blockers]
    assert not blockers, blockers
