"""Filtros de la colección de usuarios operativos (FR-015)."""

from uuid import UUID

from fastapi import Query

from operational_context_service.application.ports import ApplicationUserFilters
from operational_context_service.domain.status import EntityStatus


def application_user_filters(
    status: EntityStatus = Query(
        default="ACTIVE",
        description="Estado de la membresía; por defecto solo ACTIVE.",
    ),
    search: str | None = Query(
        default=None,
        max_length=160,
        description="Búsqueda parcial, sin distinguir mayúsculas, en nombre y correo de referencia.",
    ),
    keycloak_user_id: str | None = Query(default=None, max_length=255),
    person_identity_id: UUID | None = Query(default=None),
) -> ApplicationUserFilters:
    """Construye los filtros de la colección de usuarios operativos."""
    return ApplicationUserFilters(
        status=status,
        search=search.strip() or None if search else None,
        keycloak_user_id=keycloak_user_id.strip() or None if keycloak_user_id else None,
        person_identity_id=person_identity_id,
    )
