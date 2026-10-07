"""Esquemas de ajustes (`contracts/rest-api.md` rutas 11–13; 013)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from inventory_service.api.schemas.operations import MovementResponse, Quantity, UnitCost, movement_response
from inventory_service.api.schemas.queries import PageQuery
from inventory_service.domain.quantities import format_decimal, format_money

REASON_MAX_LENGTH = 2000


def required_reason(value: Any) -> str:
    """Motivo obligatorio: texto no vacío de hasta 2 000 caracteres (`REASON_REQUIRED`)."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > REASON_MAX_LENGTH:
        raise PydanticCustomError(
            "REASON_REQUIRED", f"El motivo es obligatorio: un texto de 1 a {REASON_MAX_LENGTH} caracteres."
        )
    return value.strip()


RequiredReason = Annotated[str, BeforeValidator(required_reason)]


class AdjustmentIn(BaseModel):
    """Ajuste manual (FR-030): el usuario operativo sale de `operational-access`, no del cuerpo."""

    model_config = ConfigDict(extra="forbid")

    adjustment_key: UUID
    branch_id: UUID
    company_product_id: UUID
    adjustment_type: Literal["POSITIVE", "NEGATIVE"]
    quantity: Quantity
    unit_cost: UnitCost = None
    reason: RequiredReason = Field(default=None, validate_default=True)


class InventoryAdjustmentResponse(BaseModel):
    id: UUID
    operation_id: UUID
    movement_id: UUID
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    adjustment_type: str
    quantity: str
    reason: str
    previous_balance: str
    new_balance: str
    unit_cost: str
    adjustment_value: str
    inventory_count_id: UUID | None
    application_user_id: UUID
    created_at: datetime
    created_by: str
    movement: MovementResponse

    @classmethod
    def of(cls, row: Any, movement: Any) -> InventoryAdjustmentResponse:
        return cls(
            id=row.id,
            operation_id=row.operation_id,
            movement_id=row.movement_id,
            company_id=row.company_id,
            branch_id=row.branch_id,
            company_product_id=row.company_product_id,
            adjustment_type=row.adjustment_type,
            quantity=format_decimal(row.quantity),
            reason=row.reason,
            previous_balance=format_decimal(row.previous_balance),
            new_balance=format_decimal(row.new_balance),
            unit_cost=format_decimal(row.unit_cost),
            adjustment_value=format_money(row.adjustment_value),
            inventory_count_id=row.inventory_count_id,
            application_user_id=row.application_user_id,
            created_at=row.created_at,
            created_by=row.created_by,
            movement=movement_response(movement),
        )


class AdjustmentQuery(PageQuery):
    branch_id: UUID | None = None
    company_product_id: UUID | None = None
    adjustment_type: Literal["POSITIVE", "NEGATIVE"] | None = None
    inventory_count_id: UUID | None = None
    created_at_from: AwareDatetime | None = None
    created_at_to: AwareDatetime | None = None

    @model_validator(mode="after")
    def _range(self) -> AdjustmentQuery:
        if self.created_at_from and self.created_at_to and self.created_at_from > self.created_at_to:
            raise PydanticCustomError("INVALID_DATE_RANGE", "`created_at_from` no puede ser posterior a `created_at_to`.")
        return self


class AdjustmentPage(BaseModel):
    items: list[InventoryAdjustmentResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int
