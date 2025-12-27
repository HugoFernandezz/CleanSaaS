"""Pydantic schemas for cleaning jobs API."""

from typing import Any

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    """Request schema para crear un job de limpieza."""

    dataset_id: int = Field(..., description="ID del dataset a procesar")
    rules: dict[str, Any] = Field(..., description="JSON con reglas de limpieza")
    output_format: str = Field(
        default="parquet",
        description="Formato de salida (parquet o csv)",
    )


class JobResponse(BaseModel):
    """Response schema para un job de limpieza."""

    id: int
    dataset_id: int
    status: str
    output_path_s3: str | None = None
    created_at: str
    updated_at: str | None = None


class JobStatusResponse(BaseModel):
    """Response schema para el estado de un job."""

    id: int
    status: str
    output_path_s3: str | None = None
    download_url: str | None = Field(
        None, description="URL prefirmada para descargar el resultado (si está completado)"
    )
    error_message: str | None = Field(
        None, description="Mensaje de error si el job falló"
    )


