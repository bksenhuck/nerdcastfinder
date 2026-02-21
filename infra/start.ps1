# Nerdcast Finder - Start Script
# This script starts both backend and frontend in separate terminals

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Starting Nerdcast Finder"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Get the script directory (infra/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Project root (one level up from infra/)
$projectRoot = Split-Path -Parent $scriptDir

# Try to find virtual environment
# Option 1: Two levels up (sibling of project root)
$venvParent = Split-Path -Parent $projectRoot
$venvPath = Join-Path $venvParent "venv_nerdcastfinder\Scripts\Activate.ps1"

# Option 2: If not found, try one level up
if (-not (Test-Path $venvPath)) {
    $venvPath = Join-Path $projectRoot "..\venv_nerdcastfinder\Scripts\Activate.ps1"
    $venvPath = [System.IO.Path]::GetFullPath($venvPath)
}

# Option 3: Check if already in PATH (already activated)
$venvActivated = $env:VIRTUAL_ENV -ne $null

# Backend and Frontend directories (in project root)
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

# Check if venv exists or is already activated
if (-not (Test-Path $venvPath) -and -not $venvActivated) {
    Write-Host "Virtual environment not found: $venvPath" -ForegroundColor Red
    Write-Host "Tried locations:" -ForegroundColor Yellow
    Write-Host "  - $venvPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Current directory structure:" -ForegroundColor Yellow
    Write-Host "  Script: $scriptDir" -ForegroundColor Gray
    Write-Host "  Project root: $projectRoot" -ForegroundColor Gray
    Write-Host "  Parent: $venvParent" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Please ensure venv_nerdcastfinder exists or activate it first" -ForegroundColor Yellow
    exit 1
}

# Display venv status
if ($venvActivated) {
    Write-Host "Using activated virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "Virtual environment found: $venvPath" -ForegroundColor Green
}
Write-Host ""

# Check if directories exist
if (-not (Test-Path $backendDir)) {
    Write-Host "Backend directory not found: $backendDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $frontendDir)) {
    Write-Host "Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

Write-Host "Starting Backend API..." -ForegroundColor Cyan
Write-Host "   Location: http://localhost:8000" -ForegroundColor Gray
Write-Host "   Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""

# Prepare activation command
if ($venvActivated) {
    $activateCmd = "Write-Host 'Using already activated venv' -ForegroundColor Yellow"
} elseif (Test-Path $venvPath) {
    $activateCmd = "& '$venvPath'"
} else {
    $activateCmd = "Write-Host 'WARNING: Running without venv!' -ForegroundColor Red"
}

# Start Backend in a new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; $activateCmd; Write-Host '=== NERDCAST FINDER - BACKEND ===' -ForegroundColor Green; python -m backend.app.main"

# Wait a bit before starting frontend
Start-Sleep -Seconds 3

Write-Host "Starting Frontend..." -ForegroundColor Cyan
Write-Host "   Location: http://127.0.0.1:8050" -ForegroundColor Gray
Write-Host ""

# Start Frontend in a new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; $activateCmd; cd '$frontendDir'; Write-Host '=== NERDCAST FINDER - FRONTEND ===' -ForegroundColor Green; python app.py"

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Both servers are starting in separate terminals" -ForegroundColor Green
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://127.0.0.1:8050" -ForegroundColor White
Write-Host ""
Write-Host "Press Enter to close this window (servers will keep running)..." -ForegroundColor Yellow
Read-Host

