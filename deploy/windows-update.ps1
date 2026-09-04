# ============================================================
# Clarity POS - Windows Update Script
#
# Pulls the latest Docker image and updates the POS installation.
#
# Client usage:
#     .\windows-update.ps1
#
# No version number is required from the client.
# The application always uses the :latest image.
# ============================================================

param(
    [string]$AppPath = "C:\pos-app"
)

$ErrorActionPreference = "Stop"

# ============================================================
# Configuration
# ============================================================

$ComposeFile = "docker-compose.prod.yml"
$ContainerName = "pos-app"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       CLARITY POS SYSTEM UPDATE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)"
Write-Host ""

# ============================================================
# Change to application directory
# ============================================================

if (-not (Test-Path $AppPath)) {
    Write-Host "Application directory not found:" -ForegroundColor Red
    Write-Host $AppPath -ForegroundColor Red
    exit 1
}

Set-Location $AppPath

Write-Host "Application directory:" -ForegroundColor Gray
Write-Host $AppPath
Write-Host ""

# ============================================================
# Validate required files
# ============================================================

if (-not (Test-Path ".env")) {
    Write-Host ".env file not found!" -ForegroundColor Red
    Write-Host "Please create .env from .env.example." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $ComposeFile)) {
    Write-Host "Docker Compose file not found:" -ForegroundColor Red
    Write-Host "$AppPath\$ComposeFile" -ForegroundColor Red
    exit 1
}

Write-Host "Configuration files found." -ForegroundColor Green
Write-Host ""

# ============================================================
# Determine Docker registry
# ============================================================

$registry = "tinashemp"

# Read DOCKER_REGISTRY from .env if present
$envLines = Get-Content ".env"

foreach ($line in $envLines) {

    $line = $line.Trim()

    if ($line -match '^DOCKER_REGISTRY\s*=\s*(.*)$') {

        $value = $matches[1].Trim()

        # Remove surrounding quotes
        $value = $value.Trim('"').Trim("'")

        if ($value) {
            $registry = $value
        }

        break
    }
}

$Image = "$registry/clarity-pos:latest"

Write-Host "Docker image:" -ForegroundColor Gray
Write-Host $Image
Write-Host ""

# ============================================================
# Pull latest image
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Pulling latest application image..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

docker pull $Image

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to pull the latest image." -ForegroundColor Red
    Write-Host "The current installation has NOT been changed." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Latest image downloaded successfully." -ForegroundColor Green
Write-Host ""

# ============================================================
# Update application
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Updating application container..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# IMPORTANT:
# We deliberately do NOT run:
#
#     docker compose down
#
# because PostgreSQL does not need to be stopped during
# an application update.

docker compose -f $ComposeFile up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to start the updated application." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Application container started." -ForegroundColor Green
Write-Host ""

# ============================================================
# Wait for container
# ============================================================

Write-Host "Waiting for application container..." -ForegroundColor Cyan

$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {

    $attempt++

    $running = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null

    if ($running -eq "true") {
        Write-Host "Application container is running." -ForegroundColor Green
        break
    }

    Write-Host "Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray

    Start-Sleep -Seconds 2
}

if ($attempt -ge $maxAttempts -and $running -ne "true") {

    Write-Host ""
    Write-Host "ERROR: Application container did not start." -ForegroundColor Red
    Write-Host ""
    Write-Host "Recent container logs:" -ForegroundColor Yellow
    docker logs $ContainerName --tail 50

    exit 1
}

Write-Host ""

# ============================================================
# Wait for PostgreSQL
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Checking database..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

$maxDbAttempts = 30
$dbAttempt = 0
$dbReady = $false

while ($dbAttempt -lt $maxDbAttempts) {

    $dbAttempt++

    $health = docker inspect `
        -f "{{.State.Health.Status}}" `
        "pos-postgres" 2>$null

    if ($health -eq "healthy") {
        $dbReady = $true
        break
    }

    Write-Host "Database status: $health ($dbAttempt/$maxDbAttempts)" -ForegroundColor Gray

    Start-Sleep -Seconds 2
}

if (-not $dbReady) {

    Write-Host ""
    Write-Host "ERROR: PostgreSQL did not become healthy." -ForegroundColor Red
    Write-Host ""
    Write-Host "Database logs:" -ForegroundColor Yellow

    docker logs pos-postgres --tail 50

    exit 1
}

Write-Host "Database is healthy." -ForegroundColor Green
Write-Host ""

# ============================================================
# Run migrations
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Checking database migrations..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

docker exec $ContainerName python manage.py migrate --noinput

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "ERROR: Database migrations failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "The application image has been updated, but the database" -ForegroundColor Yellow
    Write-Host "migration process failed." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check logs with:" -ForegroundColor Yellow
    Write-Host "docker logs $ContainerName --tail 100" -ForegroundColor White

    exit 1
}

Write-Host ""
Write-Host "Database migrations completed successfully." -ForegroundColor Green
Write-Host ""

# ============================================================
# Collect static files
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Collecting static files..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

docker exec $ContainerName python manage.py collectstatic --noinput

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "ERROR: collectstatic failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs with:" -ForegroundColor Yellow
    Write-Host "docker logs $ContainerName --tail 100" -ForegroundColor White

    exit 1
}

Write-Host ""
Write-Host "Static files collected successfully." -ForegroundColor Green
Write-Host ""

# ============================================================
# Final container check
# ============================================================

Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host "Final application check..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

$running = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null

if ($running -ne "true") {

    Write-Host "ERROR: Application container is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Recent logs:" -ForegroundColor Yellow

    docker logs $ContainerName --tail 100

    exit 1
}

Write-Host "Application container is running." -ForegroundColor Green
Write-Host ""

# ============================================================
# Cleanup
# ============================================================

Write-Host "Cleaning unused Docker resources..." -ForegroundColor Cyan

docker image prune -f

Write-Host ""

# ============================================================
# Complete
# ============================================================

Write-Host "========================================" -ForegroundColor Green
Write-Host "       UPDATE COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application: $Image" -ForegroundColor Cyan
Write-Host "URL:         http://localhost:8085" -ForegroundColor Cyan
Write-Host ""
Write-Host "To check application logs:" -ForegroundColor Yellow
Write-Host "docker logs pos-app --tail 50" -ForegroundColor White
Write-Host ""