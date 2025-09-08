#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

# Local dev runner for EmotionAI API (Windows)
# - Creates/uses a virtualenv (.venv)
# - Starts Uvicorn on 127.0.0.1:8000
# - Waits for /health
# - Executes a few tests

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $repoRoot

$venvDir = if ($env:VENV_DIR) { $env:VENV_DIR } else { '.venv' }
$uvicornHost = if ($env:UVICORN_HOST) { $env:UVICORN_HOST } else { '127.0.0.1' }
$uvicornPort = if ($env:UVICORN_PORT) { $env:UVICORN_PORT } else { '8000' }
$baseUrl = "http://${uvicornHost}:${uvicornPort}"

Write-Host "Setting up virtual environment..."
if (-not (Test-Path $venvDir)) {
  Write-Host "Creating virtual environment..."
  python -m venv $venvDir
}

$activate = Join-Path $venvDir "Scripts\Activate.ps1"
Write-Host "Activating virtual environment..."
& $activate

Write-Host "Installing/upgrading dependencies..."
python -m pip install --upgrade pip wheel
if (Test-Path 'requirements-production.txt') {
  python -m pip install --no-cache-dir -r requirements-production.txt
} elseif (Test-Path 'requirements.txt') {
  python -m pip install --no-cache-dir -r requirements.txt
} else {
  python -m pip install --no-cache-dir 'uvicorn[standard]' fastapi
}

Write-Host "Starting uvicorn server at $baseUrl..."
Write-Host "Press Ctrl+C to stop the server"

# Start uvicorn directly in the foreground
python -m uvicorn main:app --host $uvicornHost --port $uvicornPort --reload
