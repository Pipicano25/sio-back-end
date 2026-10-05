"""Filtros del listado de listas de precios (FR-046).

Sin `status` solo se devuelven registros `ACTIVE`; `status=ALL` devuelve todos (FR-004).
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search

StatusFilter = Literal["ACTIVE", "INACTIVE", "ALL"]


class PriceListFilters:
    """`search` (código, nombre), estado, moneda y predeterminada (FR-046)."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: StatusFilter | None = Query(default=None),
        currency_code: str | None = Query(default=None, min_length=3, max_length=3),
        is_default: bool | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {
            "currency_code": None if currency_code is None else currency_code.upper(),
            "is_default": is_default,
        }
