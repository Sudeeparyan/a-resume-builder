"""Discovery that reaches every tracked employer and lists every eligible match.

Before 2026-10-02 only Greenhouse, Lever and Ashby boards were read, so 3 of 12 tracked
employers were ever searched and 12 of 15 saved jobs were Snowflake. Workday and
SmartRecruiters boards (most medical-device, university and lab employers) are read
now, only entry-level titles in Annie's tracks are opened, the feed pass saves every
eligible match spread across employers, and run records no longer carry posting texts.
No network: the boards' JSON is recorded here.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from backend.job_quality import JobQualityService, requires_enrollment, title_in_tracks  # noqa: E402
from backend.services import portals  # noqa: E402
from backend.services.agents import AgentRunner, spread_across_companies  # noqa: E402
from backend.services.workspace_v2 import compact_run_result  # noqa: E402
from test_career_workspace import workspace  # noqa: E402,F401
from test_workspace_v2 import service  # noqa: E402,F401

DESCRIPTION = ("Build Python and SQL data pipelines on AWS with Airflow and Kafka streaming; validate device telemetry, "
               "write automated tests and maintain ETL jobs for clinical dashboards. Bachelor's or Master's degree.")


# --- reading the boards -------------------------------------------------------------------

def test_board_tokens_for_workday_and_smartrecruiters():
    assert portals.board_token({"careers_url": "https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers"}) == \
        ("workday", "medtronic.wd1.myworkdayjobs.com/MedtronicCareers")
    assert portals.board_token({"careers_url": "https://jobs.smartrecruiters.com/BoschGroup"}) == ("smartrecruiters", "BoschGroup")
    assert portals.board_token({"ats": "workday", "ats_token": "dexcom.wd1.myworkdayjobs.com/Dexcom"}) == \
        ("workday", "dexcom.wd1.myworkdayjobs.com/Dexcom")
    assert portals.board_token({"careers_url": "https://boards.greenhouse.io/Datadog"}) == ("greenhouse", "datadog")
    assert portals.board_token({"careers_url": "https://jobs.mayoclinic.org/"}) == (None, None)


def test_workday_reads_listing_then_opens_only_matching_us_titles(monkeypatch):
    listing = {"total": 4, "jobPostings": [
        {"title": "SW Test Development Engineer 2", "externalPath": "/job/San-Diego/SW-Test_JR1", "locationsText": "San Diego, California"},
        {"title": "Sr SW Test Development Engineer", "externalPath": "/job/San-Diego/Sr_JR2", "locationsText": "San Diego, California"},
        {"title": "Data Engineer I", "externalPath": "/job/Bengaluru/DE_JR3", "locationsText": "Bengaluru, India"},
        {"title": "Process Technician 3", "externalPath": "/job/Mesa/PT_JR4", "locationsText": "Mesa, Arizona"},
    ]}
    detail = {"jobPostingInfo": {"title": "SW Test Development Engineer 2", "jobDescription": "<p>" + DESCRIPTION + "</p>",
                                 "location": "San Diego, California", "country": {"descriptor": "United States of America"},
                                 "jobReqId": "JR1", "startDate": "2026-09-30",
                                 "externalUrl": "https://dexcom.wd1.myworkdayjobs.com/Dexcom/job/San-Diego/SW-Test_JR1"}}
    calls = []

    def fake(url, body=None):
        calls.append(url)
        if url.endswith("/Dexcom/jobs"):
            return (listing if body["offset"] == 0 else {"total": 4, "jobPostings": []}), None
        return detail, None

    monkeypatch.setattr(portals, "_get_json", fake)
    found, error = portals.fetch_board({"name": "Dexcom", "ats": "workday", "ats_token": "dexcom.wd1.myworkdayjobs.com/Dexcom"})
    assert error is None
    assert [p["title"] for p in found] == ["SW Test Development Engineer 2"]
    assert found[0]["location"] == "San Diego, California, United States of America"
    assert found[0]["description"].startswith("Build Python") and found[0]["requisition_id"] == "JR1"
    # Only the one matching US title was opened; the senior, foreign and non-track ones were not.
    assert [url for url in calls if "/job/" in url] == ["https://dexcom.wd1.myworkdayjobs.com/wday/cxs/dexcom/Dexcom/job/San-Diego/SW-Test_JR1"]


def test_smartrecruiters_reads_us_listing_and_opens_matching_titles(monkeypatch):
    def fake(url, body=None):
        if "/postings?" in url:
            return {"totalFound": 2, "content": [{"id": "111", "name": "Software Engineer"}, {"id": "222", "name": "Sales Manager"}]}, None
        assert url.endswith("/postings/111")
        return {"name": "Software Engineer", "refNumber": "REF1", "postingUrl": "https://jobs.smartrecruiters.com/WesternDigital/111",
                "location": {"city": "San Jose", "region": "CA", "country": "us"},
                "jobAd": {"sections": {"jobDescription": {"title": "About", "text": "<p>" + DESCRIPTION + "</p>"}}}}, None

    monkeypatch.setattr(portals, "_get_json", fake)
    found, error = portals.fetch_board({"name": "Western Digital", "careers_url": "https://jobs.smartrecruiters.com/WesternDigital"})
    assert error is None and [p["title"] for p in found] == ["Software Engineer"]
    assert found[0]["location"] == "San Jose, CA, us" and found[0]["url"].endswith("/111")


def test_fetch_all_reports_every_board_and_never_stops_on_one_failure(monkeypatch):
    rows = [{"name": "Good", "ats": "greenhouse", "ats_token": "good"},
            {"name": "Broken", "ats": "greenhouse", "ats_token": "broken"},
            {"name": "Page only", "careers_url": "https://example.org/careers"}]
    monkeypatch.setattr(portals, "tracked_companies", lambda: rows)

    def board(row, title_ok=None):
        if row["name"] == "Broken":
            raise RuntimeError("socket closed")
        return [portals._posting(row, "1", "Data Engineer", "https://boards.greenhouse.io/good/jobs/1", "Austin, TX", DESCRIPTION)], None

    monkeypatch.setattr(portals, "fetch_board", board)
    postings, coverage = portals.fetch_all()
    assert len(postings) == 1
    assert coverage[0] == "Good: 1 open postings via greenhouse"
    assert coverage[1].startswith("Broken: FETCH FAILED (RuntimeError")
    assert "no public ATS feed" in coverage[2]


def test_every_tracked_board_in_portals_yml_is_readable():
    rows = portals.tracked_companies()
    assert len(rows) >= 50
    readable = [row for row in rows if portals.board_token(row)[0]]
    assert len(readable) >= 45
    assert len({row["name"] for row in rows}) == len(rows)


# --- titles and eligibility -----------------------------------------------------------------

@pytest.mark.parametrize("title,expected", [
    ("SW Test Development Engineer 2", True), ("Software QA Engineer 2", True), ("ML Engineer I", True),
    ("Associate Data Engineer", True), ("Software Developer", True), ("Engineering Technician 1", False),
    ("Process Engineer 1", False), ("Marketing Manager", False),
    # Skill words from her track signals must not admit other kinds of job (seen live 2026-10-02).
    ("Warehouse operator", False), ("Account Executive, API", False), ("Dir, Global Warehouse Automation", False),
    ("Data Scientist - Algorithms", True), ("Applied Scientist", True), ("SDET", True),
])
def test_titles_in_annie_s_tracks(title, expected):
    assert title_in_tracks(title) is expected


def test_roles_for_current_students_are_not_hers():
    assert requires_enrollment("- Must be actively enrolled in an accredited college/university program during the internship")
    assert requires_enrollment("You must be returning to school after the internship.")
    assert not requires_enrollment("Currently pursuing or recently completed a degree in Computer Science.")
    assert not requires_enrollment("BS or MS in Computer Engineering. Recent graduates welcome.")


def test_relevance_names_the_enrollment_blocker(service):
    posting = {"title": "Software Engineer Intern (Database Engineering)", "location": "Menlo Park, CA",
               "url": "https://jobs.ashbyhq.com/snowflake/1",
               "description": DESCRIPTION + "\n- Must be actively enrolled in an accredited college/university program during the time of the internship"}
    result = JobQualityService(service).relevance(posting, "Python SQL AWS Airflow Kafka")
    assert not result["eligible"] and any("current students" in b for b in result["blockers"])


# --- what a pass saves and stores ------------------------------------------------------------

def test_spread_across_companies_interleaves_best_first():
    jobs = [{"company": "Snowflake", "id": "s1"}, {"company": "Snowflake", "id": "s2"}, {"company": "Mayo Clinic", "id": "m1"},
            {"company": "Snowflake", "id": "s3"}, {"company": "Dexcom", "id": "d1"}]
    assert [j["id"] for j in spread_across_companies(jobs)] == ["s1", "m1", "d1", "s2", "s3"]


def test_run_records_keep_who_what_where_but_not_posting_texts():
    result = {"summary": "x", "jobs": [{"company": "A", "title": "T", "url": "u", "location": "L", "description": "long " * 500}] * 3}
    compact = compact_run_result(result)
    assert compact["jobs"] == [{"company": "A", "title": "T", "url": "u", "location": "L"}] * 3
    assert compact["jobs_read"] == 3 and compact["summary"] == "x"
    assert compact_run_result({"summary": "no jobs key"}) == {"summary": "no jobs key"}
    assert len(json.dumps(compact)) < 500


def test_the_feed_pass_lists_every_eligible_match_whatever_today_s_plan(service, monkeypatch):
    companies = ["Dexcom", "Medtronic", "Mayo Clinic", "Western Governors University", "Illumina", "Insulet", "ResMed"]
    postings = []
    for index, company in enumerate(companies):
        board = {"name": company, "careers_url": f"https://boards.greenhouse.io/c{index}"}
        for role in ("Data Engineer", "Software Engineer"):
            postings.append(portals._posting(board, f"{index}{role[0]}", role, f"https://boards.greenhouse.io/c{index}/jobs/{role[0]}",
                                             "Austin, TX", DESCRIPTION + " Python SQL Kafka Airflow pipeline streaming testing."))
    monkeypatch.setattr(portals, "fetch_all", lambda *a, **k: (postings, [f"{c}: 2 open postings via greenhouse" for c in companies]))
    # Today's application plan is already met: the AI search would refuse, the feed pass still lists jobs.
    service.save_goals({"weekly_target": 1, "workdays": [0, 1, 2, 3, 4, 5, 6], "start_date": service.today()})
    monkeypatch.setattr(service, "goals", lambda on=None: {**service.__class__.goals(service, on), "remaining_today": 0})
    with pytest.raises(ValueError, match="daily application target"):
        AgentRunner(service, lambda *a, **k: {}).enqueue("discovery", preset="balanced_five")

    runner = AgentRunner(service, lambda *a, **kw: pytest.fail("the portals preset must never call the AI"))
    runner.enqueue("discovery", preset="portals")
    runner.pool.shutdown(wait=True)
    run = service.runs()[0]
    assert run["state"] == "completed", run["error"]
    saved = service.w.jobs()
    rejected = run["result"]["rejected_leads"]
    assert len(saved) > 5, rejected
    # Spread across employers: the first seven saved (in save order) are seven different companies.
    company = {job["id"]: job["company"] for job in saved}
    first = [company[job_id] for job_id in run["result"]["added_job_ids"]][:7]
    assert len(first) == 7 and len(set(first)) == 7
    # The stored run keeps no posting texts.
    assert all("description" not in job for job in run["result"]["jobs"])


def test_a_restore_sticks_when_the_next_pass_reads_the_same_sentence(service, monkeypatch):
    board = {"name": "Dexcom", "careers_url": "https://boards.greenhouse.io/dexcom"}
    refusing = portals._posting(board, "9", "Data Engineer", "https://boards.greenhouse.io/dexcom/jobs/9", "San Diego, CA",
                                DESCRIPTION + " Python SQL Kafka Airflow pipeline. We are unable to provide visa sponsorship.")
    monkeypatch.setattr(portals, "fetch_all", lambda *a, **k: ([dict(refusing)], ["Dexcom: 1 open postings via greenhouse"]))

    def feed_pass():
        runner = AgentRunner(service, lambda *a, **kw: pytest.fail("no AI"))
        runner.enqueue("discovery", preset="portals")
        runner.pool.shutdown(wait=True)
        return service.runs()[0]

    first = feed_pass()
    assert [item["url"] for item in first["result"]["excluded"]] == [refusing["url"]]
    excluded_id = first["result"]["excluded"][0]["id"]
    service.restore_excluded(excluded_id)

    second = feed_pass()
    assert second["state"] == "completed", second["error"]
    assert second["result"]["excluded"] == []
    row = next(item for item in service.excluded(include_restored=True) if item["id"] == excluded_id)
    assert row["restored_at"]  # still restored: the pass did not clear her decision
    # The restored job is still saved (the liveness sweep may mark the made-up URL expired; it never deletes it).
    assert [(job["url"], job["deleted_at"]) for job in service.w.jobs(include_deleted=True)] == [(refusing["url"], None)]


def test_internships_and_out_of_target_postings_are_skipped_quietly_by_the_feed_pass(service, monkeypatch):
    board = {"name": "Western Digital", "careers_url": "https://boards.greenhouse.io/wd"}
    good = portals._posting(board, "1", "Software Engineer", "https://boards.greenhouse.io/wd/jobs/1", "San Jose, CA",
                            DESCRIPTION + " Python SQL Kafka Airflow pipeline streaming testing.")
    noise = [
        portals._posting(board, "2", "Summer 2027 Intern - Hardware Engineering", "https://boards.greenhouse.io/wd/jobs/2", "San Jose, CA", DESCRIPTION),
        portals._posting(board, "3", "Senior Software Engineer", "https://boards.greenhouse.io/wd/jobs/3", "San Jose, CA", DESCRIPTION),
        portals._posting(board, "4", "Software Engineer", "https://boards.greenhouse.io/wd/jobs/4", "Mexico City, Mexico",
                         DESCRIPTION + " Visa sponsorship is NOT provided for this position."),
        portals._posting(board, "5", "Warehouse operator", "https://boards.greenhouse.io/wd/jobs/5", "Durham, NC", DESCRIPTION),
    ]
    monkeypatch.setattr(portals, "fetch_all", lambda *a, **k: ([good, *noise], ["Western Digital: 5 open postings via greenhouse"]))
    runner = AgentRunner(service, lambda *a, **kw: pytest.fail("no AI"))
    runner.enqueue("discovery", preset="portals")
    runner.pool.shutdown(wait=True)
    run = service.runs()[0]
    assert run["state"] == "completed", run["error"]
    assert [job["title"] for job in service.w.jobs()] == ["Software Engineer"]
    # Nothing outside her target lands in Excluded roles or the rejected-lead log.
    assert service.excluded() == [] and run["result"]["excluded"] == []
    assert run["result"]["rejected_leads"] == [] and run["result"]["outside_target"] == 4
    assert "Skipped 4 postings outside her target" in run["result"]["summary"]


def test_internship_titles_are_blocked_by_relevance(service):
    posting = {"title": "Master's Machine Learning Internship 2027 (USA)", "location": "San Francisco, CA",
               "url": "https://boards.greenhouse.io/pinterest/jobs/1", "description": DESCRIPTION}
    result = JobQualityService(service).relevance(posting, "Python SQL AWS Airflow Kafka")
    assert not result["eligible"] and any("Internships and co-ops" in b for b in result["blockers"])
