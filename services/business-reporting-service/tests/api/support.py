"""Datos ficticios por reporte sobre los dobles (`tests/fakes.py`)."""

from __future__ import annotations

from business_reporting_service.application.ports import (
    BranchSales,
    PresentationSales,
    ProductSales,
    SalesTotal,
    StockEvolution,
)
from tests.fakes import MILLILITER, TABLET, D, Fakes, purchase

PERIOD = {"date_from": "2026-10-01", "date_to": "2026-10-18"}


def base(fakes: Fakes) -> str:
    return f"/api/v1/companies/{fakes.company.id}/reports"


def branch_base(fakes: Fakes, branch=None) -> str:
    return f"/api/v1/companies/{fakes.company.id}/branches/{branch or fakes.branches[0].id}/reports"


def seed_sales(fakes: Fakes):
    tablets = fakes.product("Acetaminofén 500 mg", code="A-001", unit=TABLET)
    syrup = fakes.product("Jarabe para la tos 120 ml", code="J-120", unit=MILLILITER)
    fakes.product_sales = [
        ProductSales(tablets, "A-001", "Acetaminofén 500 mg", "COP", D("1250"), D("625000"), 84, [
            PresentationSales(None, "CJ10", "Caja x 10", D("100"), D("1000"), D("500000")),
            PresentationSales(None, "UND", "Unidad", D("250"), D("250"), D("125000")),
        ]),
        ProductSales(syrup, "J-120", "Jarabe para la tos 120 ml", "COP", D("2400"), D("400000"), 20, []),
    ]
    fakes.sales_totals = [SalesTotal("COP", D("1025000"), 95)]
    principal, norte, _ = fakes.branches
    fakes.branch_sales = [BranchSales(principal.id, "COP", 60, D("750000")), BranchSales(norte.id, "COP", 35, D("250000"))]
    return tablets, syrup


def seed_purchases(fakes: Fakes, count: int = 3):
    principal = fakes.branches[0].id
    categories = ["RECEIVED", "PENDING_RECEIPT", "CANCELLED"]
    fakes.purchases = [purchase(principal, categories[i % 3], "1000.00", number=f"OC-{i:06d}") for i in range(count)]
    return fakes.purchases


def seed_evolution(fakes: Fakes, count: int = 2):
    branch = fakes.branches[0].id
    rows = []
    for index in range(count):
        product = fakes.product(f"Producto ficticio {index:03d}", code=f"P-{index:03d}", unit=TABLET)
        rows.append(StockEvolution(product, D("10"), D("5"), D("3"), D("0"), D("1"), D("2"), D("1"), D("14"), 6))
    fakes.evolution[branch] = rows
    return rows
