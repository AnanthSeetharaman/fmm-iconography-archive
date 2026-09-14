# ==============================================================================
# Five Metal Masonry (FMM) - Kill & Restart Application Server
# ==============================================================================
$ErrorActionPreference = "SilentlyContinue"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  FIVE METAL MASONRY (FMM) - SERVER KILL AND RESTART SCRIPT" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Working Directory: $PSScriptRoot"
Write-Host ""

Write-Host "[1/3] Terminating any existing processes holding port 8000..." -ForegroundColor Yellow

# 1. Kill any process listening on port 8000
$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        if ($procId -gt 0 -and $procId -ne $PID) {
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $pname = if ($p) { $p.ProcessName } else { "Process" }
            Write-Host "  -> Stopping $pname (PID: $procId) on port 8000..." -ForegroundColor Red
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            taskkill /F /PID $procId 2>$null | Out-Null
        }
    }
}

# 2. Kill any lingering python processes running run_app.py
$pyProcs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%' AND CommandLine LIKE '%run_app.py%'" -ErrorAction SilentlyContinue
foreach ($p in $pyProcs) {
    if ($p.ProcessId -ne $PID) {
        Write-Host "  -> Stopping lingering run_app.py (PID: $($p.ProcessId))..." -ForegroundColor Red
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        taskkill /F /PID $p.ProcessId 2>$null | Out-Null
    }
}

# 3. Fallback netstat check
$netstatLines = netstat -ano 2>$null | Select-String ":8000\s+.*LISTENING"
foreach ($line in $netstatLines) {
    $parts = ($line.ToString().Trim() -split '\s+')
    $pidToKill = $parts[-1]
    if ($pidToKill -match '^\d+$' -and [int]$pidToKill -gt 0) {
        Write-Host "  -> Fallback stopping PID $pidToKill..." -ForegroundColor Red
        taskkill /F /PID $pidToKill 2>$null | Out-Null
    }
}

Write-Host ""
Write-Host "[2/3] Verifying port 8000 is released..." -ForegroundColor Yellow
$released = $false
for ($i = 0; $i -lt 10; $i++) {
    $check = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if (-not $check) {
        $released = $true
        break
    }
    Start-Sleep -Milliseconds 500
}

if ($released) {
    Write-Host "  -> Port 8000 is completely free!" -ForegroundColor Green
} else {
    Write-Host "  -> Notice: Continuing startup check..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] Starting FMM Iconography Archive (run_app.py)..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Local Archive URL:  http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Data Studio URL:    http://127.0.0.1:8000/#admin_studio" -ForegroundColor Green
Write-Host "Visual OCR Studio:  http://127.0.0.1:8000/#ocr_studio" -ForegroundColor Green
Write-Host "Interactive Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path $PSScriptRoot
python "$PSScriptRoot\run_app.py"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Server exited with code $LASTEXITCODE." -ForegroundColor Red
    pause
}
