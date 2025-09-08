#!/usr/bin/env pwsh
# Test script for EmotionAI API endpoints
# Run this while the server is running to test the endpoints

$uvicornHost = if ($env:UVICORN_HOST) { $env:UVICORN_HOST } else { '127.0.0.1' }
$uvicornPort = if ($env:UVICORN_PORT) { $env:UVICORN_PORT } else { '8000' }
$baseUrl = "http://${uvicornHost}:${uvicornPort}"

Write-Host "Testing EmotionAI API at $baseUrl"
Write-Host "=================================="

try {
    Write-Host "Testing health endpoint..."
    $resp = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing
    Write-Host "[✓] Health: $($resp.Content)"
} catch {
    Write-Host "[✗] Health endpoint failed: $($_.Exception.Message)"
    exit 1
}

try {
    Write-Host "Testing root endpoint..."
    $resp = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    Write-Host "[✓] Root: $($resp.Content)"
} catch {
    Write-Host "[✗] Root endpoint failed: $($_.Exception.Message)"
}

try {
    Write-Host "Testing v1 API structure..."
    # Test if endpoints exist (expecting auth required for most)
    $resp = Invoke-WebRequest -Uri "$baseUrl/v1/api/chat" -Method POST -ContentType 'application/json' -Body '{}' -UseBasicParsing
    Write-Host "[✓] v1-api-chat Status: $($resp.StatusCode)"
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 401 -or $statusCode -eq 422) {
        Write-Host "[✓] v1-api-chat Status: $statusCode (expected - needs auth/valid input)"
    } else {
        Write-Host "[✗] v1-api-chat Status: $statusCode (unexpected)"
    }
}

Write-Host ""
Write-Host "API endpoints available at $baseUrl/v1/api/..."
Write-Host "- /health (health check)"
Write-Host "- /v1/api/chat (chat endpoint)"
Write-Host "- /v1/api/breathing (breathing exercises)"
Write-Host "- /v1/api/usage (usage analytics)"
