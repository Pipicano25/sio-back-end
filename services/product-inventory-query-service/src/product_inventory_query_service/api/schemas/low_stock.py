"""Esquema `LowStockPair` de `low-stock-products` (FR-022-51; contrato §4.3). Sin costos (FR-022-15)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from product_inventory_query_service.api.schemas.product_overview import Out, ReferenceOut


class LowStockPair(Out):
    """Par (producto, sucursal) con existencia **estrictamente menor** que el mínimo activo (FR-022-50)."""

    company_product_id: UUID
    display_name: str
    internal_code: str
    base_unit: ReferenceOut | None
    branch_id: UUID
    base_quantity: str
    minimum_stock: str
    shortfall: str = Field(description="`minimum_stock − base_quantity`, siempre mayor que cero.")
    policy_status: Literal["ACTIVE"]
