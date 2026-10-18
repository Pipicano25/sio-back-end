"""Esquemas de las agregaciones de ventas para reportes (spec 023, SAL-R1 y SAL-R2).

Decimales como cadena (como el resto de Sales): cantidades con 4 decimales e importes con 2. Sin costos ni
márgenes: la rentabilidad no forma parte de estas agregaciones (fase 2 de la spec 023).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from sales_service.api.schemas.sales import MONEY, QUANTITY, StrictModel, fmt

MAX_PERIOD_DAYS = 366
MAX_BRANCHES = 100


class AggregateQuery(StrictModel):
    date_from: date
    date_to: date
    branch_id: Annotated[list[UUID], Field(max_length=MAX_BRANCHES)] = []

    @model_validator(mode="after")
    def _period(self) -> "AggregateQuery":
        if self.date_to < self.date_from:
            raise PydanticCustomError("INVALID_DATE_RANGE", "La fecha final no puede ser anterior a la inicial.")
        if (self.date_to - self.date_from).days + 1 > MAX_PERIOD_DAYS:
            raise PydanticCustomError("PERIOD_TOO_LONG", "El período no puede superar 366 días.")
        return self

    @property
    def branch_ids(self) -> list[UUID]:
        return list(dict.fromkeys(self.branch_id))


class ByProductQuery(AggregateQuery):
    order_by: Literal["quantity_base", "amount"] = "quantity_base"
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    include_presentations: bool = False


class PresentationAggregateOut(BaseModel):
    company_product_presentation_id: UUID | None
    code: str | None
    name: str | None
    quantity: str
    quantity_base: str
    amount: str


class ProductAggregateOut(BaseModel):
    company_product_id: UUID
    product_code: str
    product_name: str
    currency_code: str
    quantity_base: str
    amount: str
    sales_count: int
    presentations: list[PresentationAggregateOut] | None = None

    @classmethod
    def of(cls, row) -> "ProductAggregateOut":
        return cls(
            company_product_id=row.company_product_id,
            product_code=row.product_code,
            product_name=row.product_name,
            currency_code=row.currency_code,
            quantity_base=fmt(row.quantity_base, QUANTITY),
            amount=fmt(row.amount, MONEY),
            sales_count=row.sales_count,
            presentations=None if row.presentations is None else [
                PresentationAggregateOut(
                    company_product_presentation_id=item.company_product_presentation_id,
                    code=item.code,
                    name=item.name,
                    quantity=fmt(item.quantity, QUANTITY),
                    quantity_base=fmt(item.quantity_base, QUANTITY),
                    amount=fmt(item.amount, MONEY),
                )
                for item in row.presentations
            ],
        )


class CurrencyTotalOut(BaseModel):
    currency_code: str
    amount: str
    sales_count: int


class ByProductOut(BaseModel):
    company_id: UUID
    date_from: date
    date_to: date
    branch_ids: list[UUID]
    sales_status: Literal["CONFIRMED"] = "CONFIRMED"
    order_by: str
    items: list[ProductAggregateOut]
    totals: list[CurrencyTotalOut]


class BranchAggregateOut(BaseModel):
    branch_id: UUID
    currency_code: str
    sales_count: int
    total_amount: str


class BranchTotalOut(BaseModel):
    currency_code: str
    sales_count: int
    total_amount: str


class ByBranchOut(BaseModel):
    company_id: UUID
    date_from: date
    date_to: date
    branch_ids: list[UUID]
    sales_status: Literal["CONFIRMED"] = "CONFIRMED"
    items: list[BranchAggregateOut]
    totals: list[BranchTotalOut]
