# Backend - CleanSaaS

Backend API para limpieza de datos usando FastAPI, Polars y PostgreSQL.

## Estructura

```
backend/
├── app/
│   ├── api/          # Routers/Endpoints
│   ├── core/         # Config, DB, Errors
│   ├── models/       # SQLAlchemy Models
│   ├── schemas/      # Pydantic Schemas
│   └── services/     # Business Logic
├── alembic/          # Migraciones de base de datos
└── scripts/          # Scripts de utilidad
```

## Configuración

### Variables de Entorno

El backend requiere las siguientes variables de entorno (ver `env.template` en la raíz):

- `DATABASE_URL`: URL de conexión a PostgreSQL (formato: `postgresql+asyncpg://user:pass@host:port/dbname`)
- `S3_ENDPOINT_URL`: URL del endpoint S3/MinIO
- `S3_ACCESS_KEY_ID`: Clave de acceso S3
- `S3_SECRET_ACCESS_KEY`: Clave secreta S3
- `S3_BUCKET_NAME`: Nombre del bucket S3
- `ENVIRONMENT`: Entorno (development/production)

## Desarrollo Local

### Instalación

```bash
# Instalar dependencias con Poetry
poetry install

# Activar entorno virtual
poetry shell
```

### Base de Datos

#### Generar Migración Inicial

```bash
# Desde el directorio backend/
alembic revision --autogenerate -m "Initial migration: projects, datasets, cleaning_jobs"
```

#### Aplicar Migraciones

```bash
alembic upgrade head
```

#### Revertir Migración

```bash
alembic downgrade -1
```

### Ejecutar Servidor

```bash
# Desarrollo con hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# O usando Python directamente
python -m uvicorn app.main:app --reload
```

## Modelos de Datos

### Project
- `id`: Identificador único
- `name`: Nombre del proyecto
- `description`: Descripción opcional
- `created_at`: Timestamp de creación

### Dataset
- `id`: Identificador único
- `project_id`: Referencia al proyecto
- `file_path_s3`: Ruta del archivo en S3
- `status`: Estado (uploading, uploaded, processing, ready, error)
- `row_count`: Número de filas (opcional)

### CleaningJob
- `id`: Identificador único
- `dataset_id`: Referencia al dataset
- `rules_config_json`: Configuración de reglas en JSON
- `status`: Estado (pending, running, completed, failed, cancelled)
- `output_path_s3`: Ruta del archivo procesado en S3

## Testing

```bash
poetry run pytest
```

## Linting y Formateo

```bash
# Formatear código
poetry run black .

# Linting
poetry run ruff check .

# Type checking
poetry run mypy app/
```


