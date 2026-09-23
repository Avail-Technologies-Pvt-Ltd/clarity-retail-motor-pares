# ============================================================
# Clarity POS - Windows Update & Deployment Script
#
# Pulls the latest Docker image and updates the POS installation.
#
# Usage:
#     .\windows-update.ps1
#     .\windows-update.ps1 -AppPath "C:\pos-app"
# ============================================================

param(
    [string]$AppPath = ""
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       CLARITY POS SYSTEM UPDATE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# ============================================================
# Auto-detect Application Directory
# ============================================================

$resolvedPath = ""

if ($AppPath -and (Test-Path $AppPath)) {
    $resolvedPath = (Resolve-Path $AppPath).Path
} elseif (Test-Path ".\docker-compose.prod.yml") {
    $resolvedPath = (Get-Location).Path
} elseif (Test-Path "$PSScriptRoot\..\docker-compose.prod.yml") {
    $resolvedPath = (Resolve-Path "$PSScriptRoot\..").Path
} elseif (Test-Path "$PSScriptRoot\docker-compose.prod.yml") {
    $resolvedPath = (Resolve-Path "$PSScriptRoot").Path
} elseif (Test-Path "C:\pos-app\docker-compose.prod.yml") {
    $resolvedPath = "C:\pos-app"
} elseif (Test-Path "C:\pos-app") {
    $resolvedPath = "C:\pos-app"
}

if (-not $resolvedPath -or -not (Test-Path $resolvedPath)) {
    Write-Host "ERROR: Application directory could not be determined." -ForegroundColor Red
    Write-Host "Expected location: C:\pos-app or current directory with docker-compose.prod.yml" -ForegroundColor Yellow
    exit 1
}

Set-Location $resolvedPath

Write-Host "Application Directory: $resolvedPath" -ForegroundColor Green
Write-Host ""

# ============================================================
# Check Docker Engine Status
# ============================================================

Write-Host "Checking Docker status..." -ForegroundColor Gray
$null = & docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host " ERROR: Docker Desktop is not running or not accessible." -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "Please start Docker Desktop, wait for the engine to start," -ForegroundColor Yellow
    Write-Host "and run update.bat again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host "Docker engine is running." -ForegroundColor Green
Write-Host ""

# ============================================================
# Validate Required Files
# ============================================================

$ComposeFile = "docker-compose.prod.yml"
$ContainerName = "pos-app"

if (-not (Test-Path $ComposeFile)) {
    Write-Host "ERROR: Docker Compose file not found: $resolvedPath\$ComposeFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "WARNING: .env not found. Creating from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env. Please update .env with production credentials if needed." -ForegroundColor Yellow
    } else {
        Write-Host "ERROR: .env file not found in $resolvedPath" -ForegroundColor Red
        Write-Host "Please create a .env file before deploying." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Configuration files verified." -ForegroundColor Green
Write-Host ""

# ============================================================
# Determine Docker Registry and Image
# ============================================================

$registry = "tinashemp"
$tag = "latest"

$envLines = Get-Content ".env"
foreach ($line in $envLines) {
    $line = $line.Trim()
    if ($line -match '^DOCKER_REGISTRY\s*=\s*(.*)$') {
        $val = $matches[1].Trim().Trim('"').Trim("'")
        if ($val) { $registry = $val }
    }
    if ($line -match '^TAG\s*=\s*(.*)$') {
        $val = $matches[1].Trim().Trim('"').Trim("'")
        if ($val) { $tag = $val }
    }
}

$Image = "$registry/clarity-pos:$tag"

Write-Host "Docker Image: $Image" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Pull Latest Image
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Pulling latest application image..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray

docker pull $Image

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: Failed to pull $Image from remote registry." -ForegroundColor Yellow
    Write-Host "Checking if a local image is available..." -ForegroundColor Yellow
    $localCheck = docker images -q $Image 2>$null
    if (-not $localCheck) {
        Write-Host "ERROR: No local or remote image found for $Image." -ForegroundColor Red
        Write-Host "Ensure the GitHub Actions build completed and pushed to Docker Hub," -ForegroundColor Yellow
        Write-Host "or run a local build first." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Found local image $Image. Proceeding with deployment..." -ForegroundColor Yellow
} else {
    Write-Host "Latest image downloaded successfully." -ForegroundColor Green
}
Write-Host ""

# ============================================================
# Deploy / Update Containers
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Applying container updates..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray

docker compose -f $ComposeFile up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to start containers with docker compose." -ForegroundColor Red
    exit 1
}

Write-Host "Containers started." -ForegroundColor Green
Write-Host ""

# ============================================================
# Wait for Database Readiness
# ============================================================

Write-Host "Waiting for database health check..." -ForegroundColor Cyan

$maxDbAttempts = 30
$dbAttempt = 0
$dbReady = $false

while ($dbAttempt -lt $maxDbAttempts) {
    $dbAttempt++
    $health = docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" "pos-postgres" 2>$null

    if ($health -eq "healthy" -or $health -eq "running") {
        $dbReady = $true
        break
    }
    Write-Host "Database status: $health ($dbAttempt/$maxDbAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $dbReady) {
    Write-Host ""
    Write-Host "ERROR: PostgreSQL did not become ready." -ForegroundColor Red
    docker logs pos-postgres --tail 30
    exit 1
}

Write-Host "Database is ready." -ForegroundColor Green
Write-Host ""

# ============================================================
# Wait for Application Container
# ============================================================

Write-Host "Waiting for application container ($ContainerName)..." -ForegroundColor Cyan

$maxAttempts = 30
$attempt = 0
$appRunning = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    $running = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null

    if ($running -eq "true") {
        $appRunning = $true
        break
    }
    Write-Host "Waiting for container start... ($attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $appRunning) {
    Write-Host ""
    Write-Host "ERROR: Application container failed to start." -ForegroundColor Red
    docker logs $ContainerName --tail 50
    exit 1
}

Write-Host "Application container is running." -ForegroundColor Green
Write-Host ""

# ============================================================
# Run Database Migrations
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Verifying database migrations..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray

docker exec $ContainerName python manage.py migrate --noinput

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Migration check reported an issue. Review logs below:" -ForegroundColor Yellow
    docker logs $ContainerName --tail 30
} else {
    Write-Host "Database migrations verified successfully." -ForegroundColor Green
}
Write-Host ""

# ============================================================
# Collect Static Files
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Collecting static files..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray

docker exec $ContainerName python manage.py collectstatic --noinput

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: collectstatic reported an issue." -ForegroundColor Yellow
} else {
    Write-Host "Static files collected successfully." -ForegroundColor Green
}
Write-Host ""

# ============================================================
# Cleanup Old Docker Images
# ============================================================

Write-Host "Cleaning up obsolete Docker images..." -ForegroundColor Gray
docker image prune -f >$null 2>&1

# ============================================================
# Deployment Summary
# ============================================================

Write-Host "============================================================" -ForegroundColor Green
Write-Host "          CLARITY POS UPDATED & DEPLOYED SUCCESSFULLY!       " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Image:       $Image" -ForegroundColor Cyan
Write-Host "  Access URL:  http://localhost:8085" -ForegroundColor Cyan
Write-Host "  Status:      Running" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View live logs:   docker logs -f $ContainerName" -ForegroundColor White
Write-Host "  Stop system:      docker compose -f $ComposeFile down" -ForegroundColor White
Write-Host "  Restart system:   docker compose -f $ComposeFile restart" -ForegroundColor White
Write-Host ""