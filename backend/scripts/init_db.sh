#!/bin/bash
# Script para inicializar la base de datos y aplicar migraciones

set -e

echo "Generando migración inicial..."
alembic revision --autogenerate -m "Initial migration: projects, datasets, cleaning_jobs"

echo "Aplicando migraciones..."
alembic upgrade head

echo "Base de datos inicializada correctamente."


