"""Puertos de la capa de aplicación (Principio XV).

Los repositorios del servicio son adaptadores SQLAlchemy concretos que reciben
la sesión; el único puerto hacia otro servicio es `ManufacturerDirectory`, que
permite sustituir Party Identity en pruebas.
"""

from __future__ import annotations

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
