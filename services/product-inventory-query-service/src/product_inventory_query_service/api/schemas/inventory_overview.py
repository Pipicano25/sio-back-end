"""Esquema `InventoryOverview` de `inventory-overviews` (FR-022-40 a FR-022-42; contrato §4.2).

La identificación del producto y sus presentaciones **sin precio**, más `stock` con el detalle por sucursal. Sin
campos de costo (FR-022-15).
"""

from __future__ import annotations

from pydantic import Field

from product_inventory_query_service.api.schemas.product_overview import PresentationOut, ProductIdentity, StockOut


class InventoryOverview(ProductIdentity):
    presentations: list[PresentationOut]
    stock: StockOut | None = Field(default=None, description="Solo con `perm:product-inventory-query:stock:read`.")
