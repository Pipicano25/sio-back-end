"""Dobles de Operational Context, Sales, Purchase, Inventory, Commercial Relationship y Product Catalog.

Como el servicio propaga el token del usuario (DR-07), cada doble de propietario evalúa **sobre ese token** el
permiso de lectura que exige el propietario real (sin verificar la firma: la verificó `sio-auth` antes) y responde
`OwnerForbiddenError` si falta, igual que el adaptador ante un `403`. El doble de OC decide la membresía por
usuario (`sub`). Cada llamada se registra (operación y argumentos) para comprobar el orden y que no hay N+1.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import jwt
from sio_auth import SioPermission, evaluate_permission

from business_reporting_service.application.exceptions import (
    DependencyUnavailableError,
    NotFoundError,
    OwnerForbiddenError,
)
from business_reporting_service.application.ports import (
    BranchInfo,
    BranchSales,
    CompanyInfo,
    CompanyProductInfo,
    Ports,
    ProductSales,
    ProductSalesResult,
    PurchasePage,
    PurchaseRow,
    PurchaseTotals,
    SalesTotal,
    StockEvolution,
    StockEvolutionPage,
    UnitInfo,
)


@dataclass
class CallLog:
    calls: list[tuple[str, object]] = field(default_factory=list)

    def record(self, operation: str, arguments: object = None) -> None:
        self.calls.append((operation, arguments))

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def count(self, operation: str) -> int:
        return sum(1 for name, _ in self.calls if name == operation)


def claims_of(authorization: str | None) -> dict:
    if not authorization:
        return {}
    return jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})


class _Owner:
    provider = "fake"
    permission: tuple[str, str, str] = ("", "", "")

    def __init__(self, data: "Fakes", authorization: str | None) -> None:
        self.data = data
        self.claims = claims_of(authorization)

    def _enter(self, operation: str, arguments: object = None) -> None:
        self.data.log.record(operation, arguments)
        if operation in self.data.fail:
            raise DependencyUnavailableError(self.provider, operation, "prueba")
        service, resource, action = self.permission
        roles = self.claims.get("resource_access", {}).get("sio-api", {}).get("roles", [])
        if not evaluate_permission(roles, SioPermission(service=service, resource=resource, action=action)):
            raise OwnerForbiddenError(self.provider, operation)
        if not self.data.is_member(self.claims.get("sub")):
            raise NotFoundError()


class FakeOC:
    def __init__(self, data: "Fakes", authorization: str | None) -> None:
        self.data = data
        self.sub = claims_of(authorization).get("sub")

    async def has_company_access(self, company_id: UUID) -> bool:
        self.data.log.record("operational_access", company_id)
        if "operational_access" in self.data.fail:
            raise DependencyUnavailableError("operational-context", "operational_access", "prueba")
        return company_id == self.data.company.id and self.data.is_member(self.sub)

    async def company(self, company_id: UUID) -> CompanyInfo | None:
        self.data.log.record("company", company_id)
        return self.data.company if company_id == self.data.company.id else None

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        self.data.log.record("branches", (company_id, status))
        if company_id != self.data.company.id:
            return []
        return [b for b in self.data.branches if b.status == status]


class FakeSales(_Owner):
    provider = "sales"
    permission = ("sales", "sales", "read")

    async def by_product(self, company_id, *, date_from, date_to, branch_ids, order_by, limit, include_presentations):
        self._enter("sales_by_product", dict(date_from=date_from, date_to=date_to, branch_ids=list(branch_ids),
                                             order_by=order_by, limit=limit, include_presentations=include_presentations))
        items = list(self.data.product_sales)
        key = (lambda p: -p.quantity_base) if order_by == "quantity_base" else (lambda p: (p.currency_code, -p.amount))
        items.sort(key=key)
        items = [p if include_presentations else replace(p, presentations=None)
                 for p in items[:limit]]
        return ProductSalesResult(items, list(self.data.sales_totals))

    async def by_branch(self, company_id, *, date_from, date_to, branch_ids):
        self._enter("sales_by_branch", dict(date_from=date_from, date_to=date_to, branch_ids=list(branch_ids)))
        return [row for row in self.data.branch_sales if not branch_ids or row.branch_id in branch_ids]


class FakePurchase(_Owner):
    provider = "purchase"
    permission = ("purchase", "purchases", "read")

    async def period(self, company_id, *, date_from, date_to, branch_ids, categories, page, page_size):
        self._enter("purchase_period", dict(date_from=date_from, date_to=date_to, branch_ids=list(branch_ids),
                                            categories=list(categories), page=page, page_size=page_size))
        in_scope = [r for r in self.data.purchases if not branch_ids or r.branch_id in branch_ids]
        rows = [r for r in in_scope if not categories or r.category in categories]
        start = (page - 1) * page_size
        return PurchasePage(rows[start:start + page_size], _totals(in_scope), len(rows))


def _totals(rows: list[PurchaseRow]) -> list[PurchaseTotals]:
    """Como PUR-R1: totales del alcance (sucursales), sin el filtro de categoría ni la página, por moneda."""
    result = []
    for currency in sorted({r.currency_code for r in rows}):
        of = [r for r in rows if r.currency_code == currency]

        def total(category):
            return sum((r.total for r in of if r.category == category), Decimal("0"))

        def count(category):
            return sum(1 for r in of if r.category == category)

        result.append(PurchaseTotals(currency, count("RECEIVED"), total("RECEIVED"), count("PENDING_RECEIPT"),
                                     total("PENDING_RECEIPT"), count("CANCELLED"), total("CANCELLED"),
                                     total("RECEIVED") + total("PENDING_RECEIPT")))
    return result


class FakeInventory(_Owner):
    provider = "inventory"
    permission = ("inventory", "stock_evolution", "read")

    async def stock_evolution(self, company_id, branch_id, *, from_at, to_at, product_ids, page, page_size):
        self._enter("stock_evolution", dict(branch_id=branch_id, from_at=from_at, to_at=to_at,
                                            product_ids=list(product_ids), page=page, page_size=page_size))
        if page in self.data.fail_inventory_pages:
            raise DependencyUnavailableError("inventory", "stock_evolution", "prueba")
        rows = sorted((r for r in self.data.evolution.get(branch_id, [])
                       if not product_ids or r.company_product_id in product_ids),
                      key=lambda r: str(r.company_product_id))  # INV-R1 ordena por `company_product_id`
        start = (page - 1) * page_size
        return StockEvolutionPage(rows[start:start + page_size], len(rows))


    async def consolidated_stock_evolution(self, company_id, branch_ids, *, from_at, to_at, product_ids, page,
                                           page_size):
        """Como INV-R1C: por producto, suma de las sucursales pedidas (nunca entre productos)."""
        self._enter("consolidated_stock_evolution", dict(branch_ids=list(branch_ids), from_at=from_at, to_at=to_at,
                                                         product_ids=list(product_ids), page=page, page_size=page_size))
        merged: dict = {}
        for branch in branch_ids:
            for row in self.data.evolution.get(branch, []):
                if product_ids and row.company_product_id not in product_ids:
                    continue
                if row.company_product_id not in merged:
                    merged[row.company_product_id] = replace(row, branch_count=1)
                    continue
                acc = merged[row.company_product_id]
                merged[row.company_product_id] = replace(acc, **{
                    name: getattr(acc, name) + getattr(row, name) for name in (
                        "opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals",
                        "positive_adjustments", "negative_adjustments", "closing_quantity", "movement_count")},
                    branch_count=acc.branch_count + 1)
        rows = [merged[key] for key in sorted(merged, key=str)]
        start = (page - 1) * page_size
        return StockEvolutionPage(rows[start:start + page_size], len(rows))


class FakeCR(_Owner):
    provider = "commercial-relationship"
    permission = ("commercial-relationship", "company_products", "read")

    async def products(self, company_id, ids):
        self._enter("company_products_search", list(ids))
        return {i: self.data.products[i] for i in ids if i in self.data.products}


class FakePC(_Owner):
    provider = "product-catalog"
    permission = ("product-catalog", "products", "read")

    async def base_units(self, global_ids):
        self._enter("product_summaries", list(global_ids))
        return {g: self.data.units.get(g) for g in global_ids}


@dataclass
class Fakes:
    company: CompanyInfo
    branches: list[BranchInfo]
    log: CallLog = field(default_factory=CallLog)
    members: set[str] = field(default_factory=set)
    fail: set[str] = field(default_factory=set)
    fail_inventory_pages: set[int] = field(default_factory=set)
    product_sales: list[ProductSales] = field(default_factory=list)
    sales_totals: list[SalesTotal] = field(default_factory=list)
    branch_sales: list[BranchSales] = field(default_factory=list)
    purchases: list[PurchaseRow] = field(default_factory=list)
    evolution: dict[UUID, list[StockEvolution]] = field(default_factory=dict)
    products: dict[UUID, CompanyProductInfo] = field(default_factory=dict)
    units: dict[UUID, UnitInfo | None] = field(default_factory=dict)

    def is_member(self, sub: str | None) -> bool:
        return sub in self.members

    def ports_for(self, authorization: str | None) -> Ports:
        return Ports(FakeOC(self, authorization), FakeSales(self, authorization), FakePurchase(self, authorization),
                     FakeInventory(self, authorization), FakeCR(self, authorization), FakePC(self, authorization))

    # ---------------------------------------------------------------- constructores de datos

    def product(self, name: str, *, code: str, unit: UnitInfo | None) -> UUID:
        product_id, global_id = uuid4(), uuid4()
        self.products[product_id] = CompanyProductInfo(product_id, global_id, code, name)
        self.units[global_id] = unit
        return product_id


TABLET = UnitInfo(UUID("00000000-0000-4000-8000-0000000000a1"), "TAB", "Tableta")
MILLILITER = UnitInfo(UUID("00000000-0000-4000-8000-0000000000a2"), "ML", "Mililitro")
USERS = ("admin.test", "supervisor.test", "compras.test", "ventas.test", "inventario.test", "reportes.test",
         "consulta.test")


def build_fakes() -> Fakes:
    company = CompanyInfo(uuid4(), "America/Bogota", "COP")
    principal = BranchInfo(uuid4(), company.id, "PPAL", "Principal", "ACTIVE", "America/Bogota")
    norte = BranchInfo(uuid4(), company.id, "NORTE", "Norte", "ACTIVE", "America/Bogota")
    closed = BranchInfo(uuid4(), company.id, "CERRADA", "Cerrada", "INACTIVE", "America/Bogota")
    return Fakes(company, [principal, norte, closed], members={f"sub-{u}" for u in USERS})


def D(value: str) -> Decimal:
    return Decimal(value)


def purchase(branch: UUID, category: str, total: str, *, number: str, day: int = 5,
             supplier: str = "Proveedor Ficticio S.A.S.") -> PurchaseRow:
    status = "CANCELLED" if category == "CANCELLED" else "CONFIRMED"
    received = datetime(2026, 10, day, 14, 0) if category == "RECEIVED" else None
    return PurchaseRow(uuid4(), date(2026, 10, day), received, branch, supplier, "900000000-0", number, f"F-{number}",
                       status, category, "RECEIVED" if received else ("PENDING" if status == "CONFIRMED" else None),
                       "COP", D(total))
