param(
    [string]$Version = "",
    [switch]$Deep,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildRoot = Join-Path $ProjectRoot "build"
$PackageJsonPath = Join-Path $ProjectRoot "desktop\package.json"

if (-not $Version) {
    $PackageJson = Get-Content -LiteralPath $PackageJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $Version = [string]$PackageJson.version
}

if (-not (Test-Path -LiteralPath $BuildRoot)) {
    Write-Host "No build directory: $BuildRoot"
    return
}

$BuildRootResolved = (Resolve-Path -LiteralPath $BuildRoot).Path
$KeepNames = @(
    "open-source-full-v$Version",
    "personal-v$Version",
    "commercial-v$Version"
)

if (-not $Deep) {
    $KeepNames += @("pyinstaller")
}

$Candidates = Get-ChildItem -LiteralPath $BuildRoot -Force |
    Where-Object {
        $_.PSIsContainer -and
        ($KeepNames -notcontains $_.Name) -and
        (
            $_.Name -like "install-test-v*" -or
            $_.Name -like "commercial-lite-v*" -or
            $_.Name -like "open-source-full-v*" -or
            $_.Name -like "personal-v*" -or
            $_.Name -like "commercial-v*" -or
            $_.Name -like "bdist.*" -or
            $_.Name -eq "backup-test" -or
            $_.Name -eq "platform-login-smoke" -or
            $_.Name -eq "lib" -or
            ($Deep -and $_.Name -eq "pyinstaller")
        )
    }

foreach ($Item in $Candidates) {
    $Resolved = (Resolve-Path -LiteralPath $Item.FullName).Path
    if (-not $Resolved.StartsWith($BuildRootResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside build root: $Resolved"
    }
    if ($WhatIf) {
        Write-Host "Would remove: $Resolved"
    } else {
        Remove-Item -LiteralPath $Resolved -Recurse -Force
        Write-Host "Removed: $Resolved"
    }
}

if (-not $Candidates) {
    Write-Host "No stale build outputs found."
}
