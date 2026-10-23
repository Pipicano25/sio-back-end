"""Puertos de la capa de aplicación (Principio XV).

Los repositorios del servicio son adaptadores SQLAlchemy concretos que reciben
la sesión. Puertos hacia infraestructura externa: `ManufacturerDirectory` (Party
Identity) y `AssetStorage` (almacenamiento de objetos compatible con S3 para el
contenido de los activos), sustituibles en pruebas.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


class ManufacturerDirectory(Protocol):
    """Consulta de existencia de organizaciones fabricantes en Party Identity.

    Raises:
        ManufacturerDirectoryUnavailableError: si Party Identity no responde de
            forma utilizable.
        ManufacturerDirectoryAccessDeniedError: si Party Identity responde
            `401` o `403` al token propagado.
    """

    def exists(self, organization_id: UUID) -> bool:
        """Indica si la organización existe."""
        ...


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Metadatos de un objeto almacenado (sin exponer bucket ni credenciales)."""

    key: str
    size: int
    content_type: str | None
    etag: str | None
    metadata: dict[str, str] = field(default_factory=dict)


class AssetStorage(Protocol):
    """Almacenamiento de objetos del contenido de los activos (compatible con S3).

    El dominio solo conoce claves de objeto dentro de `bucket`; la implementación
    concreta (MinIO hoy) es intercambiable sin cambiar los contratos.

    Raises:
        AssetStorageUnavailableError: si el almacenamiento no responde de forma utilizable.
    """

    bucket: str

    def head(self, key: str) -> StoredObject | None:
        """Metadatos del objeto o `None` si no existe."""
        ...

    def exists(self, key: str) -> bool:
        """Indica si el objeto existe."""
        ...

    def get(self, key: str) -> tuple[StoredObject, Iterator[bytes]] | None:
        """Metadatos y contenido del objeto en trozos (streaming); `None` si no existe."""
        ...

    def put(self, key: str, data: bytes, *, content_type: str, metadata: dict[str, str] | None = None) -> StoredObject:
        """Guarda el objeto (idempotente por clave)."""
        ...

    def put_if_absent(
        self, key: str, data: bytes, *, content_type: str, metadata: dict[str, str] | None = None
    ) -> bool:
        """Guarda el objeto solo si la clave no existe (escritura condicional, spec 024 FR-024-16).

        Devuelve `True` si lo escribió y `False` si ya existía; **nunca** reemplaza un objeto existente.
        """
        ...

    def list_keys(self, prefix: str) -> Iterator[str]:
        """Claves bajo un prefijo, en solo lectura (reconciliación de la spec 024, FR-024-30)."""
        ...
