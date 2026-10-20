"""Daily Search takes "find N jobs" end to end, and the ready-to-submit check reads what it produced.

Ported from the Template's pipeline tests (October 2026) onto Annie's own workspace: no AI app,
job board or posting page is reached. The posting check runs for real against a fake page.
"""

from __future__ import annotations

import hashlib
import json
import uuid

import pytest

from test_career_workspace import JD, workspace  # noqa: F401 - fixture
from test_workspace_v2 import service  # noqa: F401 - fixture

from backend.job_quality import JobQualityService
from backend.resume_contract import contract_for
from backend.services import fit, needs_you, readiness
from backend.services.agents import checked_resume_review
from backend.services.pipeline import STEP_IDS, Pipeline, choose


def posting(number, company="Acme Analytics", title="Data Engineer", description=JD):
    return {"company": company, "title": title, "location": "Austin, TX",
            "url": f"https://careers.example.test/jobs/{number}", "description": description}


class ScriptedRunner:
    """Each discovery pass saves the scripted companies; every other agent run just completes."""

    def __init__(self, services, script):
        self.s, self.script, self.calls = services, list(script), []
        self.gateway = type("Gateway", (), {"providers": {}})()  # no AI app: the app picks one that can search

    def enqueue(self, kind, job_id, provider, model, preset="default", count=None):
        self.calls.append({"kind": kind, "job_id": job_id, "preset": preset, "count": count})
        result = {}
        if kind == "discovery":
            companies = self.script.pop(0) if self.script else []
            added = []
            for entry in companies:
                company, title = entry if isinstance(entry, tuple) else (entry, "Data Engineer")
                number = len(self.calls) * 10 + len(added)
                saved = self.s.add_posting(posting(number, company=company, title=title), source="discovery")
                added.append(saved["job"]["id"])
            result = {"added_job_ids": added}
        run_id = uuid.uuid4().hex
        with self.s.w.connect() as db:
            db.execute("INSERT INTO agent_runs(id,kind,job_id,state,input,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                       (run_id, kind, job_id, "completed", "{}", json.dumps(result), self.s.now(), self.s.now()))
        return {"id": run_id}


class OpenOnly:
    """The Studio call the chain makes before any helper: opening the draft."""

    def __init__(self):
        self.opened = []

    def open(self, job_id):
        self.opened.append(job_id)


def chain(service, monkeypatch, script, *, closed=(), count=3, source="default"):
    runner, studio = ScriptedRunner(service, script), OpenOnly()
    pipeline = Pipeline(service, runner, studio, poll_seconds=0.01)
    ran = []
    for step in STEP_IDS:
        if step == "posting":
            continue  # the real posting check runs, against the fake page below

        def helper(job_id, config, step=step):
            ran.append((step, service.w.get_job(job_id)["company"]))
            return {"note": step, **({"verdict": "review", "score": 70, "next": ["Decide 1 item"]} if step == "ready" else {})}

        monkeypatch.setattr(pipeline, "_" + step, helper)

    def page(url):
        gone = any(url.rstrip("/").endswith("/" + number) for number in closed)
        return {"status": 404 if gone else 200, "final_url": url,
                "text": "" if gone else "Entry-level Data Engineer in Austin, TX. Apply now."}

    monkeypatch.setattr(JobQualityService, "_fetch", staticmethod(page))
    run_id = uuid.uuid4().hex
    config = {"count": count, "source": source, "provider": "auto", "model": "auto",
              "steps": {step: True for step in STEP_IDS}}
    progress = {"stage": "Waiting to start", "jobs_target": count, "started_epoch": 0, "find": {"state": "waiting"}, "jobs": []}
    with service.w.connect() as db:
        db.execute("INSERT INTO pipeline_runs(id,state,config,progress,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                   (run_id, "queued", json.dumps(config), json.dumps(progress), service.now(), service.now()))
    pipeline._run(run_id)
    return pipeline.get(run_id), runner, studio, ran


# ----- the chain ---------------------------------------------------------------------------------

def test_each_found_job_goes_through_every_helper_in_order(service, monkeypatch):
    run, runner, studio, ran = chain(service, monkeypatch, [["Acme Analytics", "Birch Data", "Cedar Insights"]])
    assert run["state"] == "completed", run["error"]
    searches = [call for call in runner.calls if call["kind"] == "discovery"]
    assert len(searches) == 1 and searches[0]["count"] == 3
    order = [step for step in STEP_IDS if step != "posting"]
    assert sorted(ran) == sorted((step, company) for company in ("Acme Analytics", "Birch Data", "Cedar Insights") for step in order)
    for job in run["progress"]["jobs"]:
        assert list(job["steps"]) == STEP_IDS
        assert all(step["state"] == "done" for step in job["steps"].values())
    assert run["progress"]["ready"] == {"ready": 0, "review": 3, "blocked": 0}


def test_a_closed_posting_gets_nothing_more_and_no_folder(service, monkeypatch):
    run, _, studio, ran = chain(service, monkeypatch, [["Acme Analytics", "Birch Data", "Cedar Insights"]],
                                closed=("11",))  # the first pass numbers its postings 10, 11, 12
    gone = next(job for job in run["progress"]["jobs"] if job["steps"]["posting"]["state"] == "failed")
    assert "closed" in gone["steps"]["posting"]["error"]
    assert all(step["state"] == "skipped" for name, step in gone["steps"].items() if name != "posting")
    assert gone["id"] not in studio.opened and not any(company == gone["company"] for _, company in ran)
    assert len(studio.opened) == 2


def test_the_feed_search_prepares_one_job_per_company_best_fit_first(service, monkeypatch):
    run, runner, _, _ = chain(service, monkeypatch,
                              [["Acme Analytics", ("Acme Analytics", "Analytics Engineer"), "Birch Data"]],
                              count=2, source="portals")
    assert [c["count"] for c in runner.calls if c["kind"] == "discovery"] == [None]  # the feed pass saves every match
    assert sorted(job["company"] for job in run["progress"]["jobs"]) == ["Acme Analytics", "Birch Data"]
    assert "one per company" in run["progress"]["find"]["note"]


def test_a_company_with_three_resumes_waiting_gets_no_fourth():
    jobs = [{"id": f"w{i}", "company": "Snowflake", "status": "prepared", "folder": f"data/output/s{i}"} for i in range(3)]
    jobs += [{"id": "new-snow", "company": "Snowflake", "status": "saved", "fit_score": 95},
             {"id": "new-acme", "company": "Acme", "status": "saved", "fit_score": 60}]
    assert choose(jobs, ["new-snow", "new-acme"], 2) == ["new-acme"]


def test_the_count_is_limited_to_what_an_ai_search_can_return(service):
    runner = type("Runner", (), {"gateway": type("G", (), {"providers": {}})(), "cache": None})()
    pipeline = Pipeline(service, runner, OpenOnly())
    with pytest.raises(ValueError, match="between 1 and 5"):
        pipeline.validate({"count": 6, "source": "default", "provider": "auto", "model": "auto"}, require_ready=False)


# ----- the independent review's verdict ------------------------------------------------------

@pytest.mark.parametrize("review, ok", [
    ({"verdict": "pass", "issues": []}, True),
    ({"verdict": "review", "issues": ["Check the degree wording."]}, True),
    ({"verdict": "review", "issues": []}, False),
    ({"verdict": "maybe", "issues": []}, False),
    ({"summary": "prose only"}, False),
])
def test_a_review_needs_a_verdict_and_its_reasons(review, ok):
    if ok:
        assert checked_resume_review(review)["verdict"] == review["verdict"]
    else:
        with pytest.raises(ValueError):
            checked_resume_review(review)
    # A pass that still lists issues is not a pass.
    assert checked_resume_review({"verdict": "pass", "issues": ["Dates"]})["verdict"] == "review"


# ----- readiness ---------------------------------------------------------------------------------

class BuiltStudio:
    """A Studio whose current draft has a built, assessed one-page PDF."""

    def __init__(self, services, job_id):
        self.services, self.job_id = services, job_id
        folder = services.w.root / "data/output/sample-job/preview"
        folder.mkdir(parents=True)
        (folder / "resume.pdf").write_bytes(b"%PDF-1.7 sample")
        self.pdf_sha256 = hashlib.sha256(b"%PDF-1.7 sample").hexdigest()

    def get(self, job_id):
        return {"revision": 4, "profile_revision": self.services.w.evidence().get("candidate_revision"),
                "preview": {"current": True, "revision": 4, "page_count": contract_for(self.services.w.root).pages,
                            "path": "sample-job/preview", "layout": {"full_pages": True}},
                "match": {"current": True, "score": 80, "resume_coverage": {"score": 80}, "ats_readiness": {"score": 90}}}


def saved_job(service, description=JD):
    job = service.add_posting(posting(7, description=description), source="discovery")["job"]
    with service.w.connect() as db:
        db.execute("UPDATE jobs SET posting_state='active', last_verified_at=? WHERE id=?", (service.now(), job["id"]))
        db.execute("UPDATE companies SET legitimacy_state='verified' WHERE id=?", (service.w.get_job(job["id"])["company_id"],))
    fit.for_job(service, job["id"], use_ai=False)  # the rules requirement check (no AI in tests)
    return service.w.get_job(job["id"])


def reviewed(service, job, pdf_sha256, review=None):
    jd_sha256 = hashlib.sha256(job["description"].encode()).hexdigest()
    with service.w.connect() as db:
        db.execute("INSERT INTO agent_runs(id,kind,job_id,state,input,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                   (uuid.uuid4().hex, "resume_match", job["id"], "completed", "{}",
                    json.dumps({"pdf_sha256": pdf_sha256, "jd_sha256": jd_sha256,
                                "review": review or {"summary": "Shows Python and SQL with quoted evidence.",
                                                     "verdict": "pass", "issues": []}}),
                    service.now(), service.now()))


def test_a_job_with_no_resume_is_not_ready(service):
    from backend.services.resume_studio import ResumeStudio

    job = service.add_posting(posting(3), source="discovery")["job"]
    result = readiness.check(service, ResumeStudio(service), job["id"])
    assert result["verdict"] == "blocked" and result["label"] == "Not ready" and result["score"] is None
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["pdf"]["state"] == "fail" and checks["posting"]["state"] == "warn"
    assert checks["sponsorship"]["state"] == "pass"
    assert "not a prediction of an interview" in result["note"]


def test_a_built_and_reviewed_resume_waits_only_for_her_predicted_items(service):
    job = saved_job(service)
    studio = BuiltStudio(service, job["id"])
    reviewed(service, job, studio.pdf_sha256)
    with service.w.connect() as db:
        for row_id, origin in (("item-1", "predicted"), ("item-2", "verified")):
            db.execute("INSERT INTO resume_items(id,job_id,section,content,origin,evidence_id,decision,created_at,updated_at) "
                       "VALUES(?,?,?,?,?,?,?,?,?)", (row_id, job["id"], "skills", "Looker", origin, "", "pending",
                                                     service.now(), service.now()))
    result = readiness.check(service, studio, job["id"])
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["review"]["state"] == "pass" and "Python and SQL" in checks["review"]["note"]
    # Only the predicted item waits for her; a verified registry item never does.
    assert checks["assurance"]["state"] == "warn" and "1 suggested item" in checks["assurance"]["note"]
    parts = result["parts"]
    assert parts["coverage"] == 80 and parts["ats"] == 90 and isinstance(parts["fit"], int)
    assert result["score"] == round((50 * parts["fit"] + 35 * 80 + 15 * 90) / 100)
    with service.w.connect() as db:
        db.execute("UPDATE resume_items SET decision='kept' WHERE id='item-1'")
    assert {c["id"]: c for c in readiness.check(service, studio, job["id"])["checks"]}["assurance"]["state"] == "pass"


@pytest.mark.parametrize("review, state", [
    ({"verdict": "pass", "issues": [], "summary": "No document issues."}, "pass"),
    ({"verdict": "review", "issues": ["Check the qualification wording."]}, "warn"),
    ({"verdict": "blocked", "issues": ["The PDF is missing the contact information."]}, "fail"),
    ({"verdict": "pass", "issues": ["The dates need review."]}, "warn"),
    ({"summary": "Legacy prose-only report."}, "warn"),
])
def test_the_exact_pdf_review_controls_readiness(service, review, state):
    job = saved_job(service)
    studio = BuiltStudio(service, job["id"])
    reviewed(service, job, studio.pdf_sha256, review)
    checked = readiness.check(service, studio, job["id"])
    review_check = next(item for item in checked["checks"] if item["id"] == "review")
    assert review_check["state"] == state
    if state != "pass":
        assert checked["verdict"] != "ready"
    if state == "fail":
        assert checked["verdict"] == "blocked" and "contact information" in review_check["note"]


def test_a_review_of_an_older_pdf_does_not_count(service):
    job = saved_job(service)
    studio = BuiltStudio(service, job["id"])
    reviewed(service, job, "an-older-pdf")
    checks = {c["id"]: c for c in readiness.check(service, studio, job["id"])["checks"]}
    assert checks["review"]["state"] == "warn" and "No independent review of this PDF" in checks["review"]["note"]


def test_a_closed_posting_blocks_the_application(service):
    job = saved_job(service)
    with service.w.connect() as db:
        db.execute("UPDATE jobs SET posting_state='expired' WHERE id=?", (job["id"],))
    result = readiness.check(service, BuiltStudio(service, job["id"]), job["id"])
    assert result["verdict"] == "blocked" and "closed" in result["next"][0]


def test_a_posting_that_now_refuses_sponsorship_blocks_the_application(service):
    job = saved_job(service)
    with service.w.connect() as db:
        db.execute("UPDATE jobs SET description=? WHERE id=?",
                   (JD + " We are unable to provide visa sponsorship for this role.", job["id"]))
    result = readiness.check(service, BuiltStudio(service, job["id"]), job["id"])
    checks = {c["id"]: c for c in result["checks"]}
    assert checks["sponsorship"]["state"] == "fail" and result["verdict"] == "blocked"


# ----- the requirement check -----------------------------------------------------------------

def test_the_rules_check_is_cached_until_the_posting_changes(service):
    job = saved_job(service)
    first = fit.cached(service, job["id"])
    assert first and first["method"] == "rules" and 0 <= first["score"] <= 100
    assert first["matrix"]["requirements"], "the rules path names the posting's tools"
    # The job card keeps discovery's own score (none for this hand-saved posting); the matrix keeps its own.
    assert service.w.get_job(job["id"]).get("fit_score") is None
    with service.w.connect() as db:
        db.execute("UPDATE jobs SET description=? WHERE id=?", (JD + " Also Terraform.", job["id"]))
    assert fit.cached(service, job["id"]) is None


def test_a_sponsorship_blocker_from_the_ai_is_left_to_the_gate(service):
    cat = fit.catalogue(service)
    raw = {"requirements": [], "hard_blockers": [
        {"excerpt": "Build streaming data pipelines with Apache Kafka and Flink", "reason": "requires visa sponsorship"},
        {"excerpt": "write SQL transformations and validate data quality", "reason": "active security clearance"}]}
    verified = fit.verify(raw, JD, cat)
    assert [b["reason"] for b in verified["hard_blockers"]] == ["active security clearance"]


def test_the_score_rewards_her_tracks_and_us_locations(service):
    matrix = {"requirements": [], "hard_blockers": []}
    good = fit.score(matrix, {"title": "Data Engineer", "location": "Austin, TX"}, service.w.root)
    senior = fit.score(matrix, {"title": "Senior Data Engineer", "location": "Austin, TX"}, service.w.root)
    abroad = fit.score(matrix, {"title": "Data Engineer", "location": "Dublin, Ireland"}, service.w.root)
    assert good["components"]["role_seniority"] == fit.ROLE_POINTS and senior["components"]["role_seniority"] == 0
    assert good["components"]["location"] == fit.LOCATION_POINTS and abroad["components"]["location"] == 0


# ----- Needs you ---------------------------------------------------------------------------------

def test_needs_you_lists_only_what_she_can_do(service, monkeypatch):
    import backend.ai as ai
    from backend.ai import limits

    monkeypatch.setattr(ai, "any_provider_configured", lambda root: False)
    ids = [item["id"] for item in needs_you.items(service)]
    assert ids[0] == "ai_setup"

    monkeypatch.setattr(ai, "any_provider_configured", lambda root: True)
    monkeypatch.setattr(ai, "ready_providers", lambda root: {"kimi_cli": True})
    limits.HealthBook(service.w.root).record("kimi_cli", False, "Kimi Code is not signed in on this machine: run `kimi login`")
    items = {item["id"]: item for item in needs_you.items(service)}
    assert "ai_signed_out" in items and "kimi login" in items["ai_signed_out"]["text"]
    # A later successful call clears it.
    limits.HealthBook(service.w.root).record("kimi_cli", True)
    assert "ai_signed_out" not in {item["id"] for item in needs_you.items(service)}


def test_needs_you_counts_predicted_items_waiting_in_assurance(service):
    job = saved_job(service)
    with service.w.connect() as db:
        db.execute("INSERT INTO resume_items(id,job_id,section,content,origin,evidence_id,decision,created_at,updated_at) "
                   "VALUES(?,?,?,?,?,?,?,?,?)", ("p-1", job["id"], "skills", "Looker", "predicted", "", "pending",
                                                 service.now(), service.now()))
    item = next(i for i in needs_you.items(service) if i["id"] == "assurance_pending")
    assert item["where"] == "assurance" and job["id"] in item["job_ids"] and "1 suggested resume item" in item["text"]
    assert any(i["id"] == "assurance_pending" for i in service.summary()["needs_you"])
