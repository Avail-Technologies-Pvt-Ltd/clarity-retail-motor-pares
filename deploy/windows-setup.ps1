# windows-setup.ps1
# Initial setup script for Windows servers
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "POS System Windows Server Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ Please run as Administrator!" -ForegroundColor Red
    exit 1
}

# Check Docker installation
Write-Host "`n📦 Checking Docker installation..." -ForegroundColor Cyan
$dockerCheck = docker --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker not found!" -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Write-Host "After installation, restart this script." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Docker found: $dockerCheck" -ForegroundColor Green

# Install Docker Compose
Write-Host "`n📦 Installing Docker Compose..." -ForegroundColor Cyan
$composePath = "C:\Program Files\Docker\docker-compose.exe"
if (-not (Test-Path $composePath)) {
    Write-Host "Downloading Docker Compose..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/docker/compose/releases/latest/download/docker-compose-Windows-x86_64.exe" -OutFile $composePath
    Write-Host "✅ Docker Compose installed" -ForegroundColor Green
} else {
    Write-Host "✅ Docker Compose already installed" -ForegroundColor Green
}

# Create app directory
Write-Host "`n📁 Creating application directory..." -ForegroundColor Cyan
$AppPath = "C:\pos-app"
if (-not (Test-Path $AppPath)) {
    New-Item -ItemType Directory -Path $AppPath -Force
    Write-Host "✅ Created $AppPath" -ForegroundColor Green
} else {
    Write-Host "✅ $AppPath already exists" -ForegroundColor Green
}

# Create .env file if it doesn't exist
$envFile = "$AppPath\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "`n⚠️  .env file not found!" -ForegroundColor Yellow
    Write-Host "Please copy .env.example to .env and edit with your settings." -ForegroundColor Yellow
    Write-Host "Example: copy .env.example .env" -ForegroundColor Yellow
}

# Setup scheduled task
Write-Host "`n⏰ Setting up scheduled task for auto-updates..." -ForegroundColor Cyan
$taskName = "POS-Auto-Update"
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "⚠️  Scheduled task already exists. Updating..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$AppPath\deploy\windows-update.ps1`" -CompanyName `"CompanyA`" -Tag `"latest`" -AppPath `"$AppPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00AM"  # Runs daily at 3 AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Automatically updates POS application"

Write-Host "✅ Scheduled task created: $taskName" -ForegroundColor Green
Write-Host "   Runs daily at 3:00 AM" -ForegroundColor Yellow

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy your application files to: $AppPath" -ForegroundColor Yellow
Write-Host "2. Create .env file with your settings" -ForegroundColor Yellow
Write-Host "3. Run update manually: .\deploy\windows-update.bat" -ForegroundColor Yellow
Write-Host "4. Check logs at: $AppPath\update.log" -ForegroundColor Yellow