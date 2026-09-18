"""
The honesty wall, as a test.

These assert the thing the whole chat design rests on: a request that would put
an untrue claim on the page is refused, and the refusal is written in Python
rather than by the model, so it cannot be softened into a hedge.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agents import edit_ops                      # noqa: E402
from backend.agents.composer import Selection            # noqa: E402
from backend.services import context_loader, factbank, resume_spec  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    fb = context_loader.load()
    roles, projects = factbank.load()
    tex = "% @b:emp.1.b1\n\\resumeItem{Built a thing}\n"
    return edit_ops.catalogue(
        fb=fb, roles=roles, projects=projects, tex=tex, rules=[],
        spec=resume_spec.Spec(), study_terms={"terraform"},
    ), fb


def test_catalogue_offers_only_real_material(cat):
    c, fb = cat
    assert c["project_ids"], "her real projects should be offerable"
    assert all(p.startswith("P") for p in c["project_ids"])
    # Coursework is never offerable as a signature project.
    assert not set(c["project_ids"]) & set(c["coursework_project_ids"])
    # Only claimable skills reach the keyword enum.
    for s in c["skills"]:
        assert fb.claimable(s), f"{s} is not claimable but was offered"


def test_schema_cannot_express_an_unheld_skill(cat):
    c, _ = cat
    schema = edit_ops.plan_schema(c)
    variants = schema["properties"]["ops"]["items"]["oneOf"]
    kw = [v for v in variants if v["properties"]["op"]["const"] == "add_skill_keyword"]
    if kw:
        allowed = {k.lower() for k in kw[0]["properties"]["keyword"]["enum"]}
        assert "kubernetes" not in allowed
        assert "terraform" not in allowed


def test_unheld_skill_is_refused_with_a_python_authored_reason(cat):
    c, fb = cat
    _reply, ops, refusals, _d = edit_ops.validate(
        {"reply": "sure", "ops": [{"op": "add_skill_keyword", "keyword": "Kubernetes"}]},
        c, fb,
    )
    assert ops == [], "an unheld skill must never become an applied op"
    assert refusals, "and it must be explained, not silently dropped"
    text = refusals[0].reason.lower()
    # The refusal must not offer a hedge as a consolation prize.
    for hedge in ("familiar with", "exposure to", "i could add"):
        assert hedge not in text or "not even" in text


def test_honest_gap_outranks_the_study_plan_reason(cat):
    """
    Terraform is both a named honest gap and in this company's study plan.

    The honest-gap reason must win: it is the stronger statement (it can never
    appear, in any form) where the study-plan reason is only about timing.
    """
    c, fb = cat
    assert fb.forbidden("terraform"), "fixture assumes terraform is a named gap"
    _r, ops, refusals, _d = edit_ops.validate(
        {"reply": "", "ops": [{"op": "add_skill_keyword", "keyword": "terraform"}]},
        c, fb,
    )
    assert ops == []
    assert any("05-skills.md" in r.reason for r in refusals)


def test_study_plan_term_is_refused_on_timing_grounds(cat):
    """A term that is only in the study plan gets the timing reason."""
    c, fb = cat
    term = "zephyr-rtos-scheduling"          # not a gap, not claimable, invented
    assert not fb.forbidden(term)
    c2 = dict(c, study_terms=[term])
    _r, ops, refusals, _d = edit_ops.validate(
        {"reply": "", "ops": [{"op": "add_skill_keyword", "keyword": term}]}, c2, fb,
    )
    assert ops == []
    assert any("study plan" in r.reason.lower() for r in refusals)


def test_invented_project_is_refused(cat):
    c, fb = cat
    _r, ops, refusals, _d = edit_ops.validate(
        {"reply": "", "ops": [{"op": "include_project", "project_id": "P99"}]}, c, fb,
    )
    assert ops == []
    assert any("04-projects.md" in r.reason for r in refusals)


def test_real_requests_are_applied(cat):
    c, fb = cat
    pid = c["project_ids"][0]
    _r, ops, refusals, _d = edit_ops.validate(
        {"reply": "done", "ops": [
            {"op": "set_pages", "pages": 2},
            {"op": "include_project", "project_id": pid},
            {"op": "set_section_order", "order": ["projects", "experience"]},
        ]},
        c, fb,
    )
    assert len(ops) == 3 and not refusals

    spec, spec_ops, tex_ops, _meta = edit_ops.split(resume_spec.Spec(), ops)
    assert spec.pages_target == 2
    assert pid in spec.selection.include_projects
    assert spec.selection.section_order == ["projects", "experience"]
    assert all(o.applied for o in spec_ops)
    assert tex_ops == []


def test_three_pages_is_not_representable(cat):
    c, fb = cat
    _r, ops, _refusals, _d = edit_ops.validate(
        {"reply": "", "ops": [{"op": "set_pages", "pages": 3}]}, c, fb,
    )
    # It survives validate() (shape is fine) but cannot be applied.
    spec, spec_ops, _t, _m = edit_ops.split(resume_spec.Spec(), ops)
    assert spec.pages_target == 1, "a 3-page resume must never be produced"
    assert all(not o.applied for o in spec_ops)


def test_rules_win_over_the_stored_spec():
    """A standing rule must outlive a one-off change, or it is not a rule."""
    base = resume_spec.Spec(pages_target=1)

    class R:
        mechanical = True
        op = "set_pages"
        args = {"pages": 2}

    assert resume_spec.apply_rule(base, R()).pages_target == 2


def test_selection_defaults_match_the_old_globals():
    """Proves the refactor changed no behaviour for existing callers."""
    from backend.agents import composer
    s = Selection()
    assert (s.max_roles, s.bullets_first_role, s.bullets_other_role) == (
        composer.MAX_ROLES, composer.BULLETS_FIRST_ROLE, composer.BULLETS_OTHER_ROLE
    )
    assert (s.max_projects, s.bullets_signature, s.bullets_supporting) == (
        composer.MAX_PROJECTS, composer.BULLETS_SIGNATURE, composer.BULLETS_SUPPORTING
    )
