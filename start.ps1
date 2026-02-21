# Nerdcast Finder - Start Script
# This script starts both backend and frontend in separate terminals

Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host "Starting Nerdcast Finder"
Write-Host "=" -NoNewline; Write-Host ("=" * 59)
Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend and Frontend directories
$backendDir = Join-Path $scriptDir "backend"
$frontendDir = Join-Path $scriptDir "frontend"

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

# Start Backend in a new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; Write-Host '=== NERDCAST FINDER - BACKEND ===' -ForegroundColor Green; python -m app.main"

# Wait a bit before starting frontend
Start-Sleep -Seconds 2

Write-Host "Starting Frontend..." -ForegroundColor Cyan
Write-Host "   Location: http://127.0.0.1:8050" -ForegroundColor Gray
Write-Host ""

# Start Frontend in a new terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; Write-Host '=== NERDCAST FINDER - FRONTEND ===' -ForegroundColor Green; python app.py"

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

