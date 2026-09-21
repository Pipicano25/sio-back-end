"""Filtros HTTP para identidades globales de personas."""

from __future__ import annotations

from uuid import UUID

from fastapi import Query

from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonVerificationStatus,
)


class PersonIdentityFilters:
    """Representa filtros disponibles para identidades de persona."""

    def __init__(
        self,
        search: str | None = Query(
            default=None,
            max_length=120,
            description=(
                "Busca parcialmente por identificación o nombres."
            ),
        ),
        identification_country_id: UUID | None = Query(
            default=None,
            description="Filtra por país externo de identificación.",
        ),
        identification_type: PersonIdentificationType | None = Query(
            default=None,
            description="Filtra por tipo de identificación.",
        ),
        verification_status: PersonVerificationStatus | None = Query(
            default=None,
            description="Filtra por estado de verificación.",
        ),
    ) -> None:
        """Inicializa los filtros de persona."""
        self.search = (
            search.strip()
            if search and search.strip()
            else None
        )
        self.identification_country_id = identification_country_id
        self.identification_type = identification_type
        self.verification_status = verification_status
