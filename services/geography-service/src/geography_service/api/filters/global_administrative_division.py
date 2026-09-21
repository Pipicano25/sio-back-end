"""Filtros HTTP para divisiones administrativas globales."""

from __future__ import annotations

from uuid import UUID

from fastapi import Query

from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
)


class GlobalAdministrativeDivisionFilters:
    """Representa filtros para divisiones administrativas.

    Attributes:
        search: Texto libre para buscar por código o nombre.
        country_id: País propietario de la división.
        parent_division_id: División administrativa superior.
        division_type: Tipo administrativo.
        status: Estado funcional.
    """

    def __init__(
        self,
        search: str | None = Query(
            default=None,
            max_length=160,
            description="Busca parcialmente por código o nombre.",
        ),
        country_id: UUID | None = Query(
            default=None,
            description="Filtra por país.",
        ),
        parent_division_id: UUID | None = Query(
            default=None,
            description="Filtra por división administrativa superior.",
        ),
        division_type: AdministrativeDivisionType | None = Query(
            default=None,
            description="Filtra por tipo de división.",
        ),
        status: AdministrativeDivisionStatus | None = Query(
            default=None,
            description="Filtra por estado funcional.",
        ),
    ) -> None:
        """Inicializa los filtros de divisiones administrativas.

        Args:
            search: Texto libre de búsqueda.
            country_id: Identificador del país.
            parent_division_id: Identificador de la división superior.
            division_type: Tipo administrativo.
            status: Estado funcional.
        """
        self.search = (
            search.strip()
            if search and search.strip()
            else None
        )
        self.country_id = country_id
        self.parent_division_id = parent_division_id
        self.division_type = division_type
        self.status = status
