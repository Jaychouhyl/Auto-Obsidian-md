param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
    throw "File not found: $Path"
}

$Signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $Signtool) {
    $WindowsKits = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($Root in $WindowsKits) {
        if (-not (Test-Path -LiteralPath $Root)) { continue }
        $Candidate = Get-ChildItem -LiteralPath $Root -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($Candidate) {
            $Signtool = $Candidate
            break
        }
    }
}

if (-not $Signtool) {
    throw "signtool.exe was not found. Install Windows SDK and rerun signing."
}

$CertPath = $env:WINDOWS_SIGN_CERT_PATH
$CertPassword = $env:WINDOWS_SIGN_CERT_PASSWORD
$CertThumbprint = $env:WINDOWS_SIGN_CERT_THUMBPRINT

if ($CertPath) {
    if (-not (Test-Path -LiteralPath $CertPath)) {
        throw "WINDOWS_SIGN_CERT_PATH does not exist: $CertPath"
    }
    if (-not $CertPassword) {
        throw "WINDOWS_SIGN_CERT_PASSWORD is required when WINDOWS_SIGN_CERT_PATH is set."
    }
    & $Signtool sign /f $CertPath /p $CertPassword /fd SHA256 /tr $TimestampUrl /td SHA256 $Path
} elseif ($CertThumbprint) {
    & $Signtool sign /sha1 $CertThumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 $Path
} else {
    throw "No signing certificate configured. Set WINDOWS_SIGN_CERT_PATH + WINDOWS_SIGN_CERT_PASSWORD, or WINDOWS_SIGN_CERT_THUMBPRINT."
}

& $Signtool verify /pa /v $Path
Write-Host "Signed and verified: $Path"
