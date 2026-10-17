# FOSSEverything — one-command dev install and launch (Windows, PowerShell).
# Installs uv if missing (uv then provisions the right Python itself), syncs
# dependencies, and runs the app. No pre-existing Python install required.

Write-Host "============================================================"
Write-Host "   FOSSEverything dev setup"
Write-Host "============================================================"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found -- installing it now..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv installation did not put 'uv' on PATH. Open a new terminal and re-run this script."
    exit 1
}

Set-Location $PSScriptRoot

Write-Host "Installing/updating dependencies with uv..."
uv sync
if (-not $?) { exit 1 }

Write-Host "Launching FOSSEverything..."
uv run python main.py @args
