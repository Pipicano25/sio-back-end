"""Filtros del historial de asesores (FR-056). Sin `status`: todas las asignaciones."""

from uuid import UUID

from fastapi import Query

from operational_context_service.application.ports import AdvisorFilters
from operational_context_service.domain.status import EntityStatus


def advisor_filters(
    status: EntityStatus | None = Query(
        default=None,
        description="ACTIVE (vigentes) o INACTIVE (cerradas); sin valor, todas.",
    ),
    is_primary: bool | None = Query(default=None),
    person_identity_id: UUID | None = Query(default=None),
) -> AdvisorFilters:
    return AdvisorFilters(status=status, is_primary=is_primary, person_identity_id=person_identity_id)
