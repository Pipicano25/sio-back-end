"""Puertos de las dependencias (Principio XV) y datos que intercambian.

Todas las implementaciones reales usan el **token del usuario** (spec 023, DR-07): cada propietario aplica su
membresía y su permiso de lectura. Las pruebas sustituyen los puertos por dobles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


# --------------------------------------------------------------------------- Operational Context


@dataclass(frozen=True, slots=True)
class BranchInfo:
    id: UUID
    company_id: UUID
    code: str
    name: str
    status: str
    timezone: str


@dataclass(frozen=True, slots=True)
class CompanyInfo:
    id: UUID
    timezone: str
    default_currency: str


class OperationalContextPort(Protocol):
    async def has_company_access(self, company_id: UUID) -> bool: ...
    async def company(self, company_id: UUID) -> CompanyInfo | None: ...
    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]: ...


# --------------------------------------------------------------------------- Sales (SAL-R1, SAL-R2)


@dataclass(frozen=True, slots=True)
class PresentationSales:
    company_product_presentation_id: UUID | None
    code: str | None
    name: str | None
    quantity: Decimal
    quantity_base: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ProductSales:
    company_product_id: UUID
    product_code: str
    product_name: str
    currency_code: str
    quantity_base: Decimal
    amount: Decimal
    sales_count: int
    presentations: list[PresentationSales] | None = None


@dataclass(frozen=True, slots=True)
class SalesTotal:
    currency_code: str
    amount: Decimal
    sales_count: int


@dataclass(frozen=True, slots=True)
class ProductSalesResult:
    items: list[ProductSales]
    totals: list[SalesTotal]


@dataclass(frozen=True, slots=True)
class BranchSales:
    branch_id: UUID
    currency_code: str
    sales_count: int
    total_amount: Decimal


class SalesPort(Protocol):
    async def by_product(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
                         order_by: str, limit: int, include_presentations: bool) -> ProductSalesResult: ...
    async def by_branch(self, company_id: UUID, *, date_from: date, date_to: date,
                        branch_ids: list[UUID]) -> list[BranchSales]: ...


# --------------------------------------------------------------------------- Purchase (PUR-R1)


@dataclass(frozen=True, slots=True)
class PurchaseRow:
    id: UUID
    operation_date: date
    received_at: datetime | None
    branch_id: UUID
    supplier_name: str
    supplier_identification: str
    number: str | None
    supplier_document_number: str | None
    status: str
    category: str
    receipt_status: str | None
    currency_code: str
    total: Decimal


@dataclass(frozen=True, slots=True)
class PurchaseTotals:
    currency_code: str
    received_count: int
    received_total: Decimal
    pending_receipt_count: int
    pending_receipt_total: Decimal
    cancelled_count: int
    cancelled_total: Decimal
    effective_total: Decimal


@dataclass(frozen=True, slots=True)
class PurchasePage:
    items: list[PurchaseRow]
    totals: list[PurchaseTotals]
    total_records: int


class PurchasePort(Protocol):
    async def period(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
                     categories: list[str], page: int, page_size: int) -> PurchasePage: ...


# --------------------------------------------------------------------------- Inventory (INV-R1)


@dataclass(frozen=True, slots=True)
class StockEvolution:
    company_product_id: UUID
    opening_quantity: Decimal
    entries: Decimal
    outputs: Decimal
    entry_reversals: Decimal
    output_reversals: Decimal
    positive_adjustments: Decimal
    negative_adjustments: Decimal
    closing_quantity: Decimal
    movement_count: int
    branch_count: int = 1
    """Sucursales que aportan (INV-R1C); 1 en INV-R1."""

    def balances(self) -> bool:
        """Identidad de existencias (FR-023-32)."""
        return self.closing_quantity == (
            self.opening_quantity + self.entries - self.outputs - self.entry_reversals + self.output_reversals
            + self.positive_adjustments - self.negative_adjustments
        )


@dataclass(frozen=True, slots=True)
class StockEvolutionPage:
    items: list[StockEvolution]
    total_records: int


class InventoryPort(Protocol):
    async def stock_evolution(self, company_id: UUID, branch_id: UUID, *, from_at: datetime, to_at: datetime,
                              product_ids: list[UUID], page: int, page_size: int) -> StockEvolutionPage: ...

    async def consolidated_stock_evolution(self, company_id: UUID, branch_ids: list[UUID], *, from_at: datetime,
                                           to_at: datetime, product_ids: list[UUID], page: int,
                                           page_size: int) -> StockEvolutionPage: ...


# --------------------------------------------------------------------------- CR y PC (nombres y unidad base)


@dataclass(frozen=True, slots=True)
class CompanyProductInfo:
    id: UUID
    global_product_id: UUID
    internal_code: str | None
    display_name: str


@dataclass(frozen=True, slots=True)
class UnitInfo:
    id: UUID
    code: str
    name: str


class CommercialRelationshipPort(Protocol):
    async def products(self, company_id: UUID, ids: list[UUID]) -> dict[UUID, CompanyProductInfo]: ...


class ProductCatalogPort(Protocol):
    async def base_units(self, global_ids: list[UUID]) -> dict[UUID, UnitInfo | None]: ...


@dataclass(slots=True)
class Ports:
    oc: OperationalContextPort
    sales: SalesPort
    purchase: PurchasePort
    inventory: InventoryPort
    cr: CommercialRelationshipPort
    pc: ProductCatalogPort
    extra: dict = field(default_factory=dict)
