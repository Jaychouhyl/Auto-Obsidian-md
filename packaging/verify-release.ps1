param(
    [string]$Config = "D:\obsidian-ingest-pipeline\config.toml",
    [string]$Version = "",
    [switch]$RequireSignature
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DesktopRoot = Join-Path $ProjectRoot "desktop"
$PackageJson = Get-Content -LiteralPath (Join-Path $DesktopRoot "package.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $Version) {
    $Version = [string]$PackageJson.version
}

$CommercialDir = Join-Path $ProjectRoot "build\commercial-v$Version"
$PersonalDir = Join-Path $ProjectRoot "build\personal-v$Version"
$CommunityDir = Join-Path $ProjectRoot "build\open-source-full-v$Version"
$Sidecar = Join-Path $ProjectRoot "desktop\src-tauri\binaries\obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"

function Join-Chars {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

$CommercialLabel = Join-Chars @(0x5546, 0x4E1A, 0x7248)
$CommunityLabel = Join-Chars @(0x5F00, 0x6E90, 0x5B8C, 0x6574, 0x7248)
$PersonalLabel = Join-Chars @(0x4E2A, 0x4EBA, 0x7248)
$CommercialApp = Join-Path $CommercialDir "Knowledge Studio $CommercialLabel.exe"
$CommercialInstaller = Join-Path $CommercialDir "Knowledge Studio ${CommercialLabel}_${Version}_x64-setup.exe"
$CommercialPortableSidecar = Join-Path $CommercialDir "obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"
$CommercialWorkspace = Join-Path $CommercialDir "workspace"
$PersonalApp = Join-Path $PersonalDir "Knowledge Studio $PersonalLabel.exe"
$PersonalInstaller = Join-Path $PersonalDir "Knowledge Studio ${PersonalLabel}_${Version}_x64-setup.exe"
$PersonalPortableSidecar = Join-Path $PersonalDir "obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"
$PersonalWorkspace = Join-Path $PersonalDir "workspace"
$CommunityApp = Join-Path $CommunityDir "Ingest Studio $CommunityLabel.exe"
$CommunityInstaller = Join-Path $CommunityDir "Ingest Studio ${CommunityLabel}_${Version}_x64-setup.exe"
$CommunityPortableSidecar = Join-Path $CommunityDir "obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"
$CommunityWorkspace = Join-Path $CommunityDir "workspace"

$Checks = @()
function Add-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:Checks += [pscustomobject]@{
        Name = $Name
        Ok = $Ok
        Detail = $Detail
    }
}

Add-Check "commercial_dir" (Test-Path -LiteralPath $CommercialDir) $CommercialDir
Add-Check "personal_dir" (Test-Path -LiteralPath $PersonalDir) $PersonalDir
Add-Check "community_dir" (Test-Path -LiteralPath $CommunityDir) $CommunityDir
Add-Check "commercial_app" (Test-Path -LiteralPath $CommercialApp) $CommercialApp
Add-Check "commercial_installer" (Test-Path -LiteralPath $CommercialInstaller) $CommercialInstaller
Add-Check "commercial_portable_sidecar" (Test-Path -LiteralPath $CommercialPortableSidecar) $CommercialPortableSidecar
Add-Check "commercial_portable_workspace" (Test-Path -LiteralPath $CommercialWorkspace) $CommercialWorkspace
Add-Check "personal_app" (Test-Path -LiteralPath $PersonalApp) $PersonalApp
Add-Check "personal_installer" (Test-Path -LiteralPath $PersonalInstaller) $PersonalInstaller
Add-Check "personal_portable_sidecar" (Test-Path -LiteralPath $PersonalPortableSidecar) $PersonalPortableSidecar
Add-Check "personal_portable_workspace" (Test-Path -LiteralPath $PersonalWorkspace) $PersonalWorkspace
Add-Check "community_app" (Test-Path -LiteralPath $CommunityApp) $CommunityApp
Add-Check "community_installer" (Test-Path -LiteralPath $CommunityInstaller) $CommunityInstaller
Add-Check "community_portable_sidecar" (Test-Path -LiteralPath $CommunityPortableSidecar) $CommunityPortableSidecar
Add-Check "community_portable_workspace" (Test-Path -LiteralPath $CommunityWorkspace) $CommunityWorkspace
Add-Check "sidecar" (Test-Path -LiteralPath $Sidecar) $Sidecar

if (Test-Path -LiteralPath $Sidecar) {
    $Output = & $Sidecar status --json --config $Config
    $Parsed = $Output | ConvertFrom-Json
    Add-Check "sidecar_status" ($null -ne $Parsed.paths.project_root) $Parsed.paths.project_root
    Add-Check "ocr_config" ($Parsed.tools.ocr -eq "builtin" -or [bool]$Parsed.tools.ocr) "ocr=$($Parsed.tools.ocr)"
}

$Signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
foreach ($File in @(
    $CommercialApp
    $CommercialInstaller
    $PersonalApp
    $PersonalInstaller
    $CommunityApp
    $CommunityInstaller
)) {
    if (-not (Test-Path -LiteralPath $File)) { continue }
    if ($Signtool) {
        & $Signtool verify /pa $File *> $null
        $Signed = $LASTEXITCODE -eq 0
        Add-Check "signature:$([IO.Path]::GetFileName($File))" ($Signed -or -not $RequireSignature) ($(if ($Signed) { "signed: $File" } else { "unsigned: $File" }))
    } else {
        Add-Check "signature:$([IO.Path]::GetFileName($File))" (-not $RequireSignature) "signtool unavailable; run packaging/sign-windows.ps1 after configuring certificate"
    }
}

$Checks | Format-Table -AutoSize
if ($Checks | Where-Object { -not $_.Ok }) {
    exit 1
}
