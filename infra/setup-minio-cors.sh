#!/bin/bash
# Script para configurar CORS en MinIO usando mc (MinIO Client)

set -e

MC_ALIAS="cleansaas"
MC_ENDPOINT="http://localhost:9000"
MC_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
MC_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET_NAME="${S3_BUCKET_NAME:-datasets}"

echo "Configurando CORS para MinIO..."

# Verificar si mc está instalado
if ! command -v mc &> /dev/null; then
    echo "MinIO Client (mc) no encontrado. Instalando..."
    # Para Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /tmp/mc
        chmod +x /tmp/mc
        MC_CMD="/tmp/mc"
    # Para macOS
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install minio/stable/mc || echo "Por favor instala mc manualmente"
        MC_CMD="mc"
    else
        echo "Por favor instala MinIO Client manualmente"
        exit 1
    fi
else
    MC_CMD="mc"
fi

# Configurar alias
$MC_CMD alias set $MC_ALIAS $MC_ENDPOINT $MC_ACCESS_KEY $MC_SECRET_KEY

# Crear bucket si no existe
if ! $MC_CMD ls $MC_ALIAS/$BUCKET_NAME &> /dev/null; then
    echo "Creando bucket '$BUCKET_NAME'..."
    $MC_CMD mb $MC_ALIAS/$BUCKET_NAME
fi

# Configurar CORS para permitir todas las operaciones desde cualquier origen
echo "Configurando CORS..."
cat > /tmp/cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

$MC_CMD anonymous set download $MC_ALIAS/$BUCKET_NAME || true
$MC_CMD cors set /tmp/cors.json $MC_ALIAS/$BUCKET_NAME || echo "Nota: CORS puede requerir configuración manual en la consola de MinIO"

echo "MinIO configurado. Accede a la consola en: http://localhost:9001"
echo "Usuario: $MC_ACCESS_KEY"
echo "Contraseña: $MC_SECRET_KEY"


