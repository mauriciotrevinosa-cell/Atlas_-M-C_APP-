# Startup script for ARIA Desktop
Write-Host "Launching ARIA Terminal..." -ForegroundColor Cyan

# Define path to app
$AppPath = Join-Path $PSScriptRoot "apps\desktop"
$ElectronPath = Join-Path $AppPath "node_modules\.bin\electron.cmd"

# Check if node_modules exists
if (-not (Test-Path "$AppPath\node_modules")) {
    Write-Host "Installing dependencies (One-time setup)..." -ForegroundColor Yellow
    Set-Location -Path $AppPath
    npm install
}

# Run execution
if (Test-Path $ElectronPath) {
    Set-Location -Path $AppPath
    & $ElectronPath .
} else {
    Write-Host "Error: Electron binary not found." -ForegroundColor Red
    Write-Host "Trying 'npm start' instead..."
    Set-Location -Path $AppPath
    npm start
}
