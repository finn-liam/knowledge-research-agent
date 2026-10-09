# =====================================================================
# Knowledge Research Agent - one-click dev shutdown
# Stops (if running): Web (5173) -> API (8900) -> Qdrant container
# Usage:
#   Double-click stop-dev.bat
#   or:  powershell -NoProfile -ExecutionPolicy Bypass -File stop-dev.ps1
# Safety: only touches processes VERIFIED as this project (health/page
# fingerprints). A foreign program on the same port is left untouched.
# =====================================================================
$ErrorActionPreference = "Continue"

# Keep in sync with start-dev.ps1
$ApiPort = 8900
$WebPort = 5173

function Write-Step([string]$m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok([string]$m)   { Write-Host "    [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host "    [!] $m" -ForegroundColor Yellow }

function Get-ListeningPid([int]$Port) {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return $c.OwningProcess } else { return $null }
}

function Stop-ProcessTree([int]$ProcId) {
    # /T walks the whole tree (npm -> cmd -> node chains); /F since dev
    # servers do not respond to graceful console closes from taskkill
    taskkill /PID $ProcId /T /F 2>$null | Out-Null
}

function Test-PortReleased([int]$Port) {
    Start-Sleep -Seconds 1
    return -not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "========== Knowledge Research Agent - Dev Shutdown ==========" -ForegroundColor Green

# ---------- 1. Web frontend (Next dev on $WebPort) ----------
$webPid = Get-ListeningPid $WebPort
if ($webPid) {
    $isOurs = $false
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort" -TimeoutSec 3 -UseBasicParsing
        # Next.js fingerprint: dev pages reference /_next/ assets
        $isOurs = ($r.StatusCode -eq 200) -and ($r.Content -match "_next")
    } catch { }
    if ($isOurs) {
        Write-Step "Stopping web frontend (port $WebPort, PID $webPid)..."
        Stop-ProcessTree $webPid
        if (Test-PortReleased $WebPort) { Write-Ok "Web stopped" }
        else { Write-Warn "Port $WebPort still listening - kill it manually: netstat -ano | findstr :$WebPort" }
    } else {
        Write-Warn "Port $WebPort held by a non-Next program (PID $webPid) - left untouched"
    }
} else {
    Write-Ok "Web not running"
}

# ---------- 2. API backend (uvicorn on $ApiPort) ----------
$apiPid = Get-ListeningPid $ApiPort
if ($apiPid) {
    $ours = $false
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 3 -UseBasicParsing
        # Same fingerprint start-dev.ps1 uses to verify our backend
        $ours = ($r.StatusCode -eq 200) -and ($r.Content -match "llm_mode")
    } catch { }
    if ($ours) {
        Write-Step "Stopping API backend (port $ApiPort, PID $apiPid)..."
        Stop-ProcessTree $apiPid
        if (Test-PortReleased $ApiPort) { Write-Ok "API stopped" }
        else { Write-Warn "Port $ApiPort still listening - kill it manually: netstat -ano | findstr :$ApiPort" }
    } else {
        Write-Warn "Port $ApiPort held by another program (PID $apiPid) - left untouched"
    }
} else {
    Write-Ok "API not running"
}

# ---------- 3. Qdrant container ----------
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    $ddBin = "Z:\software\Docker\resources\bin\docker.exe"
    if (Test-Path $ddBin) { $docker = [pscustomobject]@{ Source = $ddBin } }
}
if ($docker) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $running = docker ps --filter "name=infra-qdrant-1" --format "{{.Names}}" 2>$null
        if ($running) {
            Write-Step "Stopping Qdrant container..."
            docker stop infra-qdrant-1 *> $null
            Write-Ok "Qdrant stopped"
        } else {
            Write-Ok "Qdrant not running"
        }
    } else {
        Write-Warn "Docker engine not running - skip Qdrant"
    }
} else {
    Write-Warn "docker not found - skip Qdrant"
}

Write-Host ""
Write-Host "========== Shutdown complete ==========" -ForegroundColor Green
Write-Host ""
