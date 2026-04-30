$listeners = Get-NetTCPConnection -State Listen -LocalPort 8766 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if (-not $listeners) {
    Write-Host "No Asteria listener found on port 8766."
    return
}

foreach ($targetPid in $listeners) {
    Stop-Process -Id $targetPid -Force
    Write-Host "Stopped Asteria process $targetPid."
}
