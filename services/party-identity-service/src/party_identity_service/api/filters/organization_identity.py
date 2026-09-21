"""Filtros HTTP para identidades globales de organizaciones."""

from __future__ import annotations

from uuid import UUID

from fastapi import Query

from party_identity_service.domain.organization_identity import (
    OrganizationIdentificationType,
)


class OrganizationIdentityFilters:
    """Representa filtros disponibles para identidades de organización."""

    def __init__(
        self,
        search: str | None = Query(
            default=None,
            max_length=120,
            description=(
                "Busca parcialmente por identificación o nombre."
            ),
        ),
        country_id: UUID | None = Query(
            default=None,
            description="Filtra por país externo de registro.",
        ),
        identification_type: OrganizationIdentificationType | None = Query(
            default=None,
            description="Filtra por tipo de identificación.",
        ),
        registration_status: str | None = Query(
            default=None,
            max_length=30,
            description="Filtra por estado legal conocido.",
        ),
    ) -> None:
        """Inicializa los filtros de organización."""
        self.search = (
            search.strip()
            if search and search.strip()
            else None
        )
        self.country_id = country_id
        self.identification_type = identification_type
        self.registration_status = registration_status
