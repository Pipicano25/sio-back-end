"""Filtros HTTP disponibles para países globales."""

from __future__ import annotations

from fastapi import Query

from geography_service.domain.global_country import (
    GlobalCountryStatus,
)


class GlobalCountryFilters:
    """Representa los filtros disponibles para países globales.

    Attributes:
        search: Texto libre para buscar por nombre o códigos ISO.
        iso2_code: Código ISO alpha-2 utilizado como filtro exacto.
        iso3_code: Código ISO alpha-3 utilizado como filtro exacto.
        status: Estado funcional utilizado como filtro exacto.
    """

    def __init__(
        self,
        search: str | None = Query(
            default=None,
            max_length=120,
            description="Busca parcialmente por nombre, ISO2 o ISO3.",
        ),
        iso2_code: str | None = Query(
            default=None,
            min_length=2,
            max_length=2,
            description="Filtra exactamente por código ISO alpha-2.",
        ),
        iso3_code: str | None = Query(
            default=None,
            min_length=3,
            max_length=3,
            description="Filtra exactamente por código ISO alpha-3.",
        ),
        status: GlobalCountryStatus | None = Query(
            default=None,
            description="Filtra por estado funcional.",
        ),
    ) -> None:
        """Inicializa los filtros de países.

        Args:
            search: Texto libre de búsqueda.
            iso2_code: Código ISO alpha-2 exacto.
            iso3_code: Código ISO alpha-3 exacto.
            status: Estado funcional exacto.
        """
        self.search = (
            search.strip()
            if search and search.strip()
            else None
        )
        self.iso2_code = (
            iso2_code.upper()
            if iso2_code
            else None
        )
        self.iso3_code = (
            iso3_code.upper()
            if iso3_code
            else None
        )
        self.status = status
