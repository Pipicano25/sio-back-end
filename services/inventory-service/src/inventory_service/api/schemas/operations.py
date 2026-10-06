"""Esquemas de operaciones, reversos y respuestas (`contracts/rest-api.md`).

Entrada: `extra="forbid"` (campo desconocido → `422 UNKNOWN_FIELD`); cantidades y
costos con las reglas de `domain.quantities` y su causa en `errors[].code`.
Salida: cantidades y costos como cadena con 4 decimales (R-10).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from inventory_service.domain.quantities import QuantityError, format_decimal, parse_quantity, parse_unit_cost

MAX_LINES = 100
REASON_MAX_LENGTH = 2000


def _quantity(value: Any) -> Decimal:
    try:
        return parse_quantity(value)
    except QuantityError as error:
        raise PydanticCustomError(error.code, error.message) from None


def _unit_cost(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return parse_unit_cost(value)
    except QuantityError as error:
        raise PydanticCustomError(error.code, error.message) from None


def _reason(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise PydanticCustomError("INVALID_FORMAT", "El motivo debe ser un texto no vacío.")
    if len(value.strip()) > REASON_MAX_LENGTH:
        raise PydanticCustomError("INVALID_FORMAT", f"El motivo admite a lo sumo {REASON_MAX_LENGTH} caracteres.")
    return value.strip()


Quantity = Annotated[Decimal, BeforeValidator(_quantity)]
UnitCost = Annotated[Decimal | None, BeforeValidator(_unit_cost)]
Reason = Annotated[str | None, BeforeValidator(_reason)]


class LineIn(BaseModel):
    """Línea de una operación: cantidad en unidad base (DS-09)."""

    model_config = ConfigDict(extra="forbid")

    origin_detail_id: UUID
    company_product_id: UUID
    quantity: Quantity
    unit_cost: UnitCost = None


class OperationIn(BaseModel):
    """Entrada de compra o salida de venta (FR-010)."""

    model_config = ConfigDict(extra="forbid")

    operation_key: UUID
    company_id: UUID
    branch_id: UUID
    origin_type: str
    origin_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: Reason = None
    lines: list[LineIn]

    @field_validator("lines", mode="before")
    @classmethod
    def _lines_in_range(cls, value: Any) -> Any:
        if isinstance(value, list) and not 1 <= len(value) <= MAX_LINES:
            raise PydanticCustomError("LINES_OUT_OF_RANGE", f"Debe tener entre 1 y {MAX_LINES} líneas.")
        return value


class ReversalIn(BaseModel):
    """Reverso de una operación completa (FR-030): `company_id` obligatorio."""

    model_config = ConfigDict(extra="forbid")

    operation_key: UUID
    company_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: Reason = None


class MovementResponse(BaseModel):
    id: UUID
    line_index: int
    origin_detail_id: UUID
    company_product_id: UUID
    movement_type: str
    quantity: str
    previous_balance: str
    new_balance: str
    balance_sequence: int
    unit_cost: str | None
    reversed_movement_id: UUID | None


class BalanceAfter(BaseModel):
    company_product_id: UUID
    quantity: str


class InventoryOperationResponse(BaseModel):
    id: UUID
    operation_key: UUID
    operation_type: str
    company_id: UUID
    branch_id: UUID
    origin_type: str
    origin_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: str | None
    reverses_operation_id: UUID | None
    reversed_by_operation_id: UUID | None
    created_at: datetime
    created_by: str
    movements: list[MovementResponse]
    balances: list[BalanceAfter] | None = None

    @classmethod
    def from_stored(cls, stored: Any, *, with_balances: bool = True) -> InventoryOperationResponse:
        extra: dict[str, Any] = {}
        if with_balances:
            extra["balances"] = [
                BalanceAfter(company_product_id=product, quantity=format_decimal(quantity))
                for product, quantity in stored.balances_after.items()
            ]
        return cls(
            id=stored.id,
            operation_key=stored.operation_key,
            operation_type=stored.operation_type,
            company_id=stored.company_id,
            branch_id=stored.branch_id,
            origin_type=stored.origin_type,
            origin_id=stored.origin_id,
            application_user_id=stored.application_user_id,
            correlation_id=stored.correlation_id,
            reason=stored.reason,
            reverses_operation_id=stored.reverses_operation_id,
            reversed_by_operation_id=stored.reversed_by_operation_id,
            created_at=stored.created_at,
            created_by=stored.created_by,
            movements=[
                MovementResponse(
                    id=m.id,
                    line_index=m.line_index,
                    origin_detail_id=m.origin_detail_id,
                    company_product_id=m.company_product_id,
                    movement_type=m.movement_type,
                    quantity=format_decimal(m.quantity),
                    previous_balance=format_decimal(m.previous_balance),
                    new_balance=format_decimal(m.new_balance),
                    balance_sequence=m.balance_sequence,
                    unit_cost=format_decimal(m.unit_cost) if m.unit_cost is not None else None,
                    reversed_movement_id=m.reversed_movement_id,
                )
                for m in stored.movements
            ],
            **extra,
        )
