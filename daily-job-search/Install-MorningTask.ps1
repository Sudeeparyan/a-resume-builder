# Registers a daily job-search task in Windows Task Scheduler (per user, no admin rights).
#
# Annie (the default):  "Annie Daily Job Search", every day at 07:00, catching up at the next
#                       logon/wake if 07:00 was missed. Run once, as Annie:
#   powershell -ExecutionPolicy Bypass -File daily-job-search\Install-MorningTask.ps1
#
# Any other profile:    "Career Daily Job Search - <name> (<id>)". The dashboard installs this
#                       one itself when a profile is built (and removes it on Reset or Delete);
#                       this script is for doing it by hand:
#   powershell -ExecutionPolicy Bypass -File daily-job-search\Install-MorningTask.ps1 -Profile srikanth-nadesharam -Time 07:20
#   powershell -ExecutionPolicy Bypass -File daily-job-search\Install-MorningTask.ps1 -Profile srikanth-nadesharam -Remove
#
# To pause Annie's:  Disable-ScheduledTask -TaskName "Annie Daily Job Search"
param(
    [string]$Profile = 'annie',
    [string]$Time = '',
    [string]$Name = '',
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Profile -eq 'annie') {
    $taskName = 'Annie Daily Job Search'
    if ($Remove) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed '$taskName'."
        return
    }
    $cmd = Join-Path $here 'morning-run.cmd'
    if (-not (Test-Path $cmd)) { throw "morning-run.cmd not found next to this script." }
    $action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $here
    if (-not $Time) { $Time = '07:00' }
    $description = "Every morning at ${Time}: finds up to 5 eligible jobs and tailors a one-page resume for each, ready in the dashboard (http://127.0.0.1:8010) by 9. Nothing is submitted; Annie reviews and applies."
} else {
    # Same name the dashboard uses (backend/services/schedule_tasks.py), so either can manage it.
    $existing = Get-ScheduledTask -ErrorAction SilentlyContinue |
        Where-Object { $_.TaskName -like 'Career Daily Job Search - *' -and $_.TaskName.EndsWith("($Profile)") }
    if ($Remove) {
        $existing | Unregister-ScheduledTask -Confirm:$false
        Write-Host "Removed the daily search for profile '$Profile'."
        return
    }
    $existing | Unregister-ScheduledTask -Confirm:$false
    $label = if ($Name) { $Name } else { $Profile }
    $taskName = "Career Daily Job Search - $label ($Profile)"
    $python = Join-Path $here '..\career-dashboard\backend\.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = 'python' }
    $script = Join-Path $here 'morning_run.py'
    $action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" --profile $Profile" -WorkingDirectory $here
    if (-not $Time) { $Time = '07:20' }
    $description = "Every morning at ${Time}: finds eligible jobs for profile $Profile and tailors a resume for each. Nothing is submitted."
}

$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description $description `
    -Force | Out-Null

Write-Host "Scheduled task '$taskName' installed: daily at $Time, catches up if missed."
Write-Host "To run it now for a test: Start-ScheduledTask -TaskName '$taskName'"
