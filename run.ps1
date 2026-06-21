param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:PYTHONIOENCODING = "utf-8"
$FfmpegBin = "D:\tools\ffmpeg\ffmpeg-8.1.1-full_build\bin"
if (Test-Path $FfmpegBin) {
    $env:PATH = $FfmpegBin + ";" + $env:PATH
}
py -3 -m obsidian_ingest @RemainingArgs
