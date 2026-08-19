# =====================================================================
# Knowledge Research Agent - one-click dev startup
# Starts (if not already running): Qdrant -> API (8000) -> Web (5173)
# Usage:
#   Double-click start-dev.bat
#   or:  powershell -NoProfile -ExecutionPolicy Bypass -File start-dev.ps1
# Stop a service by closing its console window.
# =====================================================================
$ErrorActionPreference = "Continue"

$Root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ApiDir  = Join-Path $Root "apps\api"
$WebDir  = Join-Path $Root "apps\web"
$InfraDir = Join-Path $Root "infra"

function Write-Step([string]$m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok([string]$m)   { Write-Host "    [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host "    [!] $m" -ForegroundColor Yellow }

function Test-PortListening([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Http([string]$Url, [int]$TimeoutSec) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $r = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host ""
Write-Host "========== Knowledge Research Agent - Dev Startup ==========" -ForegroundColor Green

# ---------- 0. .env ----------
if (-not (Test-Path (Join-Path $ApiDir ".env"))) {
    Copy-Item (Join-Path $ApiDir ".env.example") (Join-Path $ApiDir ".env")
    Write-Warn ".env not found - copied from .env.example (Mock mode, fill API keys later)"
}

# ---------- 1. Locate Python ----------
$pythonCandidates = @(
    "F:\anaconda\envs\ai-knowledge-assistant-311\python.exe",
    (Join-Path $env:USERPROFILE "anaconda3\python.exe"),
    (Join-Path $env:USERPROFILE "miniconda3\python.exe"),
    "C:\ProgramData\anaconda3\python.exe",
    "C:\ProgramData\miniconda3\python.exe"
)
$python = $null
foreach ($c in $pythonCandidates) { if (Test-Path $c) { $python = $c; break } }
if (-not $python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}
if (-not $python) {
    Write-Host "Python 3.11 not found. Install it or add the path to pythonCandidates in start-dev.ps1." -ForegroundColor Red
    exit 1
}
& $python -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warn "fastapi/uvicorn missing in $python - run: pip install -r requirements.txt"
} else {
    Write-Ok "Python: $python"
}

# ---------- 2. Locate npm ----------
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $npm) {
    Write-Host "npm not found. Install Node.js 18+ first." -ForegroundColor Red
    exit 1
}
Write-Ok "npm: $($npm.Source)"

# ---------- 3. Docker / Qdrant ----------
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    $ddBin = "Z:\software\Docker\resources\bin\docker.exe"
    if (Test-Path $ddBin) { $docker = [pscustomobject]@{ Source = $ddBin } }
}
if ($docker) {
    $engOk = $false
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $engOk = $true
        Write-Ok "Docker engine running"
    } else {
        $ddExes = @(
            "Z:\software\Docker\Docker Desktop.exe",
            (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
            (Join-Path $env:LOCALAPPDATA "Docker\Docker Desktop.exe")
        )
        $dd = $ddExes | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($dd) {
            Write-Step "Starting Docker Desktop (waiting for engine)..."
            Start-Process $dd | Out-Null
            for ($i = 0; $i -lt 24; $i++) {
                Start-Sleep -Seconds 5
                docker info *> $null
                if ($LASTEXITCODE -eq 0) { $engOk = $true; break }
            }
            if ($engOk) { Write-Ok "Docker engine ready" }
            else { Write-Warn "Docker engine not ready after 120s - skip Qdrant (KB unavailable)" }
        } else {
            Write-Warn "Docker Desktop not found - skip Qdrant (KB unavailable)"
        }
    }
    if ($engOk) {
        if (-not (Test-PortListening 6333)) {
            $exists = docker ps -a --filter "name=infra-qdrant-1" --format "{{.Names}}" 2>$null
            if ($exists) {
                Write-Step "Starting Qdrant container..."
                docker start infra-qdrant-1 *> $null
            } else {
                Write-Step "Creating Qdrant container (first run)..."
                docker compose -f (Join-Path $InfraDir "docker-compose.yml") up -d qdrant 2>&1 | Out-Null
            }
        }
        if (Wait-Http "http://127.0.0.1:6333/collections" 60) {
            Write-Ok "Qdrant: http://localhost:6333"
        } else {
            Write-Warn "Qdrant not ready - KB features may be unavailable"
        }
    }
} else {
    Write-Warn "docker not found - skip Qdrant (KB needs it, start manually if required)"
}

# ---------- 4. API backend ----------
if (Test-PortListening 8000) {
    Write-Warn "Port 8000 already in use - reusing existing backend"
} else {
    Write-Step "Starting API backend (port 8000)..."
    Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory $ApiDir
    if (Wait-Http "http://127.0.0.1:8000/health" 90) {
        $health = (Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing).Content
        Write-Ok "API ready: $health"
    } else {
        Write-Warn "API not ready after 90s - check the backend window"
    }
}

# ---------- 5. Web frontend ----------
if (Test-PortListening 5173) {
    Write-Warn "Port 5173 already in use - reusing existing frontend"
} else {
    Write-Step "Starting frontend (port 5173)..."
    Start-Process -FilePath $npm.Source -ArgumentList "run", "dev" -WorkingDirectory $WebDir
    if (Wait-Http "http://127.0.0.1:5173" 90) {
        Write-Ok "Frontend ready"
    } else {
        Write-Warn "Frontend not ready after 90s - check the frontend window"
    }
}

Write-Host ""
Write-Host "========== Startup complete ==========" -ForegroundColor Green
Write-Host "  Web  : http://localhost:5173"
Write-Host "  API  : http://localhost:8000  (docs: /docs)"
Write-Host "  Stop : close the corresponding console window"
Write-Host ""
