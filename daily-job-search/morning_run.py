#!/usr/bin/env python3
"""Annie's morning run: find up to 5 new eligible jobs and tailor a resume for each.

Started by the "Annie Daily Job Search" scheduled task at 07:00 (installed by
Install-MorningTask.ps1) so everything is ready by 9 AM. It can also be run by hand:

    career-dashboard/backend/.venv/Scripts/python.exe daily-job-search/morning_run.py

What it does, in order:
  1. Starts the dashboard server on http://127.0.0.1:8010 if it is not running.
  2. Ages quiet applications (the ghosted rule).
  3. Runs discovery: tracked career pages (no AI), then one AI web-research pass.
     Both respect the sponsorship gate, the never-re-apply rules and the weekly
     goal, and save at most 5 ranked jobs linked to today's search run.
  4. For each new job: Resume Studio AI tailor (predicted items stay pending in
     the Assurance tab), an AI study plan, and a compiled, validated one-page PDF.
  5. Regenerates the dashboard projections and writes MORNING-REPORT.md under
     daily-job-search/<date>/.

Nothing is ever submitted anywhere; Annie reviews and applies herself.
"""
import csv
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

DAILY_DIR = Path(__file__).resolve().parent
ROOT = DAILY_DIR.parent
BACKEND = ROOT / "career-dashboard" / "backend"
APP_ROOT = ROOT / "career-dashboard"
VENV_PY = BACKEND / ".venv" / "Scripts" / "python.exe"
SCRIPTS = BACKEND / "scripts"
BASE_URL = "http://127.0.0.1:8010"

# The scheduled task's console is cp1252; em-dashes and arrows in job text must not crash logging.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path[:0] = [str(APP_ROOT), str(SCRIPTS)]
try:
    from tracking import today as _today
except Exception:  # the run must still work if the app's helpers move
    _today = lambda: date.today().isoformat()  # noqa: E731

TODAY = _today()
LOG_DIR = DAILY_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / (TODAY + ".log")
REPORT_DIR = DAILY_DIR / TODAY


def log(message):
    line = time.strftime("%H:%M:%S") + "  " + message
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


class ApiError(Exception):
    pass


def api(method, path, body=None, timeout=30):
    request = urllib.request.Request(BASE_URL + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, data=data, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:1500]
        raise ApiError(f"{method} {path} -> HTTP {error.code}: {detail}") from None
    except (OSError, ValueError) as error:
        raise ApiError(f"{method} {path} -> {error}") from None


def server_health():
    try:
        with urllib.request.urlopen(BASE_URL + "/api/health", timeout=2) as response:
            document = json.load(response)
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def ensure_server():
    document = server_health()
    if document:
        if str(document.get("root", "")).replace("\\", "/").rstrip("/").endswith("career-dashboard"):
            log("Dashboard is already running on " + BASE_URL)
            return
        raise SystemExit(
            "Port 8010 is answered by a different app, so the morning run cannot start. "
            "Close whatever is on port 8010 and run Start Dashboard.cmd."
        )
    log("Dashboard is not running; starting it in the background (no browser tab).")
    server_log = LOG_FILE.open("a", encoding="utf-8")
    starter = VENV_PY if VENV_PY.exists() else "python"
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(starter), "run.py", "--no-browser"],
        cwd=str(BACKEND),
        stdout=server_log,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        close_fds=True,
    )
    deadline = time.monotonic() + 300  # the first start can rebuild the React client
    while time.monotonic() < deadline:
        if server_health():
            log("Dashboard is up on " + BASE_URL)
            return
        time.sleep(3)
    raise SystemExit(
        "The dashboard did not start within 5 minutes. "
        "Open Start Dashboard.cmd and share what it says. Log: " + str(LOG_FILE)
    )


def run_agent(kind, job_id=None, preset="default", timeout_minutes=20):
    """Enqueue an agent run and wait for it; returns the finished run record."""
    body = {"kind": kind, "preset": preset}
    if job_id:
        body["job_id"] = job_id
    queued = api("POST", "/api/v2/agents/run", body)
    run_id = queued["id"]
    log(f"Started {kind}" + (f" ({preset})" if kind == "discovery" else "") + f" run {run_id}")
    deadline = time.monotonic() + timeout_minutes * 60
    while time.monotonic() < deadline:
        time.sleep(15)
        runs = api("GET", "/api/v2/agents").get("runs", [])
        record = next((r for r in runs if r.get("id") == run_id), None)
        if record is None:
            continue
        state = record.get("state")
        if state == "completed":
            return record
        if state == "failed":
            raise ApiError(f"{kind} run failed: {record.get('error') or 'no error recorded'}")
    raise ApiError(f"{kind} run did not finish within {timeout_minutes} minutes")


