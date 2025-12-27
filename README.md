# CleanSaaS - Data Cleaning SaaS MVP

Sistema SaaS de alto rendimiento para limpieza de datos basado en reglas, capaz de procesar archivos de hasta 10 GB mediante arquitectura streaming-first.

## 🏗️ Arquitectura

- **Backend**: FastAPI (async) + Polars (Rust-backed) + PostgreSQL 15
- **Frontend**: React 18 + Vite + TypeScript + TanStack Query
- **Almacenamiento**: MinIO (S3-compatible) para archivos grandes
- **Base de Datos**: PostgreSQL 15 para metadatos

## 🚀 Inicio Rápido

### Prerrequisitos

- **Docker Desktop para Windows**: [Descargar e instalar](https://www.docker.com/products/docker-desktop/)
  - Requiere Windows 10/11 64-bit con WSL 2 habilitado
  - Después de instalar, reinicia PowerShell y verifica con: `docker --version`
- Poetry (para desarrollo local del backend)
- Node.js 20+ (para desarrollo local del frontend)

### Configuración

1. **Clonar el repositorio** (si aplica)

2. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   ```
   Edita `.env` según tus necesidades.

3. **Iniciar servicios con Docker Compose**:
   ```bash
   docker compose up -d
   ```

   Esto levantará:
   - PostgreSQL en `localhost:5432`
   - MinIO API en `localhost:9000` (Console en `localhost:9001`)
   - Backend FastAPI en `http://localhost:8000`
   - Frontend React en `http://localhost:3000`

4. **Inicializar MinIO** (primera vez):
   - Accede a `http://localhost:9001`
   - Login: `minioadmin` / `minioadmin`
   - Crea un bucket llamado `datasets` (o el nombre configurado en `.env`)

### Desarrollo Local (sin Docker)

#### Backend

```bash
cd backend
poetry install
poetry shell
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📁 Estructura del Proyecto

```
CleanSaaS/
├── backend/              # FastAPI + Polars
│   ├── app/
│   │   ├── api/         # Routers/Endpoints
│   │   ├── core/        # Config, Security, Logging
│   │   ├── models/      # SQLAlchemy Models
│   │   ├── schemas/     # Pydantic Schemas
│   │   └── services/    # Business Logic (CleaningEngine)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/            # React + Vite
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── infra/               # Infrastructure configs
├── docs/                # Documentation
└── docker-compose.yml
```

## 🔧 Tecnologías Clave

### Backend
- **FastAPI**: Framework web asíncrono de alto rendimiento
- **Polars**: Motor de datos en Rust con evaluación perezosa y streaming
- **SQLAlchemy 2.0**: ORM asíncrono
- **Pydantic v2**: Validación de datos estricta

### Frontend
- **React 18**: Framework UI
- **TanStack Query v5**: Gestión de estado remoto
- **Zustand**: Estado local ligero
- **@tanstack/react-virtual**: Virtualización para grandes datasets
- **react-querybuilder**: Constructor visual de reglas

## 📝 Reglas de Desarrollo

Este proyecto utiliza archivos `.cursorrules` para guiar el desarrollo asistido por IA:

- `.cursorrules`: Reglas maestras del proyecto
- `.cursor/rules/backend.mdc`: Reglas específicas de backend
- `.cursor/rules/frontend.mdc`: Reglas específicas de frontend
- `.cursor/rules/data-pipeline.mdc`: Reglas del motor de datos

**Principios críticos**:
- ✅ **Streaming First**: Siempre usar `pl.scan_csv()` y `collect(streaming=True)`
- ❌ **PROHIBIDO Pandas**: Solo Polars para procesamiento de datos
- ✅ **Async First**: Todos los endpoints deben ser `async def`
- ✅ **Virtualización**: NUNCA renderizar >50 elementos directamente en el DOM

## 🧪 Testing

```bash
# Backend
cd backend
poetry run pytest

# Frontend
cd frontend
npm run test
```

## 📚 Documentación

- API Docs: `http://localhost:8000/docs` (Swagger UI)
- Roadmap: Ver `RoadMAP.md` para arquitectura detallada

## 🔐 Seguridad

- Nunca hardcodear credenciales
- Usar variables de entorno para todos los secretos
- Validar todas las entradas con Pydantic
- No usar `eval()` o `exec()` en el parser de reglas

## 📄 Licencia

[Especificar licencia]

