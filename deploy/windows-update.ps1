# windows-update.ps1
# Windows PowerShell script to check and apply updates

param(
    [string]$CompanyName = "CompanyA",
    [string]$Tag = "latest",
    [string]$AppPath = "C:\pos-app"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "POS System Update Check - $CompanyName" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to app directory
Set-Location $AppPath

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
    Write-Host "✅ Loaded .env file" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    exit 1
}

# Login to Docker Registry (if using private registry)
if ($env:DOCKER_USERNAME -and $env:DOCKER_PASSWORD) {
    Write-Host "🔐 Logging into Docker registry..." -ForegroundColor Cyan
    $env:DOCKER_PASSWORD | docker login -u $env:DOCKER_USERNAME --password-stdin
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker login failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Docker login successful" -ForegroundColor Green
}

# Set registry and image name
$registry = if ($env:DOCKER_REGISTRY) { $env:DOCKER_REGISTRY } else { "yourusername" }
$imageName = "$registry/pos-app"
$fullImage = "$imageName`:$Tag"

Write-Host "`n📦 Checking image: $fullImage" -ForegroundColor Cyan

# Check current running image
$currentImage = docker inspect --format='{{.Config.Image}}' pos-app-web 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Current image: $currentImage" -ForegroundColor Yellow
} else {
    Write-Host "No running container found" -ForegroundColor Yellow
}

# Pull latest image
Write-Host "`n📦 Checking for updates..." -ForegroundColor Cyan
$pullOutput = docker pull $fullImage 2>&1

if ($pullOutput -match "Image is up to date|Status: Image is up to date") {
    Write-Host "✅ No updates available - latest version already running" -ForegroundColor Green
    exit 0
}

Write-Host "🔄 Updates found! Deploying..." -ForegroundColor Yellow

# Stop old containers
Write-Host "Stopping old containers..." -ForegroundColor Cyan
docker-compose -f docker/docker-compose.prod.yml down

# Start new containers
Write-Host "Starting new containers..." -ForegroundColor Cyan
docker-compose -f docker/docker-compose.prod.yml up -d

# Wait for database
Write-Host "⏳ Waiting for database..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Run migrations
Write-Host "🔄 Running migrations..." -ForegroundColor Cyan
docker-compose -f docker/docker-compose.prod.yml exec web python manage.py migrate --noinput

# Collect static files
Write-Host "📁 Collecting static files..." -ForegroundColor Cyan
docker-compose -f docker/docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Clean up old images
Write-Host "🧹 Cleaning up old images..." -ForegroundColor Cyan
docker system prune -f

Write-Host "`n✅ Update complete!" -ForegroundColor Green
Write-Host "New image: $fullImage" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan

# Log the update
$logEntry = "[$(Get-Date)] Update applied - Image: $fullImage"
Add-Content -Path "$AppPath\update.log" -Value $logEntry