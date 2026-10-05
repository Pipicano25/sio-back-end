"""Filtros del listado de precios de lista (FR-057).

Sin `status` solo se devuelven registros `ACTIVE`; `status=ALL` devuelve todos (FR-004).
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Query
from pydantic import AwareDatetime

StatusFilter = Literal["ACTIVE", "INACTIVE", "ALL"]


class PriceListItemFilters:
    """Estado, lista, producto, presentación y vigentes en un instante (FR-057)."""

    def __init__(
        self,
        status: StatusFilter | None = Query(default=None),
        price_list_id: UUID | None = Query(default=None),
        company_product_id: UUID | None = Query(default=None),
        company_product_presentation_id: UUID | None = Query(default=None),
        applicable_at: AwareDatetime | None = Query(default=None),
    ) -> None:
        self.search = None
        self.status = status
        self.applicable_at = applicable_at
        self.columns: dict[str, Any] = {
            "price_list_id": price_list_id,
            "company_product_id": company_product_id,
            "company_product_presentation_id": company_product_presentation_id,
        }
