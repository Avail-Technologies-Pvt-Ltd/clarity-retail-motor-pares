# windows-health-check.ps1
# Check if application is running healthy
# Run this periodically to detect issues

param(
    [string]$AppPath = "C:\pos-app"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "POS System Health Check" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location $AppPath

# Check if containers are running
$containers = docker ps --filter "name=pos-app" --format "{{.Names}} {{.Status}}"

if ($containers) {
    Write-Host "✅ Containers running:" -ForegroundColor Green
    $containers | ForEach-Object { Write-Host "   $_" -ForegroundColor Yellow }
} else {
    Write-Host "❌ No containers running!" -ForegroundColor Red
    Write-Host "Attempting to restart..." -ForegroundColor Yellow
    docker-compose -f docker/docker-compose.prod.yml up -d
    exit 1
}

# Check if web app is responding
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/admin/login/" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Application is responding" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Application returned status: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Application is not responding!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to restart
    Write-Host "Attempting restart..." -ForegroundColor Yellow
    docker-compose -f docker/docker-compose.prod.yml restart web
}

# Check disk space
$disk = Get-PSDrive -Name (Split-Path $AppPath -Qualifier).TrimEnd(':')
if ($disk) {
    $freePercent = [math]::Round(($disk.Free / $disk.Used) * 100, 2)
    if ($freePercent -lt 10) {
        Write-Host "⚠️  Low disk space: $freePercent% free" -ForegroundColor Red
    } else {
        Write-Host "✅ Disk space: $freePercent% free" -ForegroundColor Green
    }
}

Write-Host "`nHealth check complete!" -ForegroundColor Green