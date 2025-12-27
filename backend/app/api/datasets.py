"""API endpoints para gestión de datasets."""

import logging
import os
import tempfile
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import NotFoundError, map_exception_to_http
from app.models.dataset import Dataset
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Obtener vista previa de un dataset (primeras N filas).

    Este endpoint usa Polars con evaluación perezosa para leer solo
    las primeras filas del archivo CSV sin cargar todo en memoria.

    Args:
        dataset_id: ID del dataset
        limit: Número máximo de filas a retornar (default: 100)
        db: Sesión de base de datos

    Returns:
        Diccionario con columnas y datos (lista de diccionarios)

    Raises:
        HTTPException: Si el dataset no existe o hay error leyendo el archivo
    """
    try:
        # 1. Buscar el dataset por ID
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", dataset_id)

        # 2. Determinar si el archivo está en S3 o es una ruta local
        file_path = dataset.file_path_s3
        local_file_path: str | None = None
        
        # Si es una ruta local (empieza con /)
        if file_path.startswith("/") and os.path.exists(file_path):
            local_file_path = file_path
        else:
            # El archivo está en S3, necesitamos descargarlo temporalmente
            # Construir key de S3 (file_path_s3 ya contiene la key relativa)
            s3_key = file_path
            
            # Descargar archivo temporalmente usando boto3
            try:
                # Crear archivo temporal
                with tempfile.NamedTemporaryFile(
                    mode="wb", delete=False, suffix=".csv"
                ) as tmp_file:
                    local_file_path = tmp_file.name
                    
                    # Descargar desde S3 usando boto3
                    storage_service.s3_client.download_fileobj(
                        settings.s3_bucket_name,
                        s3_key,
                        tmp_file,
                    )
                    logger.info(f"Downloaded file from S3: {s3_key} -> {local_file_path}")
            except Exception as e:
                logger.error(f"Error downloading file from S3: {str(e)}", exc_info=True)
                # Limpiar archivo temporal si existe
                if local_file_path and os.path.exists(local_file_path):
                    try:
                        os.unlink(local_file_path)
                    except:
                        pass
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error downloading file from S3: {str(e)}",
                )
        
        # 3. Leer CSV con Polars usando scan_csv (CRÍTICO: nunca read_csv)
        try:
            lazy_frame = pl.scan_csv(
                local_file_path,
                infer_schema_length=1000,  # Inferir schema desde primeras filas
                try_parse_dates=True,
            )
        except Exception as e:
            logger.error(f"Error reading CSV with Polars: {str(e)}", exc_info=True)
            # Limpiar archivo temporal si fue descargado
            if local_file_path and not file_path.startswith("/"):
                try:
                    os.unlink(local_file_path)
                except:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error reading CSV file: {str(e)}",
            )

        # 4. Obtener las primeras N filas usando head() y collect()
        # CRÍTICO: Usar head() antes de collect() para limitar la lectura
        # Esto es seguro porque solo lee las primeras N filas
        df = lazy_frame.head(limit).collect()

        # 5. Convertir a formato JSON (lista de diccionarios)
        # Polars tiene un método to_dicts() que convierte a lista de dicts
        rows = df.to_dicts()

        # 6. Obtener nombres de columnas
        columns = df.columns

        # 7. Limpiar archivo temporal si fue descargado de S3
        if local_file_path and not file_path.startswith("/"):
            try:
                os.unlink(local_file_path)
                logger.debug(f"Cleaned up temporary file: {local_file_path}")
            except Exception as e:
                logger.warning(f"Could not delete temporary file: {str(e)}")

        logger.info(
            f"Preview generated for dataset {dataset_id}: {len(rows)} rows, {len(columns)} columns"
        )

        return {
            "dataset_id": dataset_id,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "total_columns": len(columns),
        }

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting dataset preview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating dataset preview",
        )

