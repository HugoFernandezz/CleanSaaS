"""API endpoints para gestión de archivos y S3."""

import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import NotFoundError, map_exception_to_http
from app.models.dataset import Dataset, DatasetStatus
from app.models.project import Project
from app.schemas.storage import (
    FileUploadCompleteRequest,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])


def generate_s3_key(filename: str, project_id: int | None = None) -> str:
    """
    Generar clave S3 para un archivo.

    Esta función es determinista: genera la misma clave para los mismos inputs.
    Organiza los archivos por proyecto y fecha para facilitar la gestión.

    Args:
        filename: Nombre del archivo
        project_id: ID del proyecto (opcional)

    Returns:
        Clave S3 (ruta) para el archivo
    """
    # Generar nombre único para evitar colisiones
    unique_id = uuid.uuid4().hex[:8]
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    safe_filename = Path(filename).name  # Solo el nombre, sin ruta

    if project_id:
        return f"projects/{project_id}/{timestamp}/{unique_id}_{safe_filename}"
    return f"uploads/{timestamp}/{unique_id}_{safe_filename}"


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def create_presigned_url(
    request: PresignedUrlRequest,
    db: AsyncSession = Depends(get_db),
) -> PresignedUrlResponse:
    """
    Generar URL prefirmada para subir un archivo directamente a S3/MinIO.

    Este endpoint es perezoso: solo genera la URL, no procesa el archivo.
    El archivo se sube directamente desde el navegador a S3, evitando
    que pase por el servidor backend y consuma memoria.

    Args:
        request: Request con nombre de archivo y proyecto opcional
        db: Sesión de base de datos (para validar proyecto si se proporciona)

    Returns:
        URL prefirmada y campos necesarios para la subida

    Raises:
        HTTPException: Si el proyecto no existe o hay error con S3
    """
    try:
        # Validar que el proyecto existe si se proporciona
        if request.project_id:
            result = await db.execute(
                select(Project).where(Project.id == request.project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise NotFoundError("Project", request.project_id)

        # Generar clave S3
        s3_key = generate_s3_key(request.filename, request.project_id)

        # Verificar que el bucket existe, si no existe intentar crearlo
        if not storage_service.check_bucket_exists(settings.s3_bucket_name):
            logger.warning(f"Bucket {settings.s3_bucket_name} does not exist, attempting to create...")
            try:
                storage_service.s3_client.create_bucket(Bucket=settings.s3_bucket_name)
                logger.info(f"Bucket {settings.s3_bucket_name} created successfully")
            except Exception as e:
                logger.error(f"Failed to create bucket: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Storage bucket '{settings.s3_bucket_name}' does not exist and could not be created. Please create it manually in MinIO console at http://localhost:9001",
                )

        # Generar POST prefirmado (mejor para subidas desde navegador)
        # Nota: No incluimos Content-Type en conditions porque el navegador
        # lo establecerá automáticamente y puede causar conflictos
        presigned_post = storage_service.generate_presigned_post(
            bucket=settings.s3_bucket_name,
            key=s3_key,
            expires_in=3600,  # 1 hora
            conditions=[
                ["content-length-range", 1, 10 * 1024 * 1024 * 1024],  # Max 10GB
            ],
        )

        return PresignedUrlResponse(
            url=presigned_post["url"],
            fields=presigned_post["fields"],
            key=s3_key,
            expires_in=3600,
        )

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating presigned URL",
        )


@router.post("/upload-complete")
async def file_upload_complete(
    request: FileUploadCompleteRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """
    Callback para notificar que la subida de archivo completó.

    Este endpoint registra el archivo en la base de datos después de que
    el frontend lo haya subido directamente a S3.

    Args:
        request: Request con información del archivo subido
        db: Sesión de base de datos

    Returns:
        Confirmación de registro con dataset_id

    Raises:
        HTTPException: Si hay error al registrar el archivo
    """
    try:
        # Validar o crear proyecto
        project_id = request.project_id
        if project_id:
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise NotFoundError("Project", project_id)
        else:
            # Si no hay project_id, crear un proyecto por defecto
            default_project = Project(
                name="Default Project",
                description="Proyecto creado automáticamente para archivos sin proyecto",
            )
            db.add(default_project)
            await db.flush()
            project_id = default_project.id
            logger.info(f"Created default project {project_id} for file upload")

        # Crear Dataset en la BD
        # Estado READY: el archivo está subido y listo para procesar
        dataset = Dataset(
            project_id=project_id,
            file_path_s3=request.key,  # La key de S3 es la ruta
            status=DatasetStatus.READY,  # Cambiado de UPLOADED a READY para permitir procesamiento inmediato
            row_count=None,  # Se puede calcular después
        )
        db.add(dataset)
        await db.flush()  # Para obtener el ID
        await db.commit()

        logger.info(f"Dataset {dataset.id} created and marked as READY for file {request.key}")

        return {
            "status": "received",
            "message": "File upload completion registered",
            "dataset_id": dataset.id,
            "key": request.key,
        }

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering file upload",
        )

