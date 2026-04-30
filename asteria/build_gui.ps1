# Asteria Command Station -- GUI Build Script
# Builds the React GUI app for production serving by the Asteria daemon.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$guiAppDir = Join-Path $scriptDir "gui-app"

if (-not (Test-Path (Join-Path $guiAppDir "package.json"))) {
    Write-Host "Error: gui-app/package.json not found. Are you in the asteria directory?" -ForegroundColor Red
    exit 1
}

Push-Location $guiAppDir
try {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    npm install --silent

    Write-Host "Building Asteria Command Station..." -ForegroundColor Cyan
    npx vite build

    Write-Host ""
    Write-Host "Build complete! Output in asteria/gui-app/dist/" -ForegroundColor Green
    Write-Host "The daemon will automatically serve the built app." -ForegroundColor Gray
} finally {
    Pop-Location
}
