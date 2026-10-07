"""Respuestas de valoración (`contracts/rest-api.md` rutas 29–31; 013)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from inventory_service.api.schemas.queries import PageQuery
from inventory_service.domain.quantities import format_decimal, format_money, optional_decimal


class LayersQuery(PageQuery):
    include_closed: bool = False


class ProductValuation(BaseModel):
    company_product_id: UUID
    quantity: str
    inventory_value: str
    average_unit_cost: str | None
    open_layers: int
    has_unknown_cost: bool


class BranchValuationResponse(BaseModel):
    items: list[ProductValuation]
    total_value: str
    has_unknown_cost: bool
    """Algún producto de la sucursal conserva capas abiertas sin costo histórico."""
    page: int
    page_size: int
    total_records: int

    @classmethod
    def of(cls, result, page: int, page_size: int) -> BranchValuationResponse:
        return cls(
            items=[
                ProductValuation(
                    company_product_id=row.company_product_id,
                    quantity=format_decimal(row.quantity),
                    inventory_value=format_money(row.inventory_value),
                    average_unit_cost=optional_decimal(row.average_unit_cost),
                    open_layers=row.open_layers,
                    has_unknown_cost=row.has_unknown_cost,
                )
                for row in result.items
            ],
            total_value=format_money(result.total_value),
            has_unknown_cost=result.has_unknown_cost,
            page=page,
            page_size=page_size,
            total_records=result.total_records,
        )


class CostLayer(BaseModel):
    id: UUID
    layer_kind: str
    origin_movement_id: UUID | None
    original_quantity: str
    remaining_quantity: str
    unit_cost: str
    cost_known: bool
    """`false` solo en una apertura sin costo histórico; distinto de un costo real 0."""
    currency_code: str | None
    """Nulo solo en aperturas creadas por la migración (moneda no registrada al migrar)."""
    received_at: datetime
    status: str

    @classmethod
    def of(cls, row) -> CostLayer:
        return cls(
            id=row.id,
            layer_kind=row.layer_kind,
            origin_movement_id=row.origin_movement_id,
            original_quantity=format_decimal(row.original_quantity),
            remaining_quantity=format_decimal(row.remaining_quantity),
            unit_cost=format_decimal(row.unit_cost),
            cost_known=row.cost_known,
            currency_code=row.currency_code,
            received_at=row.received_at,
            status=row.status,
        )


class LayersPage(BaseModel):
    items: list[CostLayer]
    page: int
    page_size: int
    total_records: int


class CostConsumption(BaseModel):
    id: UUID
    cost_layer_id: UUID
    consumption_type: str
    quantity: str
    unit_cost: str
    cost_amount: str
    cost_known: bool
    restores_consumption_id: UUID | None


class CostConsumptionsResponse(BaseModel):
    movement_id: UUID
    items: list[CostConsumption]

    @classmethod
    def of(cls, movement_id: UUID, rows) -> CostConsumptionsResponse:
        return cls(
            movement_id=movement_id,
            items=[
                CostConsumption(
                    id=row.id,
                    cost_layer_id=row.cost_layer_id,
                    consumption_type=row.consumption_type,
                    quantity=format_decimal(row.quantity),
                    unit_cost=format_decimal(row.unit_cost),
                    cost_amount=format_money(row.cost_amount),
                    cost_known=row.cost_known,
                    restores_consumption_id=row.restores_consumption_id,
                )
                for row in rows
            ],
        )
