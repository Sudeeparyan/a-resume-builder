"""One Windows scheduled task per profile for the daily job search.

Annie's task ("Annie Daily Job Search", 07:00, installed by
daily-job-search/Install-MorningTask.ps1) is left exactly as it is. Every other
profile gets "Career Daily Job Search - <name>" when its workspace is built,
running `morning_run.py --profile <id>`, which writes that profile's own logs
and MORNING-REPORT.md under profiles/<id>/daily-job-search/. Start times are
staggered 20 minutes apart (07:20, 07:40, ...) so two profiles never compete for
the same AI allowance. Reset and Delete remove the task.

Tasks are per-user (no administrator rights). Off Windows every call is a no-op
that says so. Tests replace `_powershell` so the suite never touches the real
Task Scheduler.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

from backend.paths import APP_ROOT, REPO_ROOT

TASK_PREFIX = "Career Daily Job Search - "
ANNIE_TIME = "07:00"
FIRST_SLOT = "07:20"
STEP_MINUTES = 20


def supported() -> bool:
    # CAREER_NO_SCHEDULED_TASKS=1 keeps a disposable copy of the app (a test run) from
    # registering real tasks that would point at a temporary folder.
    return sys.platform == "win32" and not os.environ.get("CAREER_NO_SCHEDULED_TASKS")


def unsupported_note() -> str:
    if sys.platform != "win32":
        return "Scheduled tasks are only set up on Windows."
    return "Scheduled tasks are switched off for this copy of the app (CAREER_NO_SCHEDULED_TASKS)."


def _quote(value: str) -> str:
    """A PowerShell single-quoted literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _powershell(script: str, timeout: int = 60) -> tuple[int, str]:
    run = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return run.returncode, (run.stdout or "") + (run.stderr or "")


def task_name(profile_id: str, display_name: str = "") -> str:
    label = " ".join(str(display_name or profile_id).split())[:60]
    return f"{TASK_PREFIX}{label} ({profile_id})"


def _find_script(profile_id: str) -> str:
    # Our tasks end with "(<id>)"; matching on that survives a renamed profile.
    return (
        f"Get-ScheduledTask -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.TaskName -like {_quote(TASK_PREFIX + '*')} -and $_.TaskName.EndsWith({_quote('(' + profile_id + ')')}) }}"
    )


def next_slot(taken: list[str]) -> str:
    """The first free start time after Annie's 07:00, 20 minutes apart."""
    used = {ANNIE_TIME, *[t for t in taken if t]}
    slot = datetime.strptime(FIRST_SLOT, "%H:%M")
    for _ in range(60):
        text = slot.strftime("%H:%M")
        if text not in used:
            return text
        slot += timedelta(minutes=STEP_MINUTES)
    return FIRST_SLOT


def install(profile_id: str, display_name: str, at: str) -> dict:
    """Register (or replace) the profile's daily task at `at` (HH:MM, local time)."""
    datetime.strptime(at, "%H:%M")
    name = task_name(profile_id, display_name)
    if not supported():
        return {"installed": False, "task": name, "time": at, "note": unsupported_note()}
    python = APP_ROOT / "backend/.venv/Scripts/python.exe"
    if not python.exists():
        python = sys.executable
    script_path = REPO_ROOT / "daily-job-search/morning_run.py"
    arguments = f'"{script_path}" --profile {profile_id}'
    description = (f"Every morning at {at}: finds eligible jobs for {display_name} and tailors a resume for each, "
                   f"ready in the dashboard. Nothing is submitted; the candidate reviews and applies.")
    script = "\n".join([
        "$ErrorActionPreference = 'Stop'",
        _find_script(profile_id) + " | Unregister-ScheduledTask -Confirm:$false",
        f"$action = New-ScheduledTaskAction -Execute {_quote(python)} -Argument {_quote(arguments)} "
        f"-WorkingDirectory {_quote(REPO_ROOT / 'daily-job-search')}",
        f"$trigger = New-ScheduledTaskTrigger -Daily -At {_quote(at)}",
        "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun "
        "-ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew",
        f"Register-ScheduledTask -TaskName {_quote(name)} -Action $action -Trigger $trigger "
        f"-Settings $settings -Description {_quote(description)} -Force | Out-Null",
    ])
    try:
        code, output = _powershell(script)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"installed": False, "task": name, "time": at, "note": f"Could not reach Task Scheduler: {error}"}
    if code:
        return {"installed": False, "task": name, "time": at, "note": output.strip()[-400:] or "Task Scheduler refused the task."}
    return {"installed": True, "task": name, "time": at, "note": f"Runs every day at {at}."}


def remove(profile_id: str) -> dict:
    """Unregister the profile's task; nothing to do when there is none."""
    if not supported():
        return {"removed": False, "note": unsupported_note()}
    try:
        code, output = _powershell(_find_script(profile_id) + " | Unregister-ScheduledTask -Confirm:$false")
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"removed": False, "note": f"Could not reach Task Scheduler: {error}"}
    return {"removed": code == 0, "note": "" if code == 0 else output.strip()[-400:]}


def set_enabled(profile_id: str, enabled: bool) -> dict:
    if not supported():
        return {"changed": False, "note": unsupported_note()}
    verb = "Enable-ScheduledTask" if enabled else "Disable-ScheduledTask"
    try:
        code, output = _powershell(_find_script(profile_id) + f" | {verb} | Out-Null")
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"changed": False, "note": f"Could not reach Task Scheduler: {error}"}
    return {"changed": code == 0, "note": "" if code == 0 else output.strip()[-400:]}


def status(profile_id: str) -> dict:
    """{'exists', 'task', 'enabled', 'next_run'} for the profile's task."""
    if not supported():
        return {"exists": False, "supported": False}
    script = (
        _find_script(profile_id) + " | Select-Object -First 1 | ForEach-Object { "
        "$info = $_ | Get-ScheduledTaskInfo; "
        "[pscustomobject]@{ task = $_.TaskName; state = [string]$_.State; "
        "next_run = if ($info.NextRunTime) { $info.NextRunTime.ToString('s') } else { '' } } } | ConvertTo-Json -Compress"
    )
    try:
        code, output = _powershell(script)
    except (OSError, subprocess.TimeoutExpired):
        return {"exists": False, "supported": True, "error": "Task Scheduler did not answer"}
    text = output.strip()
    if code or not text.startswith("{"):
        return {"exists": False, "supported": True}
    try:
        found = json.loads(text)
    except json.JSONDecodeError:
        return {"exists": False, "supported": True}
    return {"exists": True, "supported": True, "task": found.get("task"),
            "enabled": found.get("state") != "Disabled", "next_run": found.get("next_run") or None}


def install_for(profiles, profile_id: str) -> dict:
    """Install a ready profile's task at the next free slot and remember it in the registry."""
    profile = profiles.get(profile_id)
    if profile.get("legacy"):
        return {"installed": False, "note": "Annie's own task (Annie Daily Job Search) is managed separately."}
    taken = [(p.get("schedule") or {}).get("time") for p in profiles.list() if p["id"] != profile_id]
    at = (profile.get("schedule") or {}).get("time") or next_slot(taken)
    result = install(profile_id, profile["name"], at)
    profiles.update(profile_id, schedule={"time": at, "enabled": bool(result.get("installed")),
                                          "task": result.get("task"), "note": result.get("note", "")})
    return result
