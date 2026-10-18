"""Esquema de `inventory-summary` (FR-022-55 a FR-022-57; contrato §4.4).

Indicadores **operativos** por propietario (D-022-11): `adopted_products` lo cuenta CR (solo empresa) y los demás
los calcula Inventory (INV-3), por sucursal y consolidado. **No** hay `quantities_by_base_unit` (D-022-10),
`products_out_of_stock` (D-022-11), costos ni valoración económica (fuera del alcance de la spec 022, decisión
del 2026-10-17).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from product_inventory_query_service.api.schemas.product_overview import Out


class SummaryCountsOut(Out):
    products_with_positive_balance: int
    products_with_zero_balance: int = Field(description="Saldos registrados en cero; nunca productos sin registro.")
    products_with_policy: int
    products_below_minimum: int


class BranchSummaryOut(Out):
    branch_id: UUID
    products_with_positive_balance: int
    products_with_zero_balance: int
    products_with_policy: int
    products_below_minimum: int


class InventorySummaryOut(Out):
    company_id: UUID
    resolved_at: datetime
    adopted_products: int = Field(description="Productos `ACTIVE` con control de inventario (Commercial "
                                              "Relationship); solo a nivel de empresa.")
    branches: list[BranchSummaryOut]
    consolidated: SummaryCountsOut
