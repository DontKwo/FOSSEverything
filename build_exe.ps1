<#
.SYNOPSIS
    Builds the standalone FOSSEverything executable using PyInstaller.
.EXAMPLE
    .\build_exe.ps1
    .\build_exe.ps1 -OneFile
#>
param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   FOSSEverything - Standalone Executable Builder" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$argsList = @("scripts/build_executable.py")
if ($OneFile) {
    $argsList += "--onefile"
}

$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if ($uvPath) {
    Write-Host "[INFO] Running test suite (pytest -q)..." -ForegroundColor Green
    & uv run python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Pre-build tests failed. Aborting build."
        exit $LASTEXITCODE
    }
    Write-Host "[INFO] Building with uv..." -ForegroundColor Green
    & uv run python @argsList
} elseif (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "[INFO] Building with .venv\Scripts\python.exe..." -ForegroundColor Green
    & ".venv\Scripts\python.exe" @argsList
} else {
    $pyPath = Get-Command python -ErrorAction SilentlyContinue
    if ($pyPath) {
        Write-Host "[INFO] Building with system python..." -ForegroundColor Green
        & python @argsList
    } else {
        Write-Error "Neither uv nor Python was found. Please install uv (https://astral.sh/uv) or Python 3.11+."
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Build finished successfully! See .\dist folder." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Build failed with exit code $LASTEXITCODE." -ForegroundColor Red
}

