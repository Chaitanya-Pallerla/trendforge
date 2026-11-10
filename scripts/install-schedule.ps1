<#
.SYNOPSIS
  Register (or remove) a Windows Task Scheduler job that runs scripts\daily.ps1 every day.

.EXAMPLE
  .\scripts\install-schedule.ps1                 # daily at 08:00
  .\scripts\install-schedule.ps1 -At 07:30
  .\scripts\install-schedule.ps1 -Uninstall

.NOTES
  Runs as the current user while logged on (no password stored). If the PC is off or asleep at the
  scheduled time, it runs as soon as possible afterwards.
#>
param(
  [string]$At = '08:00',
  [string]$TaskName = 'TrendForge Daily',
  [switch]$Uninstall
)

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task '$TaskName'."
  return
}

$script = Join-Path $PSScriptRoot 'daily.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
  -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Principal $principal -Description 'TrendForge: collect trends via camofox-browser and push to GitHub' -Force | Out-Null

$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
Write-Host "Scheduled '$TaskName' daily at $At. Next run: $($info.NextRunTime)"
Write-Host "Run it now with:  Start-ScheduledTask -TaskName '$TaskName'"
