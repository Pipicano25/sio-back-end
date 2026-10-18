"""Casos de uso de los cuatro reportes de la fase 1 (spec 023, FR-023-20 a FR-023-33).

Cada reporte: autorización previa en OC (`access.authorize`), **una** agregación del propietario por página y, si
hace falta, un lote de nombres (CR) y uno de unidades base (PC) por página. Nada se agrupa aquí a partir de
documentos individuales (FR-023-03); este módulo solo completa, valida y da forma.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from business_reporting_service.application.access import AuthorizedScope, authorize
from business_reporting_service.application.exceptions import (
    INVENTORY,
    PURCHASE,
    SALES,
    DependencyUnavailableError,
    ValidationFailedError,
)
from business_reporting_service.application.ports import (
    BranchInfo,
    Ports,
    ProductSales,
    PurchasePage,
    SalesTotal,
    StockEvolution,
    UnitInfo,
)
from business_reporting_service.domain.period import Period, build_period, today_in
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
PERCENT = Decimal("0.0001")
MAX_CONSOLIDATED_BRANCHES = 100
"""Límite de INV-R1C (`branch_id` ≤ 100)."""


def _incident(provider: str, operation: str, description: str) -> DependencyUnavailableError:
    logger.error("Incidente de integridad proveedor=%s operacion=%s detalle=%s", provider, operation, description)
    return DependencyUnavailableError(provider, operation, "integridad")


async def scope_and_period(ports: Ports, company_id: UUID, branch_ids: list[UUID] | None, date_from: date,
                           date_to: date, *, now: datetime, max_days: int, default_timezone: str):
    scope = await authorize(ports.oc, company_id, branch_ids)
    period = build_period(date_from, date_to, today=today_in(scope.company.timezone or default_timezone, now),
                          max_days=max_days)
    return scope, period


# --------------------------------------------------------------------------- R1


@dataclass(frozen=True, slots=True)
class TopProduct:
    rank: int
    sales: ProductSales
    base_unit: UnitInfo | None


@dataclass(frozen=True, slots=True)
class TopProductsReport:
    scope: AuthorizedScope
    period: Period
    rank_by: str
    items: list[TopProduct]
    totals: list[SalesTotal]

    @property
    def mixed_base_units(self) -> bool:
        return len({item.base_unit.id if item.base_unit else None for item in self.items}) > 1


async def base_units_of(ports: Ports, company_id: UUID, product_ids: list[UUID]) -> dict[UUID, tuple]:
    """`company_product_id → (CompanyProductInfo | None, UnitInfo | None)` con un lote a CR y uno a PC."""
    if not product_ids:
        return {}
    products = await ports.cr.products(company_id, product_ids)
    units = await ports.pc.base_units([info.global_product_id for info in products.values()])
    return {pid: (products.get(pid), units.get(products[pid].global_product_id) if pid in products else None)
            for pid in product_ids}


async def top_selling_products(ports: Ports, company_id: UUID, branch_ids: list[UUID], date_from: date,
                               date_to: date, *, rank_by: str, limit: int, include_presentations: bool,
                               now: datetime, max_days: int, default_timezone: str) -> TopProductsReport:
    scope, period = await scope_and_period(ports, company_id, branch_ids, date_from, date_to, now=now,
                                           max_days=max_days, default_timezone=default_timezone)
    result = await ports.sales.by_product(
        company_id, date_from=period.date_from, date_to=period.date_to, branch_ids=scope.branch_ids if scope.explicit else [],
        order_by="quantity_base" if rank_by == "quantity" else "amount", limit=limit,
        include_presentations=include_presentations,
    )
    if len(result.items) > limit:
        raise _incident(SALES, "sales_by_product", "más filas que el límite")
    enrichment = await base_units_of(ports, company_id, [item.company_product_id for item in result.items])
    missing = [item.company_product_id for item in result.items if enrichment[item.company_product_id][0] is None]
    if missing:
        # Un producto vendido que CR no reconoce como de la empresa: nunca se muestra sin verificar.
        raise _incident(SALES, "sales_by_product", "producto que Commercial Relationship no reconoce")
    items = [TopProduct(index, item, enrichment[item.company_product_id][1])
             for index, item in enumerate(result.items, start=1)]
    return TopProductsReport(scope, period, rank_by, items, result.totals)


# --------------------------------------------------------------------------- R2


@dataclass(frozen=True, slots=True)
class BranchRow:
    branch: BranchInfo
    currency_code: str
    sales_count: int
    total_amount: Decimal
    share_percentage: Decimal


@dataclass(frozen=True, slots=True)
class SalesByBranchReport:
    scope: AuthorizedScope
    period: Period
    items: list[BranchRow]
    totals: list[tuple[str, int, Decimal]]


async def sales_by_branch(ports: Ports, company_id: UUID, branch_ids: list[UUID], date_from: date, date_to: date, *,
                          now: datetime, max_days: int, default_timezone: str) -> SalesByBranchReport:
    scope, period = await scope_and_period(ports, company_id, branch_ids, date_from, date_to, now=now,
                                           max_days=max_days, default_timezone=default_timezone)
    rows = await ports.sales.by_branch(company_id, date_from=period.date_from, date_to=period.date_to,
                                       branch_ids=scope.branch_ids if scope.explicit else [])
    by_key: dict[tuple[UUID, str], tuple[int, Decimal]] = {}
    inactive: dict[UUID, BranchInfo] | None = None
    for row in rows:
        if scope.branch(row.branch_id) is None:
            if scope.explicit:
                raise _incident(SALES, "sales_by_branch", "sucursal fuera del alcance pedido")
            # Ventas de una sucursal inactiva de la empresa (no está entre las activas): se verifica con OC, una vez.
            if inactive is None:
                inactive = {b.id: b for b in await ports.oc.branches(company_id, status="INACTIVE")}
            if row.branch_id not in inactive:
                raise _incident(SALES, "sales_by_branch", "sucursal que no es de la empresa")
            scope = AuthorizedScope(scope.company, scope.branches + (inactive[row.branch_id],), scope.explicit)
        by_key[(row.branch_id, row.currency_code)] = (row.sales_count, row.total_amount)
    currencies = sorted({currency for _, currency in by_key} or {scope.company.default_currency})
    totals: dict[str, list] = defaultdict(lambda: [0, Decimal("0")])
    for (_, currency), (count, amount) in by_key.items():
        totals[currency][0] += count
        totals[currency][1] += amount
    items: list[BranchRow] = []
    for currency in currencies:
        total = totals[currency][1]
        for branch in scope.branches:
            count, amount = by_key.get((branch.id, currency), (0, Decimal("0")))
            share = (amount / total * 100).quantize(PERCENT, ROUND_HALF_UP) if total else Decimal("0").quantize(PERCENT)
            items.append(BranchRow(branch, currency, count, amount, share))
    items.sort(key=lambda r: (r.currency_code, -r.total_amount, r.branch.code, str(r.branch.id)))
    return SalesByBranchReport(scope, period, items,
                               [(c, totals[c][0], totals[c][1]) for c in currencies])


# --------------------------------------------------------------------------- R3


@dataclass(frozen=True, slots=True)
class PurchasesReport:
    scope: AuthorizedScope
    period: Period
    page: PurchasePage
    page_number: int
    page_size: int


def check_purchase_page(scope: AuthorizedScope, page: PurchasePage) -> None:
    for row in page.items:
        if scope.branch(row.branch_id) is None:
            raise _incident(PURCHASE, "purchase_period", "compra de una sucursal fuera del alcance")
        if row.category not in ("RECEIVED", "PENDING_RECEIPT", "CANCELLED"):
            raise _incident(PURCHASE, "purchase_period", "categoría desconocida")


async def purchases_scope(ports: Ports, company_id: UUID, branch_ids: list[UUID], date_from: date, date_to: date, *,
                          now: datetime, max_days: int, default_timezone: str):
    scope, period = await scope_and_period(ports, company_id, branch_ids, date_from, date_to, now=now,
                                           max_days=max_days, default_timezone=default_timezone)
    if not scope.explicit:
        # Las compras de sucursales inactivas siguen siendo de la empresa: el alcance incluye todas.
        inactive = await ports.oc.branches(company_id, status="INACTIVE")
        scope = AuthorizedScope(scope.company, scope.branches + tuple(inactive), explicit=False)
    return scope, period


async def purchases_page(ports: Ports, scope: AuthorizedScope, period: Period, *, categories: list[str], page: int,
                         page_size: int) -> PurchasesReport:
    result = await ports.purchase.period(
        scope.company.id, date_from=period.date_from, date_to=period.date_to,
        branch_ids=scope.branch_ids if scope.explicit else [], categories=categories, page=page, page_size=page_size,
    )
    check_purchase_page(scope, result)
    return PurchasesReport(scope, period, result, page, page_size)


# --------------------------------------------------------------------------- R4


@dataclass(frozen=True, slots=True)
class StockRow:
    evolution: StockEvolution
    product_code: str | None
    product_name: str
    base_unit: UnitInfo | None


@dataclass(frozen=True, slots=True)
class StockEvolutionReport:
    scope: AuthorizedScope
    period: Period
    branch: BranchInfo
    from_at: datetime
    to_at: datetime
    items: list[StockRow]
    total_records: int
    page: int
    page_size: int


async def stock_evolution_scope(ports: Ports, company_id: UUID, branch_id: UUID, date_from: date, date_to: date, *,
                                now: datetime, max_days: int, default_timezone: str):
    scope, period = await scope_and_period(ports, company_id, [branch_id], date_from, date_to, now=now,
                                           max_days=max_days, default_timezone=default_timezone)
    branch = scope.branches[0]
    from_at, to_at = period.instants(branch.timezone or scope.company.timezone or default_timezone)
    return scope, period, branch, from_at, to_at


async def stock_evolution_page(ports: Ports, scope: AuthorizedScope, period: Period, branch: BranchInfo,
                               from_at: datetime, to_at: datetime, *, product_ids: list[UUID], page: int,
                               page_size: int) -> StockEvolutionReport:
    result = await ports.inventory.stock_evolution(scope.company.id, branch.id, from_at=from_at, to_at=to_at,
                                                   product_ids=product_ids, page=page, page_size=page_size)
    items = await _stock_rows(ports, scope.company.id, result.items)
    return StockEvolutionReport(scope, period, branch, from_at, to_at, items, result.total_records, page, page_size)


async def _stock_rows(ports: Ports, company_id: UUID, rows: list[StockEvolution]) -> list[StockRow]:
    """Identidad de cada fila (FR-023-32) y nombre y unidad base por lote (un lote a CR y uno a PC por página)."""
    for row in rows:
        if not row.balances():
            raise _incident(INVENTORY, "stock_evolution", "la existencia final no cumple la identidad")
    enrichment = await base_units_of(ports, company_id, [row.company_product_id for row in rows])
    items = []
    for row in rows:
        product, unit = enrichment[row.company_product_id]
        if product is None:
            raise _incident(INVENTORY, "stock_evolution", "producto que Commercial Relationship no reconoce")
        items.append(StockRow(row, product.internal_code, product.display_name, unit))
    return items


@dataclass(frozen=True, slots=True)
class CompanyStockEvolutionReport:
    scope: AuthorizedScope
    period: Period
    timezone: str
    from_at: datetime
    to_at: datetime
    items: list[StockRow]
    total_records: int
    page: int
    page_size: int


async def company_stock_evolution_scope(ports: Ports, company_id: UUID, branch_ids: list[UUID], date_from: date,
                                        date_to: date, *, now: datetime, max_days: int, default_timezone: str):
    """Ruta consolidada: sin `branch_id`, todas las sucursales de la empresa (activas e inactivas, porque las
    inactivas pueden conservar existencias); con `branch_id`, esas. Días en la zona horaria de la empresa."""
    scope, period = await purchases_scope(ports, company_id, branch_ids, date_from, date_to, now=now,
                                          max_days=max_days, default_timezone=default_timezone)
    if len(scope.branch_ids) > MAX_CONSOLIDATED_BRANCHES:
        raise ValidationFailedError("La empresa tiene más sucursales de las que se pueden consolidar.", errors=[
            {"field": "branch_id", "message": f"Indique como máximo {MAX_CONSOLIDATED_BRANCHES} sucursales.",
             "code": "TOO_MANY_BRANCHES"}])
    timezone = scope.company.timezone or default_timezone
    from_at, to_at = period.instants(timezone)
    return scope, period, timezone, from_at, to_at


async def company_stock_evolution_page(ports: Ports, scope: AuthorizedScope, period: Period, timezone: str,
                                       from_at: datetime, to_at: datetime, *, product_ids: list[UUID], page: int,
                                       page_size: int) -> CompanyStockEvolutionReport:
    result = await ports.inventory.consolidated_stock_evolution(
        scope.company.id, scope.branch_ids, from_at=from_at, to_at=to_at, product_ids=product_ids, page=page,
        page_size=page_size)
    for row in result.items:
        if not 1 <= row.branch_count <= len(scope.branch_ids):
            raise _incident(INVENTORY, "consolidated_stock_evolution", "número de sucursales fuera del alcance")
    items = await _stock_rows(ports, scope.company.id, result.items)
    return CompanyStockEvolutionReport(scope, period, timezone, from_at, to_at, items, result.total_records, page,
                                       page_size)
