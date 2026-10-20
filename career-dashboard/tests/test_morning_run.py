"""The 07:00 morning run's own decisions: which saved jobs get a resume today, and when
to stop calling an AI that only Annie can bring back (sign-in, usage limit, budget)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT.parent / "daily-job-search" / "morning_run.py"


def load_runner(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("morning_run_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setattr(sys, "argv", ["morning_run.py"])
    spec.loader.exec_module(module)
    # Never write into the real logs folder from a test.
    monkeypatch.setattr(module, "LOG_FILE", tmp_path / "test.log")
    return module


def job(job_id, company, fit, status="saved", folder="", created="2026-10-01"):
    return {"id": job_id, "company": company, "title": "Engineer", "fit_score": fit,
            "status": status, "folder": folder, "created_at": created}


def test_prepares_best_fits_one_per_company_and_skips_companies_with_resumes_waiting(monkeypatch, tmp_path):
    runner = load_runner(monkeypatch, tmp_path)
    waiting = [job(f"s{i}", "Snowflake", 90, status="prepared", folder=f"f{i}") for i in range(3)]
    queue = [
        job("snow-new", "Snowflake", 99),
        job("mayo-a", "Mayo Clinic", 92),
        job("mayo-b", "Mayo Clinic", 91),
        job("dexcom", "Dexcom", 80),
        job("broad", "Broad Institute", None),
        job("applied", "Medtronic", 95, status="applied", folder="x"),
    ]
    chosen, held = runner.choose_jobs_to_prepare(waiting + queue, new_ids={"snow-new", "mayo-a"})
    assert [j["id"] for j in chosen] == ["mayo-a", "dexcom", "broad"]
    assert {j["id"] for j in held} == {"snow-new", "mayo-b"}


def test_the_daily_limit_holds_the_rest_for_later_mornings(monkeypatch, tmp_path):
    runner = load_runner(monkeypatch, tmp_path)
    queue = [job(f"j{i}", f"Company {i}", 70 + i) for i in range(8)]
    chosen, held = runner.choose_jobs_to_prepare(queue, new_ids=set(), limit=5)
    assert [j["id"] for j in chosen] == ["j7", "j6", "j5", "j4", "j3"]
    assert len(held) == 3


def test_only_failures_annie_must_fix_stop_the_ai_for_the_morning(monkeypatch, tmp_path):
    runner = load_runner(monkeypatch, tmp_path)
    signed_out = ("POST /api/v2/studio/x/tailor -> HTTP 400: job_tailor could not run on kimi_cli/kimi-runtime: "
                  "Kimi Code is not signed in on this machine: run `kimi login`, then retry.")
    assert "kimi login" in runner.ai_blocker(signed_out)
    assert "usage limit" in runner.ai_blocker("Your Kimi membership's usage limit is reached.")
    assert "budget" in runner.ai_blocker("study_plan run failed: Daily AI call budget reached. Saved results remain.")
    # A problem with one job's content is that job's problem, not a reason to stop.
    assert runner.ai_blocker("A tailored project arrived without a title or bullets") is None
    assert runner.ai_blocker("Kimi Code reached its time limit. Retry a smaller pass.") is None
