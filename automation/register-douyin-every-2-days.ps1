param(
    [string]$TaskName = "ObsidianIngestDouyinEvery2Days",
    [string]$StartAt = "09:30",
    [int]$Limit = 5,
    [switch]$IncludeLinks,
    [switch]$IncludeInbox
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BatchScript = Join-Path $ScriptDir "run-ingest-batch.ps1"
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

$batchArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$BatchScript`"",
    "-DouyinFavorites",
    "-Limit", $Limit
)

if (-not $IncludeLinks) {
    $batchArgs += "-SkipLinks"
}
if (-not $IncludeInbox) {
    $batchArgs += "-SkipInbox"
}

$action = New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument ($batchArgs -join " ") `
    -WorkingDirectory $ProjectRoot

$trigger = New-ScheduledTaskTrigger -Daily -DaysInterval 2 -At $StartAt

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Every 2 days, enqueue Douyin favorites and run the Obsidian ingest pipeline." `
    -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName"
Write-Host "Runs every 2 days at:     $StartAt"
Write-Host "Batch script:             $BatchScript"
Write-Host "Logs:                     $(Join-Path $ProjectRoot 'logs')"
