#!/usr/bin/env pwsh

# Script to run the play duration accuracy test in the existing Docker development environment
Write-Host "SODAV Monitor - Running Play Duration Accuracy Test in Docker" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green

# Check if Docker is running
try {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker is running." -ForegroundColor Green
} catch {
    Write-Host "Error checking Docker status: $_" -ForegroundColor Red
    exit 1
}

# Get the root directory of the project
$rootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $rootDir

# Check if containers are running
$containersRunning = docker ps --format "{{.Names}}" | Select-String -Pattern "sodav-backend"
if (-not $containersRunning) {
    Write-Host "SODAV containers are not running. Starting them now..." -ForegroundColor Yellow

    # Start the Docker environment
    & "$rootDir\start-docker.ps1"

    # Wait for containers to be ready
    Write-Host "Waiting for containers to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
} else {
    Write-Host "SODAV containers are already running." -ForegroundColor Green
}

# Execute the play duration accuracy test in the backend container
Write-Host "Running play duration accuracy test in the backend container..." -ForegroundColor Green
docker exec sodav-backend bash -c "cd /app && python -m pytest backend/tests/integration/test_end_to_end.py::TestEndToEnd::test_play_duration_accuracy -v --log-cli-level=INFO"

Write-Host "Test completed." -ForegroundColor Green
