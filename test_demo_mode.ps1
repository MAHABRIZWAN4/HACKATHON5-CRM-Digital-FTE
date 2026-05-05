# Test Demo Mode (Windows PowerShell)

Write-Host "Testing Demo Mode Setup..." -ForegroundColor Green
Write-Host ""

# Set demo mode
$env:DISABLE_DB = "true"
Write-Host "✓ DISABLE_DB=true set" -ForegroundColor Green
Write-Host ""

# Start the server
Write-Host "Starting FastAPI server..." -ForegroundColor Yellow
$process = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 7860" -PassThru -NoNewWindow

# Wait for server to start
Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    # Test health endpoint
    Write-Host ""
    Write-Host "Testing /health endpoint..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:7860/health" -Method Get
    $response | ConvertTo-Json

    # Test root endpoint
    Write-Host ""
    Write-Host "Testing / endpoint..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:7860/" -Method Get
    $response | ConvertTo-Json

    # Test dashboard escalations
    Write-Host ""
    Write-Host "Testing /dashboard/escalations endpoint..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:7860/dashboard/escalations" -Method Get
    $response | ConvertTo-Json

    # Test support endpoint
    Write-Host ""
    Write-Host "Testing /support endpoint..." -ForegroundColor Cyan
    $body = @{
        name = "Test User"
        email = "test@example.com"
        subject = "Test"
        message = "Testing demo mode"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "http://localhost:7860/support" -Method Post -Body $body -ContentType "application/json"
    $response | ConvertTo-Json

    Write-Host ""
    Write-Host "✓ Demo mode tests completed!" -ForegroundColor Green
}
finally {
    # Cleanup
    Write-Host ""
    Write-Host "Stopping server..." -ForegroundColor Yellow
    Stop-Process -Id $process.Id -Force
}
