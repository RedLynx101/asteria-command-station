param(
    [ValidateSet("home", "cmu")]
    [string]$Profile,
    [switch]$OpenBrowser,
    [string]$BindHost = "127.0.0.1"
)

$repoRoot = Split-Path -Parent $PSScriptRoot

if ($Profile) {
    . (Join-Path $PSScriptRoot "use_asteria_env.ps1") -Profile $Profile
}

$preferredPython = Join-Path $repoRoot "env-win\Scripts\python.exe"
$activateScript = Join-Path $repoRoot "env-win\Scripts\Activate.ps1"
$pythonExe = if (Test-Path $preferredPython) { $preferredPython } elseif ($env:ASTERIA_PYTHON) { $env:ASTERIA_PYTHON } else { "python" }

$existing = Get-NetTCPConnection -State Listen -LocalPort 8766 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($existing) {
    Write-Host "Asteria already appears to be listening on port 8766 (PID(s): $($existing -join ', '))."
    if ($OpenBrowser) {
        Start-Process "http://127.0.0.1:8766/"
    }
    return
}

if ($BindHost -eq "0.0.0.0") {
    Write-Warning "Asteria will listen on all network interfaces. Use this only on a trusted LAN."
}

if ((Test-Path $preferredPython) -and (Test-Path $activateScript)) {
    # Start the daemon through the venv activation script so Python resolves the env-win packages.
    $launchCommand = "& '$activateScript'; python -m asteria.daemon.server --host '$BindHost'"
    $proc = Start-Process "powershell.exe" `
        -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command', $launchCommand `
        -WorkingDirectory $repoRoot `
        -PassThru
} else {
    $proc = Start-Process $pythonExe `
        -ArgumentList '-m','asteria.daemon.server','--host',$BindHost `
        -WorkingDirectory $repoRoot `
        -PassThru
}

Start-Sleep -Seconds 3
Write-Host "Asteria started with PID $($proc.Id)."
Write-Host "Python: $pythonExe"
Write-Host "Bind host: $BindHost"
Write-Host "Open http://127.0.0.1:8766/"
if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:8766/"
}
