param(
    [string]$Config = "",
    [string]$LinksFile = "",
    [string]$InboxDir = "",
    [int]$Limit = 10,
    [switch]$DouyinFavorites,
    [string]$DouyinUrl = "https://www.douyin.com/user/self?showTab=favorite_collection",
    [switch]$Doctor,
    [switch]$SkipLinks,
    [switch]$SkipInbox,
    [switch]$NoRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$RunPs1 = Join-Path $ProjectRoot "run.ps1"

if (-not $Config) {
    $Config = Join-Path $ProjectRoot "config.toml"
}
if (-not $LinksFile) {
    $LinksFile = Join-Path $ProjectRoot "links.txt"
}
if (-not $InboxDir) {
    $InboxDir = Join-Path $ProjectRoot "inbox"
}

$LogsDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
New-Item -ItemType Directory -Path $InboxDir -Force | Out-Null
if (-not (Test-Path $LinksFile)) {
    New-Item -ItemType File -Path $LinksFile -Force | Out-Null
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogsDir "ingest-batch-$Stamp.log"
Start-Transcript -Path $LogFile -Force | Out-Null

try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
    Write-Host "ProjectRoot: $ProjectRoot"
    Write-Host "Config:      $Config"
    Write-Host "LinksFile:   $LinksFile"
    Write-Host "InboxDir:    $InboxDir"
    Write-Host "Limit:       $Limit"
    Write-Host "LogFile:     $LogFile"
    Write-Host ""

    function Invoke-Ingest {
        param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
        Write-Host ">>> .\run.ps1 $($Args -join ' ')"
        & $RunPs1 @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: .\run.ps1 $($Args -join ' ')"
        }
    }

    if ($Doctor) {
        Invoke-Ingest doctor --config $Config
    }

    if (-not $SkipLinks) {
        $linkLines = Get-Content -Path $LinksFile -Encoding UTF8 -ErrorAction SilentlyContinue |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and -not $_.StartsWith("#") }

        if ($linkLines.Count -gt 0) {
            Invoke-Ingest import-links $LinksFile --config $Config
        } else {
            Write-Host "links.txt is empty; skip link import."
        }
    }

    if (-not $SkipInbox) {
        $supported = @(".txt", ".md", ".srt", ".vtt", ".pdf", ".mp3", ".wav", ".m4a", ".mp4", ".mkv", ".webm", ".mov", ".flac", ".ogg")
        $files = Get-ChildItem -Path $InboxDir -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $supported -contains $_.Extension.ToLowerInvariant() }

        foreach ($file in $files) {
            Invoke-Ingest add $file.FullName --title $file.BaseName --config $Config
        }

        if ($files.Count -eq 0) {
            Write-Host "inbox has no supported files; skip inbox import."
        }
    }

    if ($DouyinFavorites) {
        $sep = "?"
        if ($DouyinUrl.Contains("?")) {
            $sep = "&"
        }
        $runUrl = "$DouyinUrl${sep}obsidian_ingest_run=$Stamp"
        Invoke-Ingest add $runUrl --title "抖音收藏夹定时检查 $Stamp" --config $Config
    }

    if ($NoRun) {
        Write-Host "NoRun enabled; queued/imported sources only."
    } else {
        Invoke-Ingest run --once --limit $Limit --config $Config
    }
} finally {
    Stop-Transcript | Out-Null
    Write-Host "Log written: $LogFile"
}
