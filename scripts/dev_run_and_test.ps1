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
$baseUrl = "http://$uvicornHost:$uvicornPort"

if (-not (Test-Path $venvDir)) {
  python -m venv $venvDir | Out-Null
}

$activate = Join-Path $venvDir 'Scripts' 'Activate.ps1'
. $activate

python -m pip install --upgrade pip wheel | Out-Null
if (Test-Path 'requirements-production.txt') {
  python -m pip install --no-cache-dir -r requirements-production.txt
} elseif (Test-Path 'requirements.txt') {
  python -m pip install --no-cache-dir -r requirements.txt
} else {
  python -m pip install --no-cache-dir 'uvicorn[standard]' fastapi
}

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = 'python'
$psi.Arguments = "-m uvicorn main:app --host $uvicornHost --port $uvicornPort"
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$proc = [System.Diagnostics.Process]::Start($psi)

try {
  for ($i = 0; $i -lt 60; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -TimeoutSec 2
      if ($resp.StatusCode -eq 200) {
        Write-Host "Server is up at $baseUrl"
        break
      }
    } catch { }
    Start-Sleep -Seconds 1
    if ($i -eq 59) { throw "Timed out waiting for $baseUrl/health" }
  }

  try {
    $resp = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing
    Write-Host "[health] $($resp.Content)"
  } catch {
    Write-Warning $_
  }

  Write-Host 'Press Ctrl+C to stop, or wait 5 seconds to exit automatically...'
  Start-Sleep -Seconds 5
}
finally {
  if (-not $proc.HasExited) { $proc.Kill() }
}
