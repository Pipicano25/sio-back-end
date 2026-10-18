"""Esquemas de respuesta JSON de los reportes de la fase 1 (`contracts/business-reporting-api.md` §3).

Decimales como cadena: cantidades con 4 decimales, importes con 2 y porcentajes con 4.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

QUANTITY = Decimal("0.0001")
MONEY = Decimal("0.01")


def qty(value: Decimal) -> str:
    return format(Decimal(value).quantize(QUANTITY, ROUND_HALF_UP), "f")


def money(value: Decimal) -> str:
    return format(Decimal(value).quantize(MONEY, ROUND_HALF_UP), "f")


class UnitOut(BaseModel):
    id: UUID
    code: str
    name: str


class ReportHeader(BaseModel):
    report: str
    company_id: UUID
    date_from: date
    date_to: date
    generated_at: datetime
    criteria: dict[str, Any]


# R1


class PresentationOut(BaseModel):
    company_product_presentation_id: UUID | None
    code: str | None
    name: str | None
    quantity: str
    quantity_base: str
    amount: str


class TopProductOut(BaseModel):
    rank: int
    company_product_id: UUID
    product_code: str
    product_name: str
    base_unit: UnitOut | None
    quantity_base: str
    currency_code: str
    amount: str
    sales_count: int
    presentations: list[PresentationOut] | None = None


class SalesTotalOut(BaseModel):
    currency_code: str
    amount: str
    sales_count: int


class TopProductsOut(ReportHeader):
    branch_ids: list[UUID]
    mixed_base_units: bool
    items: list[TopProductOut]
    totals: list[SalesTotalOut]


# R2


class BranchSalesOut(BaseModel):
    branch_id: UUID
    branch_code: str
    branch_name: str
    currency_code: str
    sales_count: int
    total_amount: str
    share_percentage: str


class BranchTotalOut(BaseModel):
    currency_code: str
    sales_count: int
    total_amount: str


class SalesByBranchOut(ReportHeader):
    branch_ids: list[UUID]
    items: list[BranchSalesOut]
    totals: list[BranchTotalOut]


class BranchOnlySalesOut(BaseModel):
    currency_code: str
    sales_count: int
    total_amount: str


class BranchSalesReportOut(ReportHeader):
    """Ventas de una sola sucursal (ruta por sucursal): sin participación, porque no hay comparación."""

    branch_id: UUID
    branch_code: str
    branch_name: str
    items: list[BranchOnlySalesOut]


# R3


class PurchaseOut(BaseModel):
    purchase_id: UUID
    operation_date: date
    received_at: datetime | None
    branch_id: UUID
    branch_name: str
    supplier_name: str
    supplier_identification: str
    number: str | None
    supplier_document_number: str | None
    status: str
    category: str
    receipt_status: str | None
    currency_code: str
    total: str


class PurchaseTotalsOut(BaseModel):
    currency_code: str
    received_count: int
    received_total: str
    pending_receipt_count: int
    pending_receipt_total: str
    cancelled_count: int
    cancelled_total: str
    effective_total: str


class PurchasesOut(ReportHeader):
    branch_ids: list[UUID]
    items: list[PurchaseOut]
    totals: list[PurchaseTotalsOut]
    page: int
    page_size: int
    total_records: int
    total_pages: int


# R4


class StockEvolutionOut(BaseModel):
    company_product_id: UUID
    product_code: str | None
    product_name: str
    base_unit: UnitOut | None
    opening_quantity: str
    entries: str
    outputs: str
    entry_reversals: str
    output_reversals: str
    positive_adjustments: str
    negative_adjustments: str
    closing_quantity: str
    movement_count: int


class StockEvolutionReportOut(ReportHeader):
    branch_id: UUID
    branch_code: str
    branch_name: str
    timezone: str
    items: list[StockEvolutionOut]
    page: int
    page_size: int
    total_records: int
    total_pages: int


class ConsolidatedStockOut(StockEvolutionOut):
    branch_count: int


class CompanyStockEvolutionOut(ReportHeader):
    """Evolución consolidada por producto en las sucursales del alcance (INV-R1C). Sin costos."""

    branch_ids: list[UUID]
    timezone: str
    items: list[ConsolidatedStockOut]
    page: int
    page_size: int
    total_records: int
    total_pages: int


def total_pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 0
