# test-local.ps1
# Complete local testing script

param(
    [string]$TestType = "all"  # all, docker, migrations, health
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🧪 POS System Local Test Suite" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

# Function to print section headers
function Write-Section {
    param([string]$Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

# Function to check if Docker is running
function Test-DockerRunning {
    Write-Section "🔍 Checking Docker"
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not installed or not running!" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        return $false
    }
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
    
    # Check if Docker daemon is running
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker daemon is not running!" -ForegroundColor Red
        Write-Host "   Please start Docker Desktop" -ForegroundColor Yellow
        return $false
    }
    Write-Host "✅ Docker daemon is running" -ForegroundColor Green
    return $true
}

# Function to test Docker build
function Test-DockerBuild {
    Write-Section "📦 Testing Docker Build"
    
    Write-Host "Building production Docker image..." -ForegroundColor Yellow
    $buildResult = docker build -f docker/Dockerfile.prod -t pos-app-test:latest . 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed!" -ForegroundColor Red
        Write-Host $buildResult -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Docker build successful" -ForegroundColor Green
    
    # Check image size
    $imageSize = docker images pos-app-test:latest --format "{{.Size}}"
    Write-Host "📊 Image size: $imageSize" -ForegroundColor Cyan
    return $true
}

# Function to test Docker Compose
function Test-DockerCompose {
    Write-Section "🐳 Testing Docker Compose"
    
    # Check if docker-compose file exists
    if (-not (Test-Path "docker/docker-compose.prod.yml")) {
        Write-Host "❌ docker-compose.prod.yml not found!" -ForegroundColor Red
        return $false
    }
    Write-Host "✅ docker-compose.prod.yml found" -ForegroundColor Green
    
    # Test compose config
    Write-Host "Validating docker-compose configuration..." -ForegroundColor Yellow
    $composeCheck = docker-compose -f docker/docker-compose.prod.yml config 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker Compose configuration invalid!" -ForegroundColor Red
        Write-Host $composeCheck -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Docker Compose configuration valid" -ForegroundColor Green
    return $true
}

# Function to test container startup
function Test-ContainerStartup {
    Write-Section "🚀 Testing Container Startup"
    
    # Stop any existing test containers
    docker-compose -f docker/docker-compose.test.yml down 2>&1 | Out-Null
    
    Write-Host "Starting containers..." -ForegroundColor Yellow
    $startResult = docker-compose -f docker/docker-compose.test.yml up -d 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Container startup failed!" -ForegroundColor Red
        Write-Host $startResult -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Containers started successfully" -ForegroundColor Green
    
    # Wait for containers to be ready
    Write-Host "⏳ Waiting for containers to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Check container status
    $containerStatus = docker ps --filter "name=pos-app-test" --format "table {{.Names}}\t{{.Status}}"
    Write-Host "`nContainer status:" -ForegroundColor Cyan
    Write-Host $containerStatus -ForegroundColor Yellow
    
    # Check if web container is running
    $webRunning = docker ps --filter "name=pos-app-test-web" --format "{{.Status}}" | Select-String "Up"
    if (-not $webRunning) {
        Write-Host "❌ Web container is not running!" -ForegroundColor Red
        
        # Show logs
        Write-Host "`nWeb container logs:" -ForegroundColor Yellow
        docker logs pos-app-test-web --tail 20
        return $false
    }
    Write-Host "✅ Web container is running" -ForegroundColor Green
    
    return $true
}

# Function to test application health
function Test-ApplicationHealth {
    Write-Section "🏥 Testing Application Health"
    
    # Test if application responds
    Write-Host "Testing application response..." -ForegroundColor Yellow
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/admin/login/" -TimeoutSec 10 -UseBasicParsing -SkipCertificateCheck
        
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Application is responding (Status: $($response.StatusCode))" -ForegroundColor Green
        } elseif ($response.StatusCode -eq 302) {
            Write-Host "✅ Application is redirecting (Status: $($response.StatusCode)) - This is normal for login page" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Application responded with status: $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Application is not responding!" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        
        # Show web container logs
        Write-Host "`nWeb container logs:" -ForegroundColor Yellow
        docker logs pos-app-test-web --tail 30
        return $false
    }
    
    # Test static files
    Write-Host "`nTesting static files..." -ForegroundColor Yellow
    try {
        $staticResponse = Invoke-WebRequest -Uri "http://localhost:8000/static/admin/css/base.css" -TimeoutSec 5 -UseBasicParsing -SkipCertificateCheck
        if ($staticResponse.StatusCode -eq 200) {
            Write-Host "✅ Static files are serving correctly" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Static files not found (Status: $($staticResponse.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Static files might not be collected" -ForegroundColor Yellow
        Write-Host "   Run: docker-compose -f docker/docker-compose.test.yml exec web python manage.py collectstatic" -ForegroundColor Cyan
    }
    
    return $true
}

# Function to test database migrations
function Test-Migrations {
    Write-Section "🗄️ Testing Database Migrations"
    
    Write-Host "Running migrations..." -ForegroundColor Yellow
    $migrationResult = docker-compose -f docker/docker-compose.test.yml exec web python manage.py migrate --noinput 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Migrations failed!" -ForegroundColor Red
        Write-Host $migrationResult -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Migrations successful" -ForegroundColor Green
    
    # Show migration status
    Write-Host "`nMigration status:" -ForegroundColor Cyan
    docker-compose -f docker/docker-compose.test.yml exec web python manage.py showmigrations 2>&1 | Select-String -Pattern "\[ \]" -Context 1,0
    
    return $true
}

# Function to test environment variables
function Test-EnvironmentVariables {
    Write-Section "🔐 Testing Environment Variables"
    
    Write-Host "Checking environment variables in container..." -ForegroundColor Yellow
    
    $envVars = @(
        "DJANGO_SETTINGS_MODULE",
        "SECRET_KEY",
        "DEBUG",
        "DB_NAME",
        "DB_USER",
        "DB_HOST"
    )
    
    foreach ($envVar in $envVars) {
        $value = docker exec pos-app-test-web printenv $envVar 2>&1
        if ($LASTEXITCODE -eq 0 -and $value) {
            $displayValue = if ($envVar -eq "SECRET_KEY") { "***hidden***" } else { $value }
            Write-Host "✅ $envVar = $displayValue" -ForegroundColor Green
        } else {
            Write-Host "❌ $envVar is not set" -ForegroundColor Red
        }
    }
}

# Function to test update mechanism
function Test-UpdateMechanism {
    Write-Section "🔄 Testing Update Mechanism"
    
    Write-Host "Testing update script..." -ForegroundColor Yellow
    
    # Check if update script exists
    if (Test-Path "deploy/windows-update.ps1") {
        Write-Host "✅ Update script found" -ForegroundColor Green
        
        # Test script syntax
        $scriptCheck = powershell -Command "& { . 'deploy/windows-update.ps1' -WhatIf }" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Update script syntax is valid" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Update script has syntax issues:" -ForegroundColor Yellow
            Write-Host $scriptCheck -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Update script not found at deploy/windows-update.ps1" -ForegroundColor Red
    }
}

# Function to cleanup test containers
function Test-Cleanup {
    Write-Section "🧹 Cleaning Up Test Containers"
    
    Write-Host "Stopping test containers..." -ForegroundColor Yellow
    docker-compose -f docker/docker-compose.test.yml down -v 2>&1 | Out-Null
    
    Write-Host "Removing test images..." -ForegroundColor Yellow
    docker rmi pos-app-test:latest 2>&1 | Out-Null
    
    Write-Host "✅ Cleanup complete" -ForegroundColor Green
}

# Main test execution
function Run-AllTests {
    Write-Section "🎯 Running Complete Test Suite"
    
    $tests = @(
        @{Name="Docker Running"; Function={Test-DockerRunning}},
        @{Name="Docker Build"; Function={Test-DockerBuild}},
        @{Name="Docker Compose"; Function={Test-DockerCompose}},
        @{Name="Container Startup"; Function={Test-ContainerStartup}},
        @{Name="Environment Variables"; Function={Test-EnvironmentVariables}},
        @{Name="Database Migrations"; Function={Test-Migrations}},
        @{Name="Application Health"; Function={Test-ApplicationHealth}},
        @{Name="Update Mechanism"; Function={Test-UpdateMechanism}}
    )
    
    $passed = 0
    $failed = 0
    
    foreach ($test in $tests) {
        Write-Host "`n▶️  Running test: $($test.Name)" -ForegroundColor Magenta
        $result = & $test.Function
        if ($result -eq $true) {
            $passed++
        } else {
            $failed++
        }
    }
    
    # Summary
    Write-Section "📊 Test Summary"
    Write-Host "Passed: $passed" -ForegroundColor Green
    Write-Host "Failed: $failed" -ForegroundColor Red
    Write-Host "Total: $($passed + $failed)" -ForegroundColor Cyan
    
    if ($failed -eq 0) {
        Write-Host "`n🎉 All tests passed! Ready for client deployment!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "`n⚠️  Some tests failed. Please fix issues before deploying." -ForegroundColor Red
        return $false
    }
}

# Main execution based on TestType
switch ($TestType) {
    "all" {
        Run-AllTests
    }
    "docker" {
        Test-DockerRunning
        Test-DockerBuild
        Test-DockerCompose
    }
    "migrations" {
        Test-DockerRunning
        if (Test-DockerBuild) {
            Test-ContainerStartup
            Test-Migrations
        }
    }
    "health" {
        Test-ApplicationHealth
    }
    "cleanup" {
        Test-Cleanup
    }
    default {
        Write-Host "Invalid test type. Options: all, docker, migrations, health, cleanup" -ForegroundColor Red
    }
}

# Ask if user wants to cleanup after tests
if ($TestType -eq "all" -and (Read-Host "`nCleanup test containers? (y/n)") -eq "y") {
    Test-Cleanup
}