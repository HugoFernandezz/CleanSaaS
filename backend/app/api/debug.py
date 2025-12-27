"""Endpoints de debug para probar el motor de limpieza."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError, map_exception_to_http
from app.models.cleaning_job import CleaningJob, CleaningJobStatus
from app.models.dataset import Dataset
from app.services.engine.cleaning_engine import CleaningEngine, CleaningEngineError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

cleaning_engine = CleaningEngine()


@router.post("/run-job/{job_id}")
async def run_cleaning_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Endpoint de prueba para ejecutar un job de limpieza manualmente.

    Este endpoint es temporal para debugging y verificación del motor Polars.
    Procesa el dataset asociado al job aplicando las reglas configuradas.

    Args:
        job_id: ID del CleaningJob a ejecutar
        db: Sesión de base de datos

    Returns:
        Resultado del procesamiento con estadísticas

    Raises:
        HTTPException: Si el job no existe o hay error en el procesamiento
    """
    try:
        # 1. Obtener el job
        result = await db.execute(
            select(CleaningJob).where(CleaningJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("CleaningJob", job_id)

        # 2. Verificar que el job está en estado válido
        if job.status != CleaningJobStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is not in PENDING status (current: {job.status})",
            )

        # 3. Obtener el dataset asociado
        result = await db.execute(select(Dataset).where(Dataset.id == job.dataset_id))
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", job.dataset_id)

        # 4. Verificar que el dataset está listo
        if dataset.status.value != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset is not ready (current status: {dataset.status})",
            )

        # 5. Actualizar estado del job a RUNNING
        job.status = CleaningJobStatus.RUNNING
        await db.commit()

        try:
            # 6. Construir rutas
            # Por ahora asumimos que los archivos están en el sistema de archivos local
            # En producción, esto vendría de S3
            input_path = dataset.file_path_s3
            output_path = f"/tmp/cleaned_{job.id}.parquet"

            # 7. Procesar dataset con el motor
            stats = await cleaning_engine.process_dataset(
                input_path=input_path,
                output_path=output_path,
                rules_json=job.rules_config_json,
                output_format="parquet",
            )

            # 8. Actualizar job con resultado
            job.status = CleaningJobStatus.COMPLETED
            job.output_path_s3 = output_path
            await db.commit()

            logger.info(f"Job {job_id} completed successfully: {stats}")

            return {
                "status": "completed",
                "job_id": job_id,
                "stats": stats,
                "output_path": output_path,
            }

        except CleaningEngineError as e:
            # Error en el procesamiento
            job.status = CleaningJobStatus.FAILED
            await db.commit()
            logger.error(f"Job {job_id} failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Processing failed: {str(e)}",
            )

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error running job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


