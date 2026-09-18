"""The bridge must behave exactly like the scripts it wraps, minus the defects."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import legacy as L  # noqa: E402
from backend import paths  # noqa: E402


def test_paths_resolve_to_the_real_workspace():
    assert paths.CONTEXT.is_dir()
    assert paths.SCRIPTS.is_dir()
    assert (paths.CONTEXT / "01-basics.md").exists()
    assert paths.SPONSORSHIP_YML.exists()


def test_track_fields_match_the_tsv_schema():
    assert L.TRACK_FIELDS[0] == "app_id"
    assert L.TRACK_FIELDS[-1] == "notes"
    assert len(L.TRACK_FIELDS) == 15
    assert L.REJECT_COOLDOWN_DAYS == 180
    assert L.GHOST_COOLDOWN_DAYS == 90
    assert L.GHOST_AFTER_DAYS == 21


def test_refresh_today_unfreezes_the_import_time_date():
    L.track.TODAY = date(2000, 1, 1)
    assert L.refresh_today() == date.today()
    assert L.track.TODAY == date.today()


# -- the sponsorship gate: the rule that governs everything ----------------

def test_explicit_refusal_is_excluded_with_the_triggering_sentence():
    r = L.screen_jd(
        "Great team building data pipelines. "
        "We are unable to provide visa sponsorship for this position, now or in the future. "
        "Apply today."
    )
    assert r["verdict"] == "EXCLUDED"
    assert r["reason_label"]
    assert "sponsorship" in (r["sentence"] or "").lower()


def test_clearance_requirement_is_excluded():
    r = L.screen_jd("This position requires an active US security clearance.")
    assert r["verdict"] == "EXCLUDED"


def test_citizenship_requirement_is_excluded():
    r = L.screen_jd("Applicants must be US citizens due to ITAR requirements.")
    assert r["verdict"] == "EXCLUDED"


def test_silence_about_sponsorship_is_kept():
    """Most postings say nothing. This is the largest bucket and must survive."""
    r = L.screen_jd(
        "Data Engineer. You will build ETL pipelines in Python and SQL on AWS. "
        "Bachelor's degree required. We offer health insurance and 401k."
    )
    assert r["verdict"] == "KEEP"


def test_authorized_to_work_is_not_a_refusal():
    """She IS authorized -- this phrase must never exclude her."""
    r = L.screen_jd(
        "Candidates must be legally authorized to work in the United States. "
        "Python, Spark, and Airflow experience preferred."
    )
    assert r["verdict"] == "KEEP"


def test_explicit_offer_is_tier_a():
    r = L.screen_jd("Visa sponsorship is available for this role.")
    assert r["verdict"] == "KEEP"
    assert r["tier"] == "A"
    assert r["evidence"]


def test_silent_posting_has_no_tier_yet():
    """
    screen() only ever returns A or EXCLUDED. S/B/C are resolved afterwards by
    the company lookup -- cap-exempt, then H-1B history, then the C default.
    The gate agent owns that second step; this pins the contract.
    """
    r = L.screen_jd("Data Engineer. Python, SQL, Airflow. Bachelor's degree required.")
    assert r["verdict"] == "KEEP"
    assert r["tier"] is None


def test_positive_patterns_are_narrow_and_only_cost_a_promotion():
    """
    Known gap: 'we welcome applicants requiring sponsorship' and 'will sponsor
    H-1B' are not in positive_sponsorship, so they read as silent. That loses a
    tier-A promotion but NEVER wrongly excludes -- the posting is still kept.
    Recorded so the behaviour is deliberate rather than a surprise.
    """
    r = L.screen_jd("We welcome applicants requiring visa sponsorship and will sponsor H-1B.")
    assert r["verdict"] == "KEEP"
    assert r["reason"] == "silent"


def test_cap_exempt_university_is_detected():
    ok, why = L.cap_exempt("University of Southern California")
    assert ok is True
    assert why


def test_normalize_strips_legal_suffixes():
    assert L.normalize_company("Acme Corp, Inc.") == L.normalize_company("Acme Corp")


# -- ATS -------------------------------------------------------------------

def test_ats_score_rewards_repeated_keywords():
    jd = (
        "Required: strong Python and SQL. Requirements: Python, SQL, Airflow. "
        "You will build data pipelines using Airflow and Python every day."
    )
    weak = r"\resumeItem{Built things}"
    strong = (
        r"\resumeItem{Built Python data pipelines in Airflow, writing SQL models}"
        r"\resumeItem{Automated SQL checks in Python across the Airflow DAGs}"
    )
    assert L.ats_score(strong, jd)["score"] > L.ats_score(weak, jd)["score"]


def test_ats_score_reports_missing_terms():
    out = L.ats_score(r"\resumeItem{Wrote Python}", "Required: Kubernetes and Terraform.")
    assert isinstance(out["missing"], list)
    assert out["score"] <= 100


def test_ats_handles_empty_jd_without_dividing_by_zero():
    assert L.ats_score("anything", "")["score"] == 0


# -- LaTeX guards ----------------------------------------------------------

def test_check_tex_source_flags_placeholders_and_fill_ins(tmp_path):
    tex = tmp_path / "r.tex"
    tex.write_text(
        r"\documentclass{article}\begin{document}"
        r"{{FULL_NAME}} processed [FILL IN: rows per day]\end{document}",
        encoding="utf-8",
    )
    problems = L.check_tex_source(tex)
    joined = " ".join(problems)
    assert "FULL_NAME" in joined
    assert "FILL IN" in joined


def test_check_tex_source_passes_a_clean_file(tmp_path):
    tex = tmp_path / "ok.tex"
    tex.write_text(
        r"\documentclass{article}" "\n" r"\begin{document}" "\n"
        r"Annie processed 40 tables." "\n" r"\end{document}" "\n",
        encoding="utf-8",
    )
    assert L.check_tex_source(tex) == []


def test_the_real_shipped_resume_still_passes_its_own_guards():
    """output/Annie_Manoharan_USC_01 is the one finished application. It must stay valid."""
    tex = paths.OUTPUT / "Annie_Manoharan_USC_01" / "resume.tex"
    if not tex.exists():
        return
    assert L.check_tex_source(tex) == []
    pdf = tex.with_suffix(".pdf")
    if pdf.exists():
        assert L.count_pdf_pages(pdf) == 1


# -- tracker ---------------------------------------------------------------

def test_exclusions_returns_three_parts_even_when_empty():
    pairs, companies, reasons = L.exclusions()
    assert isinstance(pairs, set)
    assert isinstance(companies, set)
    assert isinstance(reasons, list)
