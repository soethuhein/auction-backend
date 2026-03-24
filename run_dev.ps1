# Auction Backend - Run all services
# Requires: Redis running
# Use: .\run_dev.ps1 (opens 3 separate terminal windows)

$env:DB_ENGINE = "mysql"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/2"

$root = $PSScriptRoot
$venvPython = Join-Path $root "venv\Scripts\python.exe"

Write-Host "Starting Django (Terminal 1)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; `$env:DB_ENGINE='mysql'; `$env:REDIS_URL='redis://localhost:6379/0'; `$env:CELERY_BROKER_URL='amqp://guest:guest@localhost:5672//'; `$env:CELERY_RESULT_BACKEND='redis://localhost:6379/2'; & '$venvPython' manage.py runserver 0.0.0.0:8000"

Start-Sleep -Seconds 2
Write-Host "Starting Celery Worker -P solo (Terminal 2)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; `$env:DB_ENGINE='mysql'; `$env:REDIS_URL='redis://localhost:6379/0'; `$env:CELERY_BROKER_URL='amqp://guest:guest@localhost:5672//'; `$env:CELERY_RESULT_BACKEND='redis://localhost:6379/2'; & '$venvPython' -m celery -A config worker -l info -P solo"

Start-Sleep -Seconds 2
Write-Host "Starting Celery Beat (Terminal 3)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; `$env:DB_ENGINE='mysql'; `$env:REDIS_URL='redis://localhost:6379/0'; `$env:CELERY_BROKER_URL='amqp://guest:guest@localhost:5672//'; `$env:CELERY_RESULT_BACKEND='redis://localhost:6379/2'; & '$venvPython' -m celery -A config beat -l info"

Write-Host "`nAll 3 terminals started. Close them manually when done." -ForegroundColor Green
