# Script PowerShell para inicializar la base de datos y aplicar migraciones

Write-Host "Generando migración inicial..." -ForegroundColor Green
alembic revision --autogenerate -m "Initial migration: projects, datasets, cleaning_jobs"

Write-Host "Aplicando migraciones..." -ForegroundColor Green
alembic upgrade head

Write-Host "Base de datos inicializada correctamente." -ForegroundColor Green


