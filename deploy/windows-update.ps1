# windows-update.ps1
# Run this to update the POS system

param(
    [string]$Tag = "latest",
    [string]$AppPath = "C:\pos-app"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "POS System Update" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Change to app directory
Set-Location $AppPath

# Load .env file
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
    Write-Host "Loaded .env" -ForegroundColor Green
} else {
    Write-Host ".env not found! Please create .env from .env.example" -ForegroundColor Red
    exit 1
}

# Set registry and image name
$registry = if ($env:DOCKER_REGISTRY) { $env:DOCKER_REGISTRY } else { "tinashemp" }
$fullImage = "$registry/clarity-pos`:$Tag"
$composeFile = "docker/docker-compose.prod.yml"

Write-Host ""
Write-Host "Pulling image: $fullImage" -ForegroundColor Cyan
docker pull $fullImage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to pull image!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Restarting containers..." -ForegroundColor Cyan
docker compose -f $composeFile down
docker compose -f $composeFile up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start containers!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for database to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Running migrations..." -ForegroundColor Cyan
docker exec pos-app python manage.py migrate --noinput

if ($LASTEXITCODE -ne 0) {
    Write-Host "Migrations failed! Check logs: docker logs pos-app" -ForegroundColor Yellow
} else {
    Write-Host "Migrations successful" -ForegroundColor Green
}

Write-Host ""
Write-Host "Cleaning up old images..." -ForegroundColor Cyan
docker system prune -f

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Update complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Open http://localhost:8085" -ForegroundColor Cyan
Write-Host ""
Write-Host "To check logs, run: docker logs pos-app --tail 50" -ForegroundColor Yellow