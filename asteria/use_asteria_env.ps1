param(
    [ValidateSet("home", "cmu", "custom")]
    [string]$Profile = "custom",
    [switch]$Show
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$envWinScripts = Join-Path $repoRoot "env-win\Scripts"
$envWinPython = Join-Path $envWinScripts "python.exe"

if (Test-Path $envWinPython) {
    $env:ASTERIA_PYTHON = $envWinPython
    if ($env:PATH -notlike "*$envWinScripts*") {
        $env:PATH = "$envWinScripts;$env:PATH"
    }
}

$env:ASTERIA_REPO_ROOT = $repoRoot
$env:ASTERIA_GUI_URL = "http://127.0.0.1:8766/"
$env:ASTERIA_ACTIVE_PROFILE = $Profile

if ($Show) {
    Write-Host "ASTERIA_REPO_ROOT=$env:ASTERIA_REPO_ROOT"
    Write-Host "ASTERIA_GUI_URL=$env:ASTERIA_GUI_URL"
    Write-Host "ASTERIA_ACTIVE_PROFILE=$env:ASTERIA_ACTIVE_PROFILE"
    if ($env:ROBOT) {
        Write-Host "ROBOT=$env:ROBOT"
    }
}

Write-Host "Asteria environment ready for profile '$Profile'."
Write-Host "GUI: $env:ASTERIA_GUI_URL"
if ($env:ASTERIA_PYTHON) {
    Write-Host "Python: $env:ASTERIA_PYTHON"
}
