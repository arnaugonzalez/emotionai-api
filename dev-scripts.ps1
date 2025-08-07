# EmotionAI Full-Stack Development Scripts (PowerShell)

# Configuration
$BACKEND_DIR = "."
$FRONTEND_DIR = "..\emotionai-app"  # Adjust path as needed
$API_URL = "http://localhost:8000"

# Colors for output
function Write-Status($message) {
    Write-Host "[INFO] $message" -ForegroundColor Blue
}

function Write-Success($message) {
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Write-Error-Custom($message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# Start backend services
function Start-Backend {
    Write-Status "Starting backend services..."
    Set-Location $BACKEND_DIR
    docker-compose up -d
    
    # Wait for services to be healthy
    Write-Status "Waiting for services to be ready..."
    Start-Sleep 10
    
    # Check if API is responding
    try {
        $response = Invoke-WebRequest -Uri "$API_URL/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "Backend services are running and healthy!"
        }
    }
    catch {
        Write-Warning "Backend services started but API health check failed"
    }
}

# Stop backend services
function Stop-Backend {
    Write-Status "Stopping backend services..."
    Set-Location $BACKEND_DIR
    docker-compose down
    Write-Success "Backend services stopped"
}

# Create test data
function Create-TestData {
    Write-Status "Creating test data..."
    Set-Location $BACKEND_DIR
    docker-compose exec api python create_test_data.py
    Write-Success "Test data created"
}

# Run Flutter app
function Start-Flutter {
    Write-Status "Starting Flutter app..."
    if (Test-Path $FRONTEND_DIR) {
        Set-Location $FRONTEND_DIR
        flutter run
    }
    else {
        Write-Error-Custom "Flutter app directory not found: $FRONTEND_DIR"
        Write-Warning "Please update FRONTEND_DIR in this script"
    }
}

# Full setup for development
function Initialize-FullSetup {
    Write-Status "Setting up full development environment..."
    
    # Start backend
    Start-Backend
    
    # Create test data
    Start-Sleep 5
    Create-TestData
    
    Write-Success "Full development environment is ready!"
    Write-Status "Backend API: $API_URL"
    Write-Status "Test user: test@emotionai.com / testpass123"
    Write-Status "Now you can run 'Start-Flutter' to start the Flutter app"
}

# Show status of all services
function Show-Status {
    Write-Status "Development environment status:"
    Write-Host ""
    
    # Backend services
    Set-Location $BACKEND_DIR
    Write-Host "Backend Services:"
    docker-compose ps
    Write-Host ""
    
    # API health check
    try {
        $response = Invoke-WebRequest -Uri "$API_URL/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Success "API is responding at $API_URL"
        }
    }
    catch {
        Write-Error-Custom "API is not responding at $API_URL"
    }
    Write-Host ""
    
    # Flutter app check
    if (Test-Path $FRONTEND_DIR) {
        Write-Success "Flutter app directory found: $FRONTEND_DIR"
    }
    else {
        Write-Error-Custom "Flutter app directory not found: $FRONTEND_DIR"
    }
}

# Menu system
function Show-Menu {
    Write-Host ""
    Write-Host "EmotionAI Full-Stack Development Helper" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "1. Full Setup (Backend + Test Data)"
    Write-Host "2. Start Backend Only"
    Write-Host "3. Stop Backend"
    Write-Host "4. Create Test Data"
    Write-Host "5. Run Flutter App"
    Write-Host "6. Show Status"
    Write-Host "7. Exit"
    Write-Host ""
}

# Parameter handling
param(
    [Parameter(Position=0)]
    [string]$Action
)

switch ($Action) {
    "start" { Start-Backend }
    "stop" { Stop-Backend }
    "setup" { Initialize-FullSetup }
    "data" { Create-TestData }
    "flutter" { Start-Flutter }
    "status" { Show-Status }
    default {
        Show-Menu
        $choice = Read-Host "Choose an option (1-7)"
        switch ($choice) {
            "1" { Initialize-FullSetup }
            "2" { Start-Backend }
            "3" { Stop-Backend }
            "4" { Create-TestData }
            "5" { Start-Flutter }
            "6" { Show-Status }
            "7" { exit }
            default { Write-Error-Custom "Invalid option" }
        }
    }
}