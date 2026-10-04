"""Filtros del listado de productos empresariales (FR-017)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search


class CompanyProductFilters:
    """`search` (código interno, referencia, nombre), `status` y banderas."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: Literal["ACTIVE", "INACTIVE", "ALL"] | None = Query(default=None),
        is_purchasable: bool | None = Query(default=None),
        is_sellable: bool | None = Query(default=None),
        inventory_control_enabled: bool | None = Query(default=None),
        global_product_id: UUID | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {
            "is_purchasable": is_purchasable,
            "is_sellable": is_sellable,
            "inventory_control_enabled": inventory_control_enabled,
            "global_product_id": global_product_id,
        }
