# Registers "Annie Daily Job Search" in Windows Task Scheduler: every day at 07:00,
# catching up at the next logon/wake if 07:00 was missed. Run once, as Annie:
#   powershell -ExecutionPolicy Bypass -File daily-job-search\Install-MorningTask.ps1
# To pause:  Disable-ScheduledTask -TaskName "Annie Daily Job Search"
# To remove: Unregister-ScheduledTask -TaskName "Annie Daily Job Search" -Confirm:$false
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmd = Join-Path $here 'morning-run.cmd'
if (-not (Test-Path $cmd)) { throw "morning-run.cmd not found next to this script." }

$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Daily -At '07:00'
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName 'Annie Daily Job Search' `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Every morning at 7: finds up to 5 eligible jobs and tailors a one-page resume for each, ready in the dashboard (http://127.0.0.1:8010) by 9. Nothing is submitted; Annie reviews and applies." `
    -Force | Out-Null

Write-Host "Scheduled task 'Annie Daily Job Search' installed: daily at 07:00, catches up if missed."
Write-Host "To run it now for a test: Start-ScheduledTask -TaskName 'Annie Daily Job Search'"
