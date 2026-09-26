"""Filtros de la colección de sucursales (FR-023)."""

from uuid import UUID

from fastapi import Query

from operational_context_service.application.ports import BranchFilters
from operational_context_service.domain.status import EntityStatus


def branch_filters(
    search: str | None = Query(
        default=None,
        max_length=160,
        description="Búsqueda parcial, sin distinguir mayúsculas, en código y nombre.",
    ),
    status: EntityStatus = Query(
        default="ACTIVE",
        description="Estado de uso; por defecto solo sucursales ACTIVE.",
    ),
    city_id: UUID | None = Query(default=None),
) -> BranchFilters:
    """Construye los filtros de la colección de sucursales."""
    cleaned = search.strip() if search else None

    return BranchFilters(status=status, city_id=city_id, search=cleaned or None)
