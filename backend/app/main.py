"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import datasets, debug, files, jobs
from app.core.db import engine

app = FastAPI(
    title="CleanSaaS API",
    description="API para limpieza de datos basada en reglas",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(files.router)
app.include_router(datasets.router)
app.include_router(jobs.router)
app.include_router(debug.router)


@app.on_event("startup")
async def startup() -> None:
    """Inicialización al arrancar la aplicación."""
    # Verificar conexión a la base de datos
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: None)


@app.on_event("shutdown")
async def shutdown() -> None:
    """Limpieza al cerrar la aplicación."""
    await engine.dispose()


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "CleanSaaS API", "version": "0.1.0"}


