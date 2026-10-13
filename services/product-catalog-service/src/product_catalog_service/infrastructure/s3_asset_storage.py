"""Adaptador `AssetStorage` para almacenamiento compatible con S3 (MinIO en SIO).

Usa la API S3 estándar (boto3) con direccionamiento por ruta, de modo que MinIO puede
sustituirse por otro almacenamiento S3 sin cambiar el dominio. Las credenciales llegan
por configuración y nunca se registran.
"""

from __future__ import annotations

from collections.abc import Iterator

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.application.ports import StoredObject
from product_catalog_service.config import Settings

CHUNK_SIZE = 64 * 1024
_NOT_FOUND = {"404", "NoSuchKey", "NotFound"}


class S3AssetStorage:
    def __init__(self, *, endpoint: str, bucket: str, access_key: str, secret_key: str, region: str, timeout_seconds: float) -> None:
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=timeout_seconds,
                read_timeout=timeout_seconds,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "S3AssetStorage | None":
        if not settings.asset_storage_configured:
            return None
        return cls(
            endpoint=settings.asset_storage_endpoint,
            bucket=settings.asset_storage_bucket,
            access_key=settings.asset_storage_access_key,
            secret_key=settings.asset_storage_secret_key,
            region=settings.asset_storage_region,
            timeout_seconds=settings.asset_storage_timeout_seconds,
        )

    @staticmethod
    def _info(key: str, response: dict) -> StoredObject:
        return StoredObject(
            key=key,
            size=int(response.get("ContentLength", 0)),
            content_type=response.get("ContentType"),
            etag=(response.get("ETag") or "").strip('"') or None,
            metadata={k.lower(): v for k, v in (response.get("Metadata") or {}).items()},
        )

    def head(self, key: str) -> StoredObject | None:
        try:
            return self._info(key, self._client.head_object(Bucket=self.bucket, Key=key))
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in _NOT_FOUND:
                return None
            raise AssetStorageUnavailableError("El almacenamiento de objetos rechazó la consulta.") from exc
        except BotoCoreError as exc:
            raise AssetStorageUnavailableError("El almacenamiento de objetos no está disponible.") from exc

    def exists(self, key: str) -> bool:
        return self.head(key) is not None

    def get(self, key: str) -> tuple[StoredObject, Iterator[bytes]] | None:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in _NOT_FOUND:
                return None
            raise AssetStorageUnavailableError("El almacenamiento de objetos rechazó la lectura.") from exc
        except BotoCoreError as exc:
            raise AssetStorageUnavailableError("El almacenamiento de objetos no está disponible.") from exc
        body = response["Body"]

        def chunks() -> Iterator[bytes]:
            try:
                yield from body.iter_chunks(CHUNK_SIZE)
            finally:
                body.close()

        return self._info(key, response), chunks()

    def put(self, key: str, data: bytes, *, content_type: str, metadata: dict[str, str] | None = None) -> StoredObject:
        try:
            self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, Metadata=metadata or {})
        except (ClientError, BotoCoreError) as exc:
            raise AssetStorageUnavailableError("No fue posible guardar el objeto.") from exc
        return StoredObject(key=key, size=len(data), content_type=content_type, etag=None, metadata=metadata or {})
