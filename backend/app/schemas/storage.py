"""Pydantic schemas for storage operations."""

from pydantic import BaseModel, Field, field_validator


class PresignedUrlRequest(BaseModel):
    """Request schema para generar URL prefirmada."""

    filename: str = Field(..., description="Nombre del archivo a subir")
    project_id: int | None = Field(
        None, description="ID del proyecto (opcional, para organizar archivos)"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """
        Validar que el archivo tenga extensión .csv.

        Esta validación es estricta: solo permite .csv por ahora.
        """
        if not v.lower().endswith(".csv"):
            raise ValueError("Solo se permiten archivos con extensión .csv")
        if len(v) > 255:
            raise ValueError("El nombre del archivo no puede exceder 255 caracteres")
        return v


class PresignedUrlResponse(BaseModel):
    """Response schema para URL prefirmada."""

    url: str = Field(..., description="URL prefirmada para subir el archivo")
    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Campos adicionales para el POST (si se usa presigned POST)",
    )
    key: str = Field(..., description="Clave (ruta) del archivo en S3")
    expires_in: int = Field(
        3600, description="Tiempo de expiración en segundos"
    )


class FileUploadCompleteRequest(BaseModel):
    """Request schema para notificar que la subida completó."""

    key: str = Field(..., description="Clave del archivo en S3")
    project_id: int | None = Field(
        None, description="ID del proyecto asociado"
    )
    file_size: int | None = Field(
        None, description="Tamaño del archivo en bytes"
    )


