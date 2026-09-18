"""
The pipeline, end to end, with no network and no API key.

These are the tests that would catch a regression in the parts that matter:
selection from her real facts, the page-fit loop, the honesty guards, and the
HTTP surface the two tabs depend on.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import db, legacy, paths  # noqa: E402
from backend.agents import builder, composer, deterministic as D  # noqa: E402
from backend.models import JobPosting, Tier  # noqa: E402
from backend.services import (  # noqa: E402
    context_loader, factbank, guards, latex_render, scoring,
)

STREAMING_JD = (
    "Required: Apache Kafka, Apache Flink, SQL, Python. Requirements: build ETL "
    "pipelines, ClickHouse OLAP store, Grafana dashboards, medical device telemetry, "
    "low-latency streaming, data quality validation, AWS Glue, Airflow orchestration."
)
VISION_JD = (
    "Requirements: PyTorch, computer vision, object detection and tracking, deep "
    "learning research, keypoint estimation, LSTM sequence models, Python."
)


def job(jd: str, name: str = "Acme") -> JobPosting:
    return JobPosting(
        source="test", source_id=name, company=name, role_title="Engineer",
        url="https://example.com/job", jd_text=jd,
    )


# -- the fact bank ---------------------------------------------------------

def test_every_role_and_project_parses():
    roles, projects = factbank.load()
    assert len(roles) >= 5
    assert len(projects) >= 9
    assert {p.pid for p in projects} >= {"P1", "P2", "P4", "P7"}


def test_bullets_are_whole_sentences_not_wrapped_fragments():
    """context/ wraps at ~100 columns; a bullet must be rejoined, not truncated."""
    _roles, projects = factbank.load()
    p1 = next(p for p in projects if p.pid == "P1")
    longest = max(len(b.text) for b in p1.bullets)
    assert longest > 120, "bullets look truncated at the source line width"
    assert not any("**" in b.text for b in p1.bullets)


def test_the_do_not_reuse_framing_is_honoured():
    """03-experience.md keeps the _DS framing as a historical record only."""
    roles, _ = factbank.load()
    insops = next(r for r in roles if "InsOps" in r.employer)
    by_name = {f.name: f.reusable for f in insops.framings}
    ds = [v for k, v in by_name.items() if "data-science" in k.lower()]
    de = [v for k, v in by_name.items() if "data-engineering" in k.lower()]
    assert ds == [False], "the historical framing must not be reusable"
    assert de == [True], "the current framing must stay usable"


def test_project_ranking_tracks_the_job():
    _roles, projects = factbank.load()
    streaming = factbank.rank_projects(projects, factbank.jd_tokens(STREAMING_JD))
    vision = factbank.rank_projects(projects, factbank.jd_tokens(VISION_JD))
    assert streaming[0][0].pid == "P1"
    assert vision[0][0].pid == "P2"


def test_coursework_project_is_never_signature():
    _roles, projects = factbank.load()
    ranked = factbank.rank_projects(projects, factbank.jd_tokens("BFS A* algorithms Python"))
    assert all(p.pid != "P10" for p, _ in ranked), "P10 is coursework and must be excluded"


# -- rendering -------------------------------------------------------------

def test_preamble_survives_the_template_comment_trap():
    """
    The template's own comment block contains the words "\\begin{document}" and
    "{{TOKEN}}". A naive extraction produces a document with no \\documentclass.
    """
    tex, _report = composer.compose_tex(job(STREAMING_JD))
    head = latex_render.preamble_of(tex)
    assert "\\documentclass" in head
    assert "\\pdfgentounicode" in tex     # what makes the PDF machine-readable
    assert "{{" not in tex


def test_latex_special_characters_are_escaped():
    assert latex_render.esc("100% & C# a_b") == r"100\% \& C\# a\_b"


def test_every_bullet_has_an_anchor():
    tex, report = composer.compose_tex(job(STREAMING_JD))
    n_bullets = tex.count("\\resumeItem{")
    assert len(report["anchors"]) >= n_bullets - 1
    assert all(isinstance(v, int) for v in report["anchors"].values())


# -- the build loop --------------------------------------------------------

@pytest.mark.parametrize("jd,expected_project", [
    (STREAMING_JD, "P1"),
    (VISION_JD, "P2"),
])
def test_build_is_one_page_and_passes_the_guards(jd, expected_project):
    res = asyncio.run(builder.build(job(jd, "T"), resume_id=f"t-{expected_project}"))
    assert res.report["fit"]["pages"] == 1
    assert res.report["signature_project"] == expected_project
    assert res.guards.ok, [v.message for v in res.guards.blockers]


def test_build_fills_the_page_rather_than_leaving_it_thin():
    res = asyncio.run(builder.build(job(STREAMING_JD, "Fill"), resume_id="t-fill"))
    # A thin one-pager is as bad as a two-pager; the fit loop must grow content.
    assert res.report["fit"]["chars"] > 2500
    assert res.attempts > 1, "the fit loop should try more than one density"


# -- scoring ---------------------------------------------------------------

def test_tier_beats_score():
    from backend.models import ScoredJob, SponsorVerdict

    def mk(tier, total):
        s = ScoredJob(
            job=job("x"), sponsor=SponsorVerdict(
                verdict="KEEP", tier=tier, reason="silent", reason_label="",
            ),
        )
        s.score.total = total
        return s

    ranked = scoring.rank([mk(Tier.C, 95), mk(Tier.S, 60), mk(Tier.B, 80)])
    assert [r.sponsor.tier for r in ranked] == [Tier.S, Tier.B, Tier.C]


def test_undated_posting_is_treated_as_stale():
    assert scoring.recency_subscore(None)[0] == 15.0


def test_missing_ad_text_is_not_reported_as_a_bad_job():
    assert scoring.recommendation(30, 50, has_jd=False) == "open the ad to judge this one"


def test_seniority_and_years_filters():
    assert scoring.title_is_too_senior("Staff Engineer")[0]
    assert not scoring.title_is_too_senior("Engineer II")[0]
    assert scoring.years_required("requires 7+ years of experience") == 7


def test_irrelevant_titles_are_dropped_before_anything_expensive():
    assert not D.title_is_relevant("Public Area Attendant")[0]
    assert not D.title_is_relevant("Recruiter, GTM")[0]
    assert D.title_is_relevant("Data Engineer")[0]
    assert D.title_is_relevant("Test Automation Engineer")[0]


def test_us_only_filter():
    from backend.services.sources.base import is_us
    assert is_us("Austin, TX")
    assert is_us("London, UK / Austin, United States")
    assert not is_us("Tokyo, Japan")
    assert not is_us("Berlin, Germany")


# -- deduplication ---------------------------------------------------------

def test_dedupe_prefers_the_posting_with_more_ad_text():
    a = JobPosting(source="remoteok", source_id="1", company="Acme",
                   role_title="Data Engineer", url="u", jd_text="short")
    b = JobPosting(source="greenhouse", source_id="2", company="Acme, Inc.",
                   role_title="Data Engineer", url="u2", jd_text="x" * 900)
    kept, dropped = D.dedupe([a, b])
    assert len(kept) == 1 and dropped == 1
    assert kept[0].source == "greenhouse"


# -- the API ---------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as c:
        yield c


def test_health_reports_every_subsystem(client):
    h = client.get("/api/health").json()
    assert h["ok"]
    assert h["engine"]["available"], "the LaTeX engine must be present"
    assert h["sponsor_index"]["rows"] > 80000
    assert h["workspace"]["context_files"] == 9


def test_missing_api_route_is_a_404_not_a_405(client):
    """The SPA catch-all must not swallow unknown /api paths."""
    assert client.post("/api/does-not-exist", json={}).status_code == 404


def test_resume_round_trip_and_ship_gate(client):
    folder = "Annie_Manoharan_USC_01"
    doc = client.get(f"/api/resumes/{folder}")
    if doc.status_code == 404:
        pytest.skip("the sample application is not present")
    d = doc.json()
    assert d["tex"].strip()

    ship = client.post(f"/api/resumes/{folder}/compile", json={"mode": "ship"}).json()
    assert ship["ok"], ship["problems"][:2]
    assert ship["pages"] == 1
    assert ship["pdf_b64"]


def test_a_fabricated_resume_cannot_ship(client):
    """The single most important behaviour: LaTeX is happy, the build is refused."""
    folder = "Annie_Manoharan_USC_01"
    src = client.get(f"/api/resumes/{folder}")
    if src.status_code == 404:
        pytest.skip("the sample application is not present")
    tex = src.json()["tex"]
    anchor = "\\section{Technical Skills}"
    poisoned = tex.replace(anchor, (
        "\\resumeItem{Cut latency 47.3\\% with Kubernetes and Snowflake}\n"
        "\\resumeItem{Engineer with 8 years of professional experience}\n"
        "\\resumeItem{Processed [FILL IN: records per day] records}\n"
    ) + anchor, 1)
    assert poisoned != tex

    out = client.post(
        f"/api/resumes/{folder}/compile", json={"tex": poisoned, "mode": "ship"}
    ).json()
    assert out["ok"] is False
    kinds = {v["kind"] for v in out["guards"]["violations"] if v["severity"] == "blocker"}
    assert "FABRICATION_NUMBER" in kinds
    assert "HONESTY_WALL" in kinds
    assert "BLOCKED_CLAIM" in kinds
    assert "FILL_IN_LEFT" in kinds


# -- suggestion actions (the "apply" buttons in the Suggestions panel) -----
# Pure string surgery, no filesystem -- these can run against any composed
# resume without touching her real output/ folders.

def test_remove_block_deletes_the_anchor_and_the_bullet_it_labels():
    tex, report = composer.compose_tex(job(STREAMING_JD, "RemoveTest"))
    block_id = next(iter(report["anchors"]))
    n_bullets_before = tex.count("\\resumeItem{")

    out = latex_render.remove_block(tex, block_id)

    assert f"@b:{block_id}" not in out
    assert out.count("\\resumeItem{") == n_bullets_before - 1


def test_remove_block_rejects_an_unknown_id():
    tex, _ = composer.compose_tex(job(STREAMING_JD, "RemoveMiss"))
    with pytest.raises(ValueError):
        latex_render.remove_block(tex, "not-a-real-block")


def test_add_skill_keyword_appears_on_the_page_and_compiles():
    tex, _ = composer.compose_tex(job(STREAMING_JD, "AddSkill"))
    fb = context_loader.load()
    section = tex[tex.find("Technical Skills"):]
    section = section[:section.find("\\section{", 1)]
    missing = next(
        s for s in sorted(fb.skills_strong | fb.skills_used)
        if len(s) > 2 and s.lower() not in section.lower()
    )

    out = latex_render.add_skill_keyword(tex, missing)
    added_section = out[out.find("Technical Skills"):]
    assert missing.lower() in legacy.strip_latex(added_section).lower()

    res = asyncio.run(guards_compile_ok(out))
    assert res


def test_add_skill_keyword_refuses_a_duplicate():
    tex, _ = composer.compose_tex(job(STREAMING_JD, "AddDup"))
    with pytest.raises(ValueError):
        latex_render.add_skill_keyword(tex, "SQL")   # already on the page


async def guards_compile_ok(tex: str) -> bool:
    from backend.services import tectonic
    out = await tectonic.compile_debounced(tex, resume_id="probe-suggest", mode="draft", return_pdf=False)
    return out.ok


def test_apply_suggestion_route_refuses_a_skill_she_cannot_claim(client):
    """
    A keyword that is not Strong or Used-it must be refused before any file is
    touched -- this is the honesty wall applied to the one-click "Apply" button.
    """
    folder = "Annie_Manoharan_USC_01"
    if not (paths.OUTPUT / folder).exists():
        pytest.skip("the sample application is not present")

    out = client.post(
        f"/api/resumes/{folder}/apply-suggestion",
        json={"action": "add_keyword", "keyword": "a-skill-she-has-never-touched-xyz"},
    )
    assert out.status_code == 400
    assert "not on your" in out.json()["detail"]


# -- the Profile tab ---------------------------------------------------------
# GET is read-only against her real context/ files, so it is always safe to
# run. The write path is only exercised for its *rejections* here -- an
# automated suite must never risk corrupting her real facts.

def test_profile_files_lists_every_context_file_with_its_real_content(client):
    rows = client.get("/api/profile/files").json()
    names = {r["name"] for r in rows}
    assert names == {
        "01-basics.md", "02-education.md", "03-experience.md", "04-projects.md",
        "05-skills.md", "06-achievements.md", "07-preferences.md", "08-voice.md",
        "09-anything-else.md", "QUESTIONS-FOR-YOU.md",
    }
    basics = next(r for r in rows if r["name"] == "01-basics.md")
    assert basics["content"] == paths.read_text(paths.CONTEXT / "01-basics.md")
    assert basics["description"]


def test_profile_file_save_rejects_a_file_outside_the_allowed_list(client):
    out = client.put("/api/profile/files/not-a-real-context-file.md", json={"content": "x"})
    assert out.status_code == 400


def test_profile_file_save_rejects_empty_content(client):
    out = client.put("/api/profile/files/08-voice.md", json={})
    assert out.status_code == 400
