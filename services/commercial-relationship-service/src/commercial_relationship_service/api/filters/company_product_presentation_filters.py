"""Filtros del listado de presentaciones empresariales (FR-016).

Sin `status` solo se devuelven registros `ACTIVE`; `status=ALL` devuelve todos (FR-004).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search

StatusFilter = Literal["ACTIVE", "INACTIVE", "ALL"]


class CompanyProductPresentationFilters:
    """`search` (código interno, SKU, referencia), estado, producto y banderas (FR-016)."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: StatusFilter | None = Query(default=None),
        company_product_id: UUID | None = Query(default=None),
        global_product_presentation_id: UUID | None = Query(default=None),
        is_purchasable: bool | None = Query(default=None),
        is_sellable: bool | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {
            "company_product_id": company_product_id,
            "global_product_presentation_id": global_product_presentation_id,
            "is_purchasable": is_purchasable,
            "is_sellable": is_sellable,
        }
