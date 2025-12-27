"""Cleaning engine para procesar datasets con Polars usando evaluación perezosa y streaming."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import polars as pl

from app.core.config import settings
from app.services.engine.parser import RuleParser, RuleParserError
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class CleaningEngineError(Exception):
    """Excepción para errores en el motor de limpieza."""

    pass


class CleaningEngine:
    """
    Motor de limpieza de datos usando Polars con evaluación perezosa y streaming.

    Este servicio es crítico para el rendimiento: usa pl.scan_csv() y
    collect(streaming=True) para procesar archivos grandes sin cargar todo en RAM.

    PROHIBIDO: pl.read_csv() - riesgo de OOM.
    """

    def __init__(self) -> None:
        """Inicializar el motor de limpieza."""
        pass

    async def process_dataset(
        self,
        input_path: str,
        output_path: str,
        rules_json: dict[str, Any],
        output_format: str = "parquet",
    ) -> dict[str, Any]:
        """
        Procesar un dataset aplicando reglas de limpieza.

        Esta función es perezosa: solo construye el plan de ejecución.
        La ejecución real ocurre cuando se materializa con collect(streaming=True).

        Args:
            input_path: Ruta del archivo CSV de entrada (key de S3 o ruta local)
            output_path: Ruta donde guardar el resultado
            rules_json: JSON con reglas de limpieza
            output_format: Formato de salida ("parquet" o "csv")

        Returns:
            Diccionario con estadísticas del procesamiento

        Raises:
            CleaningEngineError: Si hay error en el procesamiento
        """
        temp_file_path: str | None = None
        should_cleanup = False

        try:
            logger.info(f"Starting dataset processing: {input_path} -> {output_path}")

            # 1. Resolver ruta local (descargar de S3 si es necesario)
            local_input_path, should_cleanup = self._resolve_input_path(input_path)
            temp_file_path = local_input_path if should_cleanup else None

            # 2. Crear LazyFrame usando scan_csv (CRÍTICO: nunca read_csv)
            lazy_frame = self._create_lazy_frame(local_input_path)

            # 3. Inspeccionar schema para casting de tipos
            schema = lazy_frame.schema
            logger.debug(f"Dataset schema: {schema}")

            # 4. Parsear reglas y generar expresión Polars
            parser = RuleParser(schema=schema)
            filter_expression = parser.parse(rules_json)

            # 5. Aplicar filtro (esto es perezoso, no ejecuta aún)
            filtered_frame = lazy_frame.filter(filter_expression)

            # 6. Materializar y escribir resultado usando streaming
            if output_format.lower() == "parquet":
                self._write_parquet_streaming(filtered_frame, output_path)
            else:
                self._write_csv_streaming(filtered_frame, output_path)

            # 7. Obtener estadísticas (esto requiere materializar una vez más)
            stats = await self._get_processing_stats(
                local_input_path, output_path, filter_expression
            )

            logger.info(
                f"Dataset processing completed: {stats['input_rows']} -> {stats['output_rows']} rows"
            )

            return stats

        except RuleParserError as e:
            logger.error(f"Rule parsing error: {str(e)}")
            raise CleaningEngineError(f"Invalid rules: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing dataset: {str(e)}", exc_info=True)
            raise CleaningEngineError(f"Processing failed: {str(e)}")
        finally:
            # Limpiar archivo temporal si fue descargado de S3
            if should_cleanup and temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete temporary file: {str(e)}")

    def _resolve_input_path(self, input_path: str) -> tuple[str, bool]:
        """
        Resolver la ruta de entrada a una ruta local.

        Si la ruta es una key de S3, la descarga temporalmente.
        Si es una ruta local, la devuelve tal cual.

        Args:
            input_path: Ruta del archivo (key de S3 o ruta local)

        Returns:
            Tupla (ruta_local, should_cleanup) donde should_cleanup indica
            si el archivo debe ser eliminado después del procesamiento
        """
        # Determinar si es una ruta local o una key de S3
        if input_path.startswith("/") and os.path.exists(input_path):
            # Ruta local válida
            return input_path, False
        else:
            # Es una key de S3, necesitamos descargarla temporalmente
            s3_key = input_path
            bucket_name = settings.s3_bucket_name

            logger.info(f"Downloading file from S3: {bucket_name}/{s3_key}")

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, suffix=".csv"
            ) as tmp_file:
                local_file_path = tmp_file.name

                # Descargar desde S3 usando boto3
                try:
                    storage_service.s3_client.download_fileobj(
                        bucket_name,
                        s3_key,
                        tmp_file,
                    )
                    logger.info(f"File downloaded to temporary location: {local_file_path}")
                    return local_file_path, True
                except Exception as e:
                    logger.error(f"Error downloading file from S3: {str(e)}")
                    # Limpiar archivo temporal si existe
                    if os.path.exists(local_file_path):
                        try:
                            os.unlink(local_file_path)
                        except:
                            pass
                    raise CleaningEngineError(
                        f"Error downloading file from S3: {str(e)}"
                    )

    def _create_lazy_frame(self, input_path: str) -> pl.LazyFrame:
        """
        Crear LazyFrame desde archivo CSV usando scan_csv.

        Esta función es perezosa: no carga datos en memoria.
        Asume que input_path es una ruta local válida.

        Args:
            input_path: Ruta local del archivo CSV

        Returns:
            LazyFrame apuntando al archivo
        """
        # Verificar que el archivo existe (solo para rutas locales)
        if not os.path.exists(input_path):
            raise CleaningEngineError(f"Input file not found: {input_path}")

        # CRÍTICO: usar scan_csv, nunca read_csv
        try:
            lazy_frame = pl.scan_csv(
                input_path,
                infer_schema_length=10000,  # Inferir schema desde primeras filas
                try_parse_dates=True,
            )
            return lazy_frame
        except Exception as e:
            raise CleaningEngineError(f"Error reading CSV: {str(e)}")

    def _write_parquet_streaming(
        self, lazy_frame: pl.LazyFrame, output_path: str
    ) -> None:
        """
        Escribir resultado en formato Parquet usando streaming.

        Esta función es streaming-first: procesa chunk a chunk sin cargar todo en RAM.

        Args:
            lazy_frame: LazyFrame con datos filtrados
            output_path: Ruta donde guardar
        """
        # Crear directorio si no existe
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Escribir usando sink_parquet (streaming nativo)
        try:
            lazy_frame.sink_parquet(
                output_path,
                compression="snappy",
                maintain_order=False,  # Más rápido
            )
        except Exception as e:
            raise CleaningEngineError(f"Error writing Parquet: {str(e)}")

    def _write_csv_streaming(
        self, lazy_frame: pl.LazyFrame, output_path: str
    ) -> None:
        """
        Escribir resultado en formato CSV usando streaming.

        Esta función usa collect(streaming=True) para mantener bajo consumo de memoria.

        Args:
            lazy_frame: LazyFrame con datos filtrados
            output_path: Ruta donde guardar
        """
        # Crear directorio si no existe
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # CRÍTICO: usar collect(streaming=True) para CSV
        try:
            df = lazy_frame.collect(streaming=True)
            df.write_csv(output_path)
        except Exception as e:
            raise CleaningEngineError(f"Error writing CSV: {str(e)}")

    async def _get_processing_stats(
        self,
        input_path: str,
        output_path: str,
        filter_expression: pl.Expr,
    ) -> dict[str, Any]:
        """
        Obtener estadísticas del procesamiento.

        Esta función materializa los datos para contar filas, pero usa streaming.

        Args:
            input_path: Ruta local del archivo de entrada
            output_path: Ruta del archivo de salida
            filter_expression: Expresión de filtro aplicada

        Returns:
            Diccionario con estadísticas
        """
        # Contar filas de entrada (streaming)
        input_lazy = self._create_lazy_frame(input_path)
        input_count = (
            input_lazy.select(pl.count()).collect(streaming=True).item()
        )

        # Contar filas de salida (streaming)
        if output_path.endswith(".parquet"):
            output_lazy = pl.scan_parquet(output_path)
        else:
            output_lazy = pl.scan_csv(output_path)
        output_count = (
            output_lazy.select(pl.count()).collect(streaming=True).item()
        )

        return {
            "input_rows": input_count,
            "output_rows": output_count,
            "rows_filtered": input_count - output_count,
            "input_path": input_path,
            "output_path": output_path,
        }


# Instancia singleton del motor
cleaning_engine = CleaningEngine()

