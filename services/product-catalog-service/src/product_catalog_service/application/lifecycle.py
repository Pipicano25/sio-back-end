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


def check_version(entity: Any, expected_version: int) -> None:
    """Rechaza la operación si la versión esperada no es la vigente (409)."""
    if entity.version != expected_version:
        raise VersionConflictError()


def deactivate(entity: Any, expected_version: int, actor: str) -> bool:
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


def reactivate(entity: Any, expected_version: int, actor: str) -> bool:
    """Reactiva el registro sin restaurar `is_primary` ni `is_base` (FR-006)."""
    check_version(entity, expected_version)

    if entity.status == ACTIVE:
        return False

    entity.status = ACTIVE
    stamp_update(entity, actor)
    return True
