# Infraestructura

Este directorio contiene configuraciones y scripts de infraestructura.

## Scripts

### `init-minio.sh`

Script para inicializar MinIO con el bucket necesario para el almacenamiento de datasets.

**Uso:**
```bash
chmod +x infra/init-minio.sh
./infra/init-minio.sh
```

O ejecutar manualmente desde el contenedor:
```bash
docker compose exec minio mc mb /data/datasets
```

## Configuración Manual de MinIO

Si prefieres configurar MinIO manualmente:

1. Accede a la consola: http://localhost:9001
2. Login con:
   - Usuario: `minioadmin` (o el valor de `MINIO_ROOT_USER`)
   - Contraseña: `minioadmin` (o el valor de `MINIO_ROOT_PASSWORD`)
3. Crea un bucket llamado `datasets` (o el valor de `S3_BUCKET_NAME`)



