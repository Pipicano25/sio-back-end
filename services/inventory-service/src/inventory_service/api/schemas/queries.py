"""Parámetros y respuestas de las consultas (`contracts/rest-api.md` rutas 5 a 10)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator
from pydantic_core import PydanticCustomError

from inventory_service.domain.quantities import format_decimal, format_money, optional_decimal, optional_money

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_LOOKUP = 100


class PageQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @field_validator("page")
    @classmethod
    def _page(cls, value: int) -> int:
        if value < 1:
            raise PydanticCustomError("INVALID_FORMAT", "La página debe ser mayor o igual que 1.")
        return value

    @field_validator("page_size")
    @classmethod
    def _page_size(cls, value: int) -> int:
        if not 1 <= value <= MAX_PAGE_SIZE:
            raise PydanticCustomError("PAGE_SIZE_OUT_OF_RANGE", f"El tamaño de página debe estar entre 1 y {MAX_PAGE_SIZE}.")
        return value


class BalancesQuery(PageQuery):
    company_product_id: UUID | None = None
    in_stock_only: bool = False


class KardexQuery(PageQuery):
    occurred_at_from: AwareDatetime | None = None
    occurred_at_to: AwareDatetime | None = None
    movement_type: str | None = None
    origin_type: str | None = None
    origin_id: UUID | None = None

    @model_validator(mode="after")
    def _range(self) -> KardexQuery:
        if self.occurred_at_from and self.occurred_at_to and self.occurred_at_from > self.occurred_at_to:
            raise PydanticCustomError("INVALID_DATE_RANGE", "`occurred_at_from` no puede ser posterior a `occurred_at_to`.")
        return self


class BalanceLookupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_product_ids: list[UUID]

    @field_validator("company_product_ids", mode="before")
    @classmethod
    def _size(cls, value: Any) -> Any:
        if isinstance(value, list) and not 1 <= len(value) <= MAX_LOOKUP:
            raise PydanticCustomError("INVALID_FORMAT", f"Debe tener entre 1 y {MAX_LOOKUP} productos.")
        return value


class BalanceResponse(BaseModel):
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    quantity: str
    last_movement_at: datetime | None
    balance_sequence: int
    inventory_value: str
    average_unit_cost: str | None
    has_unknown_cost: bool

    @classmethod
    def of(cls, company_id: UUID, branch_id: UUID, product_id: UUID, row: Any | None) -> BalanceResponse:
        if row is None:
            return cls(
                company_id=company_id,
                branch_id=branch_id,
                company_product_id=product_id,
                quantity="0.0000",
                last_movement_at=None,
                balance_sequence=0,
                inventory_value="0.00",
                average_unit_cost=None,
                has_unknown_cost=False,
            )
        return cls(
            company_id=row.company_id,
            branch_id=row.branch_id,
            company_product_id=row.company_product_id,
            quantity=format_decimal(row.quantity),
            last_movement_at=row.updated_at if row.version > 0 else None,
            balance_sequence=row.version,
            inventory_value=format_money(row.inventory_value),
            average_unit_cost=optional_decimal(row.average_unit_cost),
            has_unknown_cost=row.has_unknown_cost,
        )


class BalancePage(BaseModel):
    items: list[BalanceResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int


class BalanceLookupResponse(BaseModel):
    items: list[BalanceResponse]


class KardexMovement(BaseModel):
    id: UUID
    operation_id: UUID
    line_index: int
    origin_detail_id: UUID
    company_product_id: UUID
    movement_type: str
    quantity: str
    previous_balance: str
    new_balance: str
    balance_sequence: int
    unit_cost: str | None
    movement_value: str | None
    cost_known: bool | None
    reversed_movement_id: UUID | None
    origin_type: str
    origin_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: str | None
    created_at: datetime
    created_by: str

    @classmethod
    def of(cls, row: Any) -> KardexMovement:
        return cls(
            id=row.id,
            operation_id=row.operation_id,
            line_index=row.line_index,
            origin_detail_id=row.origin_detail_id,
            company_product_id=row.company_product_id,
            movement_type=row.movement_type,
            quantity=format_decimal(row.quantity),
            previous_balance=format_decimal(row.previous_balance),
            new_balance=format_decimal(row.new_balance),
            balance_sequence=row.balance_sequence,
            unit_cost=optional_decimal(row.unit_cost),
            movement_value=optional_money(row.movement_value),
            cost_known=row.cost_known,
            reversed_movement_id=row.reversed_movement_id,
            origin_type=row.origin_type,
            origin_id=row.origin_id,
            application_user_id=row.application_user_id,
            correlation_id=row.correlation_id,
            reason=row.reason,
            created_at=row.created_at,
            created_by=row.created_by,
        )


class KardexPage(BaseModel):
    items: list[KardexMovement]
    page: int
    page_size: int
    total_records: int
    total_pages: int


def total_pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 0
