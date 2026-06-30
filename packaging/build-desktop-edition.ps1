param(
    [ValidateSet("community", "commercial", "personal")]
    [string]$Edition = "community",
    [string]$Python = "D:\python\python.exe",
    [switch]$SkipSidecar,
    [switch]$Sign
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DesktopRoot = Join-Path $ProjectRoot "desktop"
$TauriRoot = Join-Path $DesktopRoot "src-tauri"
$ConfigPath = Join-Path $TauriRoot "tauri.conf.json"
$PackageJsonPath = Join-Path $DesktopRoot "package.json"
$OriginalConfig = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
$PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Version = [string]$PackageJson.version

if (Test-Path -LiteralPath "D:\nodejs") {
    $env:Path = "D:\nodejs;$env:Path"
}
if (Test-Path -LiteralPath "$env:USERPROFILE\.cargo\bin") {
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
}

function Join-Chars {
    param([int[]]$CodePoints)
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

$CommercialLabel = Join-Chars @(0x5546, 0x4E1A, 0x7248)
$CommunityLabel = Join-Chars @(0x5F00, 0x6E90, 0x5B8C, 0x6574, 0x7248)
$PersonalLabel = Join-Chars @(0x4E2A, 0x4EBA, 0x7248)

$EditionConfig = if ($Edition -eq "commercial") {
    @{
        ProductName = "Knowledge Studio"
        WindowTitle = "Knowledge Studio"
        Identifier = "com.local.knowledgestudio"
        EnvEdition = "commercial"
        OutputDir = Join-Path $ProjectRoot "build\commercial-v$Version"
        AppFile = "Knowledge Studio $CommercialLabel.exe"
        InstallerFile = "Knowledge Studio ${CommercialLabel}_${Version}_x64-setup.exe"
    }
} elseif ($Edition -eq "personal") {
    @{
        ProductName = "Knowledge Studio"
        WindowTitle = "Knowledge Studio"
        Identifier = "com.local.knowledgestudio.personal"
        EnvEdition = "personal"
        OutputDir = Join-Path $ProjectRoot "build\personal-v$Version"
        AppFile = "Knowledge Studio $PersonalLabel.exe"
        InstallerFile = "Knowledge Studio ${PersonalLabel}_${Version}_x64-setup.exe"
    }
} else {
    @{
        ProductName = "Ingest Studio"
        WindowTitle = "Ingest Studio"
        Identifier = "com.local.ingeststudio"
        EnvEdition = ""
        OutputDir = Join-Path $ProjectRoot "build\open-source-full-v$Version"
        AppFile = "Ingest Studio $CommunityLabel.exe"
        InstallerFile = "Ingest Studio ${CommunityLabel}_${Version}_x64-setup.exe"
    }
}

function Write-TauriConfig {
    param([hashtable]$EditionConfig)
    $Config = $OriginalConfig | ConvertFrom-Json
    $Config.productName = $EditionConfig.ProductName
    $Config.identifier = $EditionConfig.Identifier
    $Config.app.windows[0].title = $EditionConfig.WindowTitle
    Write-Utf8NoBom -Path $ConfigPath -Text ($Config | ConvertTo-Json -Depth 20)
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Text
    )
    $Encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $Encoding)
}

try {
    Write-TauriConfig -EditionConfig $EditionConfig
    if ($EditionConfig.EnvEdition) {
        $env:VITE_APP_EDITION = $EditionConfig.EnvEdition
    } else {
        Remove-Item Env:VITE_APP_EDITION -ErrorAction SilentlyContinue
    }

    if (-not $SkipSidecar) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build-sidecar.ps1") -Python $Python
        if ($LASTEXITCODE -ne 0) {
            throw "sidecar build failed with exit code $LASTEXITCODE"
        }
    }

    Push-Location $DesktopRoot
    try {
        & npm.cmd run tauri build
        if ($LASTEXITCODE -ne 0) {
            throw "tauri build failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }

    $OutputDir = [string]$EditionConfig.OutputDir
    if (Test-Path -LiteralPath $OutputDir) {
        Remove-Item -LiteralPath $OutputDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

    $BuiltExe = Join-Path $TauriRoot "target\release\desktop.exe"
    $BundleDir = Join-Path $TauriRoot "target\release\bundle\nsis"
    $BuiltInstaller = Get-ChildItem -LiteralPath $BundleDir -Filter "*.exe" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not (Test-Path -LiteralPath $BuiltExe)) {
        throw "Desktop executable was not produced: $BuiltExe"
    }
    if (-not $BuiltInstaller) {
        throw "NSIS installer was not produced in $BundleDir"
    }

    $AppTarget = Join-Path $OutputDir ([string]$EditionConfig.AppFile)
    $InstallerTarget = Join-Path $OutputDir ([string]$EditionConfig.InstallerFile)
    $SidecarSource = Join-Path $TauriRoot "binaries\obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"
    $SidecarTarget = Join-Path $OutputDir "obsidian-ingest-backend-x86_64-pc-windows-msvc.exe"
    $WorkspaceTarget = Join-Path $OutputDir "workspace"
    Copy-Item -LiteralPath $BuiltExe -Destination $AppTarget -Force
    Copy-Item -LiteralPath $BuiltInstaller.FullName -Destination $InstallerTarget -Force
    if (-not (Test-Path -LiteralPath $SidecarSource)) {
        throw "Sidecar executable was not found: $SidecarSource"
    }
    Copy-Item -LiteralPath $SidecarSource -Destination $SidecarTarget -Force
    New-Item -ItemType Directory -Force -Path $WorkspaceTarget | Out-Null
    Set-Content -LiteralPath (Join-Path $WorkspaceTarget "README.txt") -Encoding UTF8 -Value @(
        "Portable workspace for this app copy.",
        "Config, queue data, cache, and account sessions are created here after first launch.",
        "This folder is intentionally empty in a fresh package."
    )

    if ($Sign) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "sign-windows.ps1") -Path $AppTarget
        if ($LASTEXITCODE -ne 0) {
            throw "signing failed for $AppTarget"
        }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "sign-windows.ps1") -Path $InstallerTarget
        if ($LASTEXITCODE -ne 0) {
            throw "signing failed for $InstallerTarget"
        }
    }

    Write-Host "Built $Edition package:"
    Write-Host "  $AppTarget"
    Write-Host "  $InstallerTarget"
} finally {
    Write-Utf8NoBom -Path $ConfigPath -Text $OriginalConfig
    Remove-Item Env:VITE_APP_EDITION -ErrorAction SilentlyContinue
}
