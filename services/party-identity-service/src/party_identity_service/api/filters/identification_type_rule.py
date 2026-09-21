"""Filtros HTTP para reglas de tipos de identificación."""

from __future__ import annotations

from uuid import UUID

from fastapi import Query

from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationSigla,
    PartyKind,
)


class IdentificationTypeRuleFilters:
    """Representa filtros disponibles para reglas de identificación."""

    def __init__(
        self,
        party_kind: PartyKind | None = Query(
            default=None,
            description="Filtra por tipo de parte.",
        ),
        country_id: UUID | None = Query(
            default=None,
            description="Filtra por país externo.",
        ),
        identification_type: IdentificationType | None = Query(
            default=None,
            description="Filtra por tipo de identificación.",
        ),
        sigla: IdentificationSigla | None = Query(
            default=None,
            description="Filtra por sigla oficial del documento.",
        ),
        is_active: bool | None = Query(
            default=None,
            description="Filtra por estado activo o inactivo.",
        ),
    ) -> None:
        """Inicializa los filtros de reglas."""
        self.party_kind = party_kind
        self.country_id = country_id
        self.identification_type = identification_type
        self.sigla = sigla
        self.is_active = is_active
