<#
.SYNOPSIS
  Clean Windows CLI runner for faceless-shorts (D-drive isolated, RTX 3050 NVENC).
.EXAMPLE
  .\faceless.ps1 doctor
  .\faceless.ps1 create --topic "Why Did the Roman Empire Collapse?" --render
  .\faceless.ps1 create --topic "The Bizarre True Story of the Balloon Boy Hoax" --render
  .\faceless.ps1 create --topic "Can You Survive Jumping Inside a Falling Elevator?" --render
  .\faceless.ps1 create --topic "Why Elevators Have Mirrors" --script "my_script.txt" --style stick-story
  .\faceless.ps1 render "data\2026-11-25\why-did-the-roman-empire-collapse"
#>
$ErrorActionPreference = "Stop"

# Force UTF-8 encoding across console and output
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)

$Root = $PSScriptRoot
$TmpDir = Join-Path $Root ".tmp"
if (-not (Test-Path $TmpDir)) {
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
}

# Force all temp, cache, and Chromium profile paths onto D: so C: is never touched
$env:TEMP = $TmpDir
$env:TMP = $TmpDir
$env:TMPDIR = $TmpDir
$env:FACELESS_HOME = Join-Path $TmpDir "faceless-home"
$env:HF_HOME = Join-Path $TmpDir "hf-cache"
$env:TORCH_HOME = Join-Path $TmpDir "torch-cache"
$env:XDG_CACHE_HOME = Join-Path $TmpDir "cache"

$FfmpegBin = "D:\gem\ffmpeg-2026-11-19-git-01ca75d350-full_build\ffmpeg\bin"
if (Test-Path $FfmpegBin) {
    $env:PATH = "$FfmpegBin;$env:PATH"
}

$PythonExe = "D:\AI-Projects\stream-clips\.streamclips\venv\Scripts\python.exe"
$RunnerPy = Join-Path $Root "scripts\faceless.py"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python venv not found at: $PythonExe"
    exit 1
}

& $PythonExe $RunnerPy @args
exit $LASTEXITCODE
