"""Esquemas de las compras del período para reportes (spec 023, PUR-R1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from purchase_service.api.schemas.purchases import MONEY, StrictModel, fmt, receipt_status

MAX_PERIOD_DAYS = 366

Category = Literal["RECEIVED", "PENDING_RECEIPT", "CANCELLED"]


class PeriodQuery(StrictModel):
    date_from: date
    date_to: date
    branch_id: Annotated[list[UUID], Field(max_length=100)] = []
    category: Annotated[list[Category], Field(max_length=3)] = []
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 50

    @model_validator(mode="after")
    def _period(self) -> "PeriodQuery":
        if self.date_to < self.date_from:
            raise PydanticCustomError("INVALID_DATE_RANGE", "La fecha final no puede ser anterior a la inicial.")
        if (self.date_to - self.date_from).days + 1 > MAX_PERIOD_DAYS:
            raise PydanticCustomError("PERIOD_TOO_LONG", "El período no puede superar 366 días.")
        return self


class PeriodPurchaseOut(BaseModel):
    id: UUID
    operation_date: date
    received_at: datetime | None
    branch_id: UUID
    supplier_name: str
    supplier_identification: str
    number: str | None
    supplier_document_number: str | None
    status: str
    category: Category
    receipt_status: str | None
    currency_code: str
    total: str

    @classmethod
    def of(cls, row) -> "PeriodPurchaseOut":
        return cls(
            id=row.id, operation_date=row.operation_date, received_at=row.received_at, branch_id=row.branch_id,
            supplier_name=row.supplier_name_snapshot, supplier_identification=row.supplier_identification_snapshot,
            number=row.number, supplier_document_number=row.supplier_document_number, status=row.status,
            category=row.category, receipt_status=receipt_status(row.status, row.received_at),
            currency_code=row.currency_code, total=fmt(row.total, MONEY),
        )


class PeriodTotalsOut(BaseModel):
    currency_code: str
    received_count: int
    received_total: str
    pending_receipt_count: int
    pending_receipt_total: str
    cancelled_count: int
    cancelled_total: str
    effective_total: str


class PeriodPage(BaseModel):
    company_id: UUID
    date_from: date
    date_to: date
    branch_ids: list[UUID]
    items: list[PeriodPurchaseOut]
    totals: list[PeriodTotalsOut]
    page: int
    page_size: int
    total_records: int
    total_pages: int
