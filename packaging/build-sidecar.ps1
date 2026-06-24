param(
    [string]$TargetTriple = "x86_64-pc-windows-msvc",
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BinaryDir = Join-Path $ProjectRoot "desktop\src-tauri\binaries"
$BuildDir = Join-Path $ProjectRoot "build\pyinstaller"
$Name = "obsidian-ingest-backend-$TargetTriple"
$Entry = Join-Path $ProjectRoot "packaging\backend_main.py"

New-Item -ItemType Directory -Force -Path $BinaryDir | Out-Null
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:PYTHONIOENCODING = "utf-8"

[string[]]$PythonCommand = if ($Python) {
    @($Python)
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    @("py", "-3")
} else {
    @("python")
}
$PythonArgs = if ($PythonCommand.Count -gt 1) {
    $PythonCommand[1..($PythonCommand.Count - 1)]
} else {
    @()
}
$PythonExe = $PythonCommand[0]

$PyInstallerArgs = @(
    $PythonArgs
    "-m"
    "PyInstaller"
    "--clean"
    "--onefile"
    "--name"
    $Name
    "--paths"
    (Join-Path $ProjectRoot "src")
    "--collect-all"
    "playwright"
    "--distpath"
    $BinaryDir
    "--workpath"
    $BuildDir
    "--specpath"
    $BuildDir
    $Entry
)

& $PythonExe @PyInstallerArgs

$Output = Join-Path $BinaryDir "$Name.exe"
if (-not (Test-Path -LiteralPath $Output)) {
    throw "Sidecar build did not produce $Output"
}

Write-Host "Built sidecar: $Output"
