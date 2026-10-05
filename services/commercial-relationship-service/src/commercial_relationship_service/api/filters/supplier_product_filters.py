"""Filtros del listado de productos de proveedor (FR-028).

Sin `status` solo se devuelven registros `ACTIVE`; `status=ALL` devuelve todos (FR-004).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query

from commercial_relationship_service.api.filters.common import normalize_search

StatusFilter = Literal["ACTIVE", "INACTIVE", "ALL"]


class SupplierProductFilters:
    """`search` (código del proveedor), estado, referencias y preferido (FR-028)."""

    def __init__(
        self,
        search: str | None = Query(default=None, max_length=100),
        status: StatusFilter | None = Query(default=None),
        company_supplier_id: UUID | None = Query(default=None),
        company_product_id: UUID | None = Query(default=None),
        company_product_presentation_id: UUID | None = Query(default=None),
        is_preferred: bool | None = Query(default=None),
    ) -> None:
        self.search = normalize_search(search)
        self.status = status
        self.columns: dict[str, Any] = {
            "company_supplier_id": company_supplier_id,
            "company_product_id": company_product_id,
            "company_product_presentation_id": company_product_presentation_id,
            "is_preferred": is_preferred,
        }
