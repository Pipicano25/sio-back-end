"""Filtros HTTP disponibles para ciudades globales."""

from __future__ import annotations

from uuid import UUID

from fastapi import Query

from geography_service.domain.global_city import (
    GlobalCityStatus,
)


class GlobalCityFilters:
    """Representa los filtros disponibles para ciudades globales.

    Attributes:
        search: Texto libre para buscar por código o nombre.
        country_id: País propietario de la ciudad.
        administrative_division_id: División administrativa asociada.
        code: Código exacto de la ciudad.
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
        administrative_division_id: UUID | None = Query(
            default=None,
            description="Filtra por división administrativa.",
        ),
        code: str | None = Query(
            default=None,
            max_length=40,
            description="Filtra exactamente por código.",
        ),
        status: GlobalCityStatus | None = Query(
            default=None,
            description="Filtra por estado funcional.",
        ),
    ) -> None:
        """Inicializa los filtros de ciudades.

        Args:
            search: Texto libre de búsqueda.
            country_id: Identificador del país.
            administrative_division_id: División administrativa asociada.
            code: Código exacto.
            status: Estado funcional.
        """
        self.search = (
            search.strip()
            if search and search.strip()
            else None
        )
        self.country_id = country_id
        self.administrative_division_id = (
            administrative_division_id
        )
        self.code = (
            code.strip()
            if code and code.strip()
            else None
        )
        self.status = status
