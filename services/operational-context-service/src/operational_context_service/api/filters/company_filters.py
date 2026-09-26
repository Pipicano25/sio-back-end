"""Filtros de la colección de empresas (FR-015). Sin búsqueda por nombre (DS-13)."""

from uuid import UUID

from fastapi import Query

from operational_context_service.application.ports import CompanyFilters
from operational_context_service.domain.status import EntityStatus


def company_filters(
    status: EntityStatus = Query(
        default="ACTIVE",
        description="Estado de uso; por defecto solo empresas ACTIVE.",
    ),
    organization_identity_id: UUID | None = Query(default=None),
    country_id: UUID | None = Query(default=None),
    city_id: UUID | None = Query(default=None),
) -> CompanyFilters:
    """Construye los filtros de la colección de empresas."""
    return CompanyFilters(
        status=status,
        organization_identity_id=organization_identity_id,
        country_id=country_id,
        city_id=city_id,
    )
