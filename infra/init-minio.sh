#!/bin/bash
# Script para inicializar MinIO con el bucket necesario
# Este script debe ejecutarse después de que MinIO esté corriendo

set -e

MC_ALIAS="cleansaas"
MC_ENDPOINT="http://localhost:9000"
MC_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
MC_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET_NAME="${S3_BUCKET_NAME:-datasets}"

echo "Configurando MinIO..."

# Instalar mc (MinIO Client) si no está disponible
if ! command -v mc &> /dev/null; then
    echo "MinIO Client (mc) no encontrado. Instalando..."
    # Para Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /tmp/mc
        chmod +x /tmp/mc
        MC_CMD="/tmp/mc"
    # Para macOS
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install minio/stable/mc || echo "Por favor instala mc manualmente: brew install minio/stable/mc"
        MC_CMD="mc"
    else
        echo "Por favor instala MinIO Client manualmente desde: https://min.io/docs/minio/linux/reference/minio-mc.html"
        exit 1
    fi
else
    MC_CMD="mc"
fi

# Configurar alias
$MC_CMD alias set $MC_ALIAS $MC_ENDPOINT $MC_ACCESS_KEY $MC_SECRET_KEY

# Crear bucket si no existe
if $MC_CMD ls $MC_ALIAS/$BUCKET_NAME &> /dev/null; then
    echo "Bucket '$BUCKET_NAME' ya existe."
else
    echo "Creando bucket '$BUCKET_NAME'..."
    $MC_CMD mb $MC_ALIAS/$BUCKET_NAME
    echo "Bucket '$BUCKET_NAME' creado exitosamente."
fi

echo "MinIO configurado correctamente."
echo "Accede a la consola en: http://localhost:9001"
echo "Usuario: $MC_ACCESS_KEY"
echo "Contraseña: $MC_SECRET_KEY"



