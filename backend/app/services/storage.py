"""Storage service for S3/MinIO operations using boto3."""

import logging
from datetime import timedelta
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Servicio para operaciones de almacenamiento en S3/MinIO.

    Este servicio es perezoso: solo crea el cliente cuando se necesita.
    No mantiene estado persistente que consuma memoria.
    """

    def __init__(self) -> None:
        """Inicializar el servicio de almacenamiento."""
        self._s3_client: boto3.client | None = None

    @property
    def s3_client(self) -> boto3.client:
        """
        Obtener cliente S3, creándolo si no existe.

        Esta propiedad es perezosa: crea el cliente solo cuando se necesita.
        """
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4"),
            )
        return self._s3_client

    def generate_presigned_url(
        self,
        operation: str,
        bucket: str,
        key: str,
        expires_in: int = 3600,
        **kwargs: Any,
    ) -> str:
        """
        Generar URL prefirmada para operaciones S3.

        Para operaciones de descarga (get_object), usa un cliente temporal
        con el endpoint público (localhost:9000) para que la firma sea válida
        desde el navegador del usuario.

        Args:
            operation: Operación a realizar ('put_object', 'get_object', etc.)
            bucket: Nombre del bucket
            key: Clave (ruta) del objeto en S3
            expires_in: Tiempo de expiración en segundos (default: 1 hora)
            **kwargs: Parámetros adicionales para la operación

        Returns:
            URL prefirmada

        Raises:
            ClientError: Si hay un error de cliente de boto3
            BotoCoreError: Si hay un error general de boto3
        """
        try:
            # Para operaciones de descarga, usar endpoint público para que la firma
            # sea válida desde el navegador del usuario
            if operation == "get_object":
                # Cliente solo para firmar URLs públicas
                # Nota: Esta es una operación offline (matemática), no requiere
                # conexión de red desde el contenedor
                # MinIO es muy estricto con la región, usar 'us-east-1' hardcodeado
                signer_client = boto3.client(
                    "s3",
                    endpoint_url="http://localhost:9000",
                    aws_access_key_id=settings.s3_access_key_id,
                    aws_secret_access_key=settings.s3_secret_access_key,
                    region_name="us-east-1",
                    config=Config(signature_version="s3v4"),
                )
                
                # Sin params extra, solo lo básico: Bucket y Key
                # NO incluir ResponseContentDisposition ni ningún otro parámetro
                url = signer_client.generate_presigned_url(
                    ClientMethod=operation,
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
            else:
                # Para otras operaciones (put_object, etc.), usar el cliente interno
                url = self.s3_client.generate_presigned_url(
                    ClientMethod=operation,
                    Params={"Bucket": bucket, "Key": key, **kwargs},
                    ExpiresIn=expires_in,
                )
            logger.info(
                f"Generated presigned URL for {operation} on bucket={bucket}, key={key}"
            )
            return url
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                f"ClientError generating presigned URL: {error_code} - {str(e)}"
            )
            raise
        except BotoCoreError as e:
            logger.error(f"BotoCoreError generating presigned URL: {str(e)}")
            raise

    def generate_presigned_post(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
        conditions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Generar POST prefirmado para subida directa a S3.

        Útil para subidas desde el navegador sin pasar por el servidor.

        Args:
            bucket: Nombre del bucket
            key: Clave (ruta) del objeto en S3
            expires_in: Tiempo de expiración en segundos (default: 1 hora)
            conditions: Condiciones adicionales para la subida (ej. tamaño máximo)

        Returns:
            Diccionario con 'url' y 'fields' para el POST

        Raises:
            ClientError: Si hay un error de cliente de boto3
            BotoCoreError: Si hay un error general de boto3
        """
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                ExpiresIn=expires_in,
                Conditions=conditions or [],
            )
            logger.info(
                f"Generated presigned POST for bucket={bucket}, key={key}"
            )
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                f"ClientError generating presigned POST: {error_code} - {str(e)}"
            )
            raise
        except BotoCoreError as e:
            logger.error(f"BotoCoreError generating presigned POST: {str(e)}")
            raise

    def check_bucket_exists(self, bucket: str) -> bool:
        """
        Verificar si un bucket existe.

        Esta función es perezosa: solo hace una consulta cuando se necesita.

        Args:
            bucket: Nombre del bucket a verificar

        Returns:
            True si el bucket existe, False en caso contrario

        Raises:
            ClientError: Si hay un error de cliente de boto3
            BotoCoreError: Si hay un error general de boto3
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # 404 significa que no existe, 403 puede significar que no tenemos permisos
            if error_code in ("404", "NoSuchBucket"):
                return False
            logger.error(f"Error checking bucket existence: {error_code} - {str(e)}")
            raise
        except BotoCoreError as e:
            logger.error(f"BotoCoreError checking bucket: {str(e)}")
            raise


# Instancia singleton del servicio
storage_service = StorageService()

