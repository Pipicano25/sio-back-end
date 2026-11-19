"""Auditoría, versión esperada y transiciones de estado comunes (Principios VI y VII, D7)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from product_catalog_service.application.exceptions import VersionConflictError

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"


def utc_now() -> datetime:
    """Fecha y hora actual con zona horaria (UTC)."""
    return datetime.now(UTC)


def stamp_create(entity: Any, actor: str) -> None:
    """Fija la auditoría de creación con la identidad autenticada."""
    now = utc_now()
    entity.created_at = now
    entity.updated_at = now
    entity.created_by = actor
    entity.updated_by = actor


def stamp_update(entity: Any, actor: str) -> None:
    """Fija la auditoría de modificación; `created_by` no cambia."""
    entity.updated_at = utc_now()
    entity.updated_by = actor


class _Unset:
    """Marca de «campo no enviado» en un `PUT` parcial (constitución 4.0.0, D28)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Any = _Unset()


def keep(entity: Any, field: str, value: Any) -> Any:
    """Valor a aplicar: el recibido o, si no se envió, el guardado (D28)."""
    return getattr(entity, field) if value is UNSET else value


def check_version(entity: Any, expected_version: int | None) -> None:
    """Rechaza la operación si se envió una versión y no es la vigente (409).

    Sin versión gana la última escritura (constitución 4.0.0, D9).
    """
    if expected_version is not None and entity.version != expected_version:
        raise VersionConflictError()


def deactivate(entity: Any, expected_version: int | None, actor: str) -> bool:
    """Inactiva el registro; limpia `is_primary`/`is_base`. Devuelve si cambió."""
    check_version(entity, expected_version)

    if entity.status == INACTIVE:
        return False

    entity.status = INACTIVE
    for flag in ("is_primary", "is_base"):
        if hasattr(entity, flag):
            setattr(entity, flag, False)
    stamp_update(entity, actor)
    return True


def reactivate(entity: Any, expected_version: int | None, actor: str) -> bool:
    """Reactiva el registro sin restaurar `is_primary` ni `is_base` (FR-006)."""
    check_version(entity, expected_version)

    if entity.status == ACTIVE:
        return False

    entity.status = ACTIVE
    stamp_update(entity, actor)
    return True
