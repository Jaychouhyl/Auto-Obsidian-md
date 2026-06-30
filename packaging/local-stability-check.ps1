param(
    [string]$Python = "D:\python\python.exe",
    [int]$LocalFiles = 20,
    [int]$Links = 20
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$WorkRoot = Join-Path $env:TEMP ("obsidian-ingest-stability-" + [Guid]::NewGuid().ToString("N"))
$Config = Join-Path $WorkRoot "config.toml"
$InputDir = Join-Path $WorkRoot "input"
$VaultDir = Join-Path $WorkRoot "vault"
$LinksFile = Join-Path $WorkRoot "links.txt"

New-Item -ItemType Directory -Force -Path $InputDir, $VaultDir, (Join-Path $WorkRoot "data"), (Join-Path $WorkRoot "cache"), (Join-Path $WorkRoot "logs") | Out-Null

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:PYTHONIOENCODING = "utf-8"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $Encoding)
}

$QueueDb = (Join-Path $WorkRoot "data\queue.sqlite").Replace("\", "\\")
$CacheDir = (Join-Path $WorkRoot "cache").Replace("\", "\\")
$VaultEscaped = $VaultDir.Replace("\", "\\")
$ConfigText = @"
[paths]
queue_db = "$QueueDb"
cache_dir = "$CacheDir"

[obsidian]
mode = "local"
vault_path = "$VaultEscaped"
folder = "Inbox"
rest_base_url = ""
rest_api_key = ""

[tools]
yt_dlp = "yt-dlp"
ffmpeg = "ffmpeg"
douyin_downloader = "douyin-dl"
douyin_config = ""
whisper = "whisper"
funasr = "funasr"
ocr = "builtin"

[llm]
enabled = false
provider = "openai-compatible"
base_url = ""
api_key = ""
model = "deepseek-chat"
language = "zh-CN"

[outputs]
formats = ["markdown", "html", "csv"]
html_dir = "$($WorkRoot.Replace("\", "\\"))\\html"
csv_path = "$($WorkRoot.Replace("\", "\\"))\\index.csv"
notion_token = ""
notion_database_id = ""
notion_title_property = "Name"
notion_api_base = "https://api.notion.com/v1"

[routing]
enabled = true
fallback_folder = "Inbox"
allowed_folders = ["Inbox"]
"@
Write-Utf8NoBom -Path $Config -Text $ConfigText

for ($Index = 1; $Index -le $LocalFiles; $Index++) {
    Write-Utf8NoBom -Path (Join-Path $InputDir ("local-note-$Index.md")) -Text "# Local note $Index`n`nThis is local stability content $Index."
}

$LinkLines = for ($Index = 1; $Index -le $Links; $Index++) {
    "https://example.invalid/stability/$Index"
}
Write-Utf8NoBom -Path $LinksFile -Text (($LinkLines -join "`n") + "`n")

Write-Host "Workspace: $WorkRoot"
& $Python -m obsidian_ingest.cli doctor --json --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "doctor failed" }

& $Python -m obsidian_ingest.cli scan-directory --dir $InputDir --json --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "scan-directory failed" }

& $Python -m obsidian_ingest.cli import-links $LinksFile --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "import-links failed" }

& $Python -m obsidian_ingest.cli run --once --limit $LocalFiles --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "local file processing failed" }

& $Python -m obsidian_ingest.cli diagnostics --json --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "diagnostics failed" }

& $Python -m obsidian_ingest.cli backup --json --config $Config | Out-Host
if ($LASTEXITCODE -ne 0) { throw "backup failed" }

Write-Host "Local stability check passed."
Write-Host "Artifacts kept at: $WorkRoot"
