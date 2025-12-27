"""API endpoints para gestión de cleaning jobs."""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import NotFoundError, map_exception_to_http
from app.models.cleaning_job import CleaningJob, CleaningJobStatus
from app.models.dataset import Dataset, DatasetStatus
from app.schemas.jobs import CreateJobRequest, JobResponse, JobStatusResponse
from app.services.engine.cleaning_engine import CleaningEngine, CleaningEngineError
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

cleaning_engine = CleaningEngine()


async def process_cleaning_job(
    job_id: int,
    dataset_path: str,
    rules_json: dict,
    output_format: str,
    db_url: str,
) -> None:
    """
    Procesar un job de limpieza en background.

    Esta función se ejecuta de forma asíncrona después de que el endpoint
    responde al cliente. Actualiza el estado del job en la base de datos.

    Args:
        job_id: ID del CleaningJob
        dataset_path: Ruta del archivo CSV de entrada
        rules_json: JSON con reglas de limpieza
        output_format: Formato de salida
        db_url: URL de la base de datos para crear nueva sesión
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.models.cleaning_job import CleaningJob, CleaningJobStatus

    # Crear nueva sesión de BD para el background task
    engine = create_async_engine(db_url)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        try:
            # Obtener el job
            result = await session.execute(
                select(CleaningJob).where(CleaningJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error(f"Job {job_id} not found in background task")
                return

            # Actualizar estado a RUNNING
            job.status = CleaningJobStatus.RUNNING
            await session.commit()
            logger.info(f"Job {job_id} started processing")

            # Generar ruta de salida
            output_dir = Path("/tmp/cleaned")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"job_{job_id}.{output_format}")

            # Procesar dataset
            stats = await cleaning_engine.process_dataset(
                input_path=dataset_path,
                output_path=output_path,
                rules_json=rules_json,
                output_format=output_format,
            )

            # Actualizar job con resultado
            job.status = CleaningJobStatus.COMPLETED
            job.output_path_s3 = output_path
            await session.commit()

            logger.info(
                f"Job {job_id} completed: {stats['input_rows']} -> {stats['output_rows']} rows"
            )

        except CleaningEngineError as e:
            logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
            # Actualizar job con error
            if job:
                job.status = CleaningJobStatus.FAILED
                await session.commit()
        except Exception as e:
            logger.error(f"Unexpected error in job {job_id}: {str(e)}", exc_info=True)
            # Re-obtener el job por si acaso
            if not job:
                result = await session.execute(
                    select(CleaningJob).where(CleaningJob.id == job_id)
                )
                job = result.scalar_one_or_none()
            if job:
                job.status = CleaningJobStatus.FAILED
                await session.commit()
        finally:
            await engine.dispose()


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_cleaning_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Crear un nuevo job de limpieza y lanzarlo en background.

    Este endpoint crea el job en la BD y lo lanza inmediatamente
    usando BackgroundTasks de FastAPI.

    Args:
        request: Request con dataset_id y rules
        background_tasks: BackgroundTasks de FastAPI
        db: Sesión de base de datos

    Returns:
        Job creado con estado PENDING

    Raises:
        HTTPException: Si el dataset no existe o no está listo
    """
    try:
        # Validar que el dataset existe y está listo
        result = await db.execute(
            select(Dataset).where(Dataset.id == request.dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", request.dataset_id)

        if dataset.status != DatasetStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset is not ready (current status: {dataset.status})",
            )

        # Nota: No validamos la existencia del archivo en S3 aquí porque:
        # 1. El archivo está en S3/MinIO, no en el sistema de archivos local
        # 2. file_path_s3 es una key de S3, no una ruta del sistema de archivos
        # 3. Si el dataset tiene estado READY, confiamos en que el archivo existe
        #    (el estado READY solo se asigna después de upload-complete exitoso)

        # Crear job en BD
        job = CleaningJob(
            dataset_id=request.dataset_id,
            rules_config_json=request.rules,
            status=CleaningJobStatus.PENDING,
        )
        db.add(job)
        await db.flush()  # Para obtener el ID
        await db.commit()

        # Lanzar procesamiento en background
        background_tasks.add_task(
            process_cleaning_job,
            job_id=job.id,
            dataset_path=dataset.file_path_s3,
            rules_json=request.rules,
            output_format=request.output_format,
            db_url=settings.database_url,
        )

        logger.info(f"Created job {job.id} for dataset {request.dataset_id}")

        # Manejar status: puede ser Enum o string dependiendo de SQLAlchemy
        status_value = job.status.value if hasattr(job.status, "value") else job.status

        return JobResponse(
            id=job.id,
            dataset_id=job.dataset_id,
            status=status_value,
            output_path_s3=job.output_path_s3,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat() if job.updated_at else None,
        )

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating cleaning job",
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """
    Obtener el estado de un job de limpieza.

    Si el job está completado, incluye una URL prefirmada para descargar
    el resultado.

    Args:
        job_id: ID del job
        db: Sesión de base de datos

    Returns:
        Estado del job y URL de descarga si está completado

    Raises:
        HTTPException: Si el job no existe
    """
    try:
        result = await db.execute(
            select(CleaningJob).where(CleaningJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("CleaningJob", job_id)

        download_url = None
        error_message = None

        # Manejar status: puede ser Enum o string dependiendo de SQLAlchemy
        job_status_value = job.status.value if hasattr(job.status, "value") else job.status

        # Si está completado, generar URL prefirmada para descarga
        is_completed = (
            job_status_value == CleaningJobStatus.COMPLETED.value
            or job_status_value == "completed"
        )
        if is_completed and job.output_path_s3:
            try:
                # Extraer key de S3 desde la ruta
                # Por ahora asumimos que es una ruta local, en producción sería s3://bucket/key
                s3_key = job.output_path_s3.replace("/tmp/cleaned/", "cleaned/")
                download_url = storage_service.generate_presigned_url(
                    operation="get_object",
                    bucket=settings.s3_bucket_name,
                    key=s3_key,
                    expires_in=3600,  # 1 hora
                )
            except Exception as e:
                logger.error(f"Error generating download URL: {str(e)}")
                # No fallar si no se puede generar la URL, solo no incluirla

        # Si falló, intentar obtener mensaje de error (por ahora None)
        if job_status_value == CleaningJobStatus.FAILED.value or job_status_value == "failed":
            error_message = "El procesamiento falló. Revisa los logs para más detalles."

        # Usar el valor ya calculado para la respuesta
        status_value = job_status_value

        return JobStatusResponse(
            id=job.id,
            status=status_value,
            output_path_s3=job.output_path_s3,
            download_url=download_url,
            error_message=error_message,
        )

    except NotFoundError as e:
        raise map_exception_to_http(e)
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting job status",
        )