def usage_limited(error):
    return "usage limit" in str(error).lower()


def list_jobs():
    output = subprocess.run(
        [str(VENV_PY), str(SCRIPTS / "career.py"), "jobs"],
        capture_output=True, text=True, timeout=120,
    )
    if output.returncode:
        raise ApiError("career.py jobs failed: " + output.stderr[-800:])
    return json.loads(output.stdout)


def validate_resume(folder):
    """Compile + validate; returns (ok, note).

    'ok' means the PDF compiled to exactly one page. The validator also hard-fails
    on the placeholder evidence map that prepare() writes (role eligibility and
    requirement review stay pending until reviewed) and on the pending visual
    review — those are Annie's Assurance-tab steps, not morning-run failures.
    """
    tex = folder / "resume.tex"
    if not tex.exists():
        return False, "resume.tex missing"
    command = [
        str(VENV_PY), str(SCRIPTS / "validate_resume.py"), str(tex),
        "--compile", "--output", str(folder / "resume.pdf"),
        "--render-dir", str(folder / "resume-preview"),
        "--qa-json", str(folder / "qa.json"),
    ]
    evidence_map = folder / "evidence-map.yml"
    if evidence_map.exists():
        command += ["--evidence-map", str(evidence_map)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    qa_path = folder / "qa.json"
    qa = None
    if qa_path.exists():
        try:
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
        except ValueError:
            qa = None
    if qa:
        if not qa.get("compile_ok"):
            return False, "the PDF did not compile — open the folder and check resume.tex"
        if qa.get("page_count") != 1:
            return False, f"the resume is {qa.get('page_count')} pages instead of one"
        if result.returncode:
            return True, "one-page PDF compiled; evidence-map and visual review still pending (Assurance tab)"
        return True, ""
    if result.returncode:
        return False, (result.stderr + result.stdout)[-600:]
    return True, ""


def main():
    if "--check" in sys.argv:
        # Plumbing test for the scheduled task: prove the wrapper, interpreter and
        # paths work without spending any AI calls.
        log("Morning-run self-check")
        log("venv python: " + ("found" if VENV_PY.exists() else "MISSING at " + str(VENV_PY)))
        log("dashboard: " + ("running on " + BASE_URL if server_health() else "not running (would be started by a real run)"))
        log("today: " + TODAY + " · log: " + str(LOG_FILE))
        return 0 if VENV_PY.exists() else 1
    started = time.monotonic()
    log(f"=== Morning run for {TODAY} ===")
    REPORT_DIR.mkdir(exist_ok=True)

    ensure_server()

    try:
        aged = api("POST", "/api/v2/jobs/age")
        log(f"Ghosted check done ({aged.get('ghosted', 0)} newly ghosted).")
    except ApiError as error:
        log("Ghosted check skipped: " + str(error))

    before = {job["id"] for job in list_jobs()}
    failures = []
    discovery_notes = []

    goal_met = False
    for preset, minutes in (("portals", 15), ("balanced_five", 25)):
        if goal_met:
            break
        try:
            record = run_agent("discovery", preset=preset, timeout_minutes=minutes)
            result = record.get("result") or {}
            added = result.get("added_job_ids") or []
            note = f"Discovery ({preset}): {len(added)} new job(s) saved."
            shortages = result.get("balanced_shortages") or []
            rejected = result.get("rejected_leads") or []
            if shortages:
                note += " Mix shortfall: " + " ".join(shortages)
            if rejected and not added:
                note += f" {len(rejected)} lead(s) were turned away by the gates (see Dashboard → Rejected leads)."
            discovery_notes.append(note)
            log(note)
        except ApiError as error:
            if "daily application target is complete" in str(error).lower():
                log("Today's application target is already met; discovery finished.")
                goal_met = True
                continue
            log(f"Discovery ({preset}) did not complete: {error}")
            failures.append(f"Discovery ({preset}): {error}")
            if preset == "balanced_five" and usage_limited(error):
                log("The AI usage limit is reached; waiting 20 minutes and trying once more.")
                time.sleep(20 * 60)
                try:
                    run_agent("discovery", preset=preset, timeout_minutes=minutes)
                    failures.pop()
                except ApiError as retry:
                    log("Retry also failed: " + str(retry))

    new_ids = {job["id"] for job in list_jobs() if job["id"] not in before}
    if not new_ids:
        log("No new jobs were discovered today.")
    # Also pick up discovered jobs that were never prepared (e.g. an earlier run stopped midway).
    jobs = [
        job for job in list_jobs()
        if job["id"] in new_ids or (job.get("status") == "saved" and not job.get("folder"))
    ][:5]
    log(f"{len(jobs)} new job(s) to tailor: " + (", ".join(j["company"] for j in jobs) or "none"))

    results = []
    for job in jobs:
        job_id = job["id"]
        entry = {"job": job, "tailored": None, "study_plan": False, "pdf": False, "notes": []}
        log(f"--- {job['company']} — {job['title']} ---")
        try:
            tailored = api("POST", f"/api/v2/studio/{job_id}/tailor", timeout=1800)
            counts = tailored.get("items", {})
            entry["tailored"] = counts
            log(f"Tailored: {counts.get('verified', 0)} verified + {counts.get('predicted', 0)} predicted items (review in Assurance).")
        except ApiError as error:
            entry["notes"].append("Tailoring failed; the deterministic draft is still in the folder. " + str(error))
            log("Tailoring failed: " + str(error))
            if usage_limited(error):
                entry["notes"].append("AI usage limit reached; re-run Tailor from the dashboard later.")
        try:
            run_agent("study_plan", job_id=job_id, timeout_minutes=20)
            entry["study_plan"] = True
            log("Study plan written.")
        except ApiError as error:
            entry["notes"].append("Study plan failed: " + str(error))
            log("Study plan failed: " + str(error))
        job = next((j for j in list_jobs() if j["id"] == job_id), job)
        entry["job"] = job
        if job.get("folder"):
            folder = APP_ROOT / job["folder"]
            ok, note = validate_resume(folder)
            entry["pdf"] = ok
            previews = sorted(folder.glob("studio/preview-*/resume.pdf"))
            if previews:
                entry["preview_pdf"] = str(previews[-1].relative_to(APP_ROOT))
            if ok:
                log("Resume ready: one-page PDF compiled." + (" " + note if note else ""))
            else:
                log("Resume problem: " + note)
            if note:
                entry["notes"].append(note)
        else:
            entry["notes"].append("No application folder was created.")
        results.append(entry)

    try:
        subprocess.run([str(VENV_PY), str(SCRIPTS / "workspace.py"), "export"],
                       capture_output=True, text=True, timeout=300)
        log("Dashboard projections regenerated.")
    except (OSError, subprocess.TimeoutExpired) as error:
        log("Projection export failed: " + str(error))

    if results:
        history = DAILY_DIR / "history.csv"
        with history.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for entry in results:
                job = entry["job"]
                writer.writerow([TODAY, job["company"], job["title"], job["url"],
                                 job.get("requisition_id", ""), job.get("location", ""),
                                 "prepared", job.get("folder", "")])

    lines = [f"# Morning report — {TODAY}", ""]
    if not results:
        lines += ["No new jobs were saved today.", ""]
        for note in discovery_notes:
            lines.append(f"- {note}")
        lines += ["",
                  "The gates only save verified, eligible postings — a quiet morning means the honest search "
                  "found nothing that passed, not that the run broke. Open the dashboard for the rejected-lead reasons, "
                  "or run Daily Search by hand.", ""]
    for entry in results:
        job = entry["job"]
        counts = entry["tailored"] or {}
        folder = entry["job"].get("folder") or ""
        lines.append(f"## {job['company']} — {job['title']}")
        lines.append(f"- Location: {job.get('location', '')} · Fit: {job.get('fit_score') or 'not scored'}")
        lines.append(f"- Apply: {job['url']}")
        if folder:
            pdf = entry.get("preview_pdf") or (folder + "/resume.pdf (appears after the Assurance review passes)")
            lines.append(f"- Resume PDF: `{pdf}` (also: dashboard → Resume Studio → Download) · Study plan: {'yes' if entry['study_plan'] else 'no'}")
        if counts:
            lines.append(f"- Tailored: {counts.get('verified', 0)} verified items, "
                         f"{counts.get('predicted', 0)} predicted — open the Assurance tab and keep/remove before applying.")
        for note in entry["notes"]:
            lines.append(f"- ⚠ {note}")
        lines.append("")
    if failures:
        lines += ["## Problems", ""] + [f"- {failure}" for failure in failures] + [""]
    lines.append("Nothing has been submitted anywhere. Review each resume, then apply through the posting link.")
    report = REPORT_DIR / "MORNING-REPORT.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    log("Report written to " + str(report))

    minutes = (time.monotonic() - started) / 60
    log(f"=== Done in {minutes:.1f} minutes: {len(results)} job(s) prepared, {len(failures)} problem(s) ===")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as error:  # never leave a silent scheduled task
        log("Morning run stopped unexpectedly: " + repr(error))
        sys.exit(1)
