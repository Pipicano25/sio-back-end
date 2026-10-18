"""Routers de los cuatro reportes de la fase 1 (spec 023; `contracts/business-reporting-api.md`).

Orden de cada solicitud:

1. `sio-auth`: token válido (`401`) y permiso funcional del reporte (`403`, sin revelar el permiso).
2. Parámetros estrictos (`422`).
3. Membresía y sucursales en Operational Context con el token del usuario (`404`), antes de cualquier otra llamada.
4. Agregación del propietario con el token del usuario (su `403` se responde como `403` genérico) y enriquecimiento
   por lote.
5. JSON, o CSV en flujo (`api/csv_stream.py`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sio_auth import SIOAuth

from business_reporting_service.api import csv_stream
from business_reporting_service.api.csv_stream import CsvPlan, Number
from business_reporting_service.api.dependencies import ports_of
from business_reporting_service.api.openapi import REPORT_ERRORS, TAG_REPORTS
from business_reporting_service.api.schemas.reports import (
    BranchOnlySalesOut,
    BranchSalesOut,
    BranchSalesReportOut,
    CompanyStockEvolutionOut,
    ConsolidatedStockOut,
    BranchTotalOut,
    PresentationOut,
    PurchaseOut,
    PurchasesOut,
    PurchaseTotalsOut,
    SalesByBranchOut,
    SalesTotalOut,
    StockEvolutionOut,
    StockEvolutionReportOut,
    TopProductOut,
    TopProductsOut,
    UnitOut,
    money,
    qty,
    total_pages,
)
from business_reporting_service.api.security import SERVICE
from business_reporting_service.application import reports
from business_reporting_service.application.exceptions import ValidationFailedError
from business_reporting_service.application.request_context import RequestBudget, request_budget

CSV_PAGE_SIZE = 100
Format = Literal["json", "csv"]


class Common(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: date
    date_to: date
    format: Format = "json"
    bom: bool = True


class TopBase(Common):
    rank_by: Literal["quantity", "amount"] = "quantity"
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    include_presentations: bool = False


class TopQuery(TopBase):
    branch_id: Annotated[list[UUID], Field(max_length=100)] = []


class BranchQuery(Common):
    branch_id: Annotated[list[UUID], Field(max_length=100)] = []


class PurchasesBase(Common):
    category: Annotated[list[Literal["RECEIVED", "PENDING_RECEIPT", "CANCELLED"]], Field(max_length=3)] = []
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 50


class PurchasesQuery(PurchasesBase):
    branch_id: Annotated[list[UUID], Field(max_length=100)] = []


class StockQuery(Common):
    company_product_id: Annotated[list[UUID], Field(max_length=100)] = []
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 50


class CompanyStockQuery(StockQuery):
    branch_id: Annotated[list[UUID], Field(max_length=100)] = []


def _unit(unit) -> UnitOut | None:
    return None if unit is None else UnitOut(id=unit.id, code=unit.code, name=unit.name)


def _header(report: str, company_id: UUID, period, generated_at, criteria: dict) -> dict:
    return {"report": report, "company_id": company_id, "date_from": period.date_from, "date_to": period.date_to,
            "generated_at": generated_at, "criteria": criteria}


def _filename(report: str, company_id: UUID, period) -> str:
    return f"{report}-{company_id}-{period.date_from.isoformat()}-{period.date_to.isoformat()}.csv"


def _csv(plan: CsvPlan, filename: str, bom: bool) -> StreamingResponse:
    return StreamingResponse(
        csv_stream.stream(plan, bom=bom),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


TOP_DESCRIPTION = (
    "Ranking por cantidad en unidad base (por defecto) o por importe, con la unidad base de cada producto. Solo "
    "ventas `CONFIRMED` por `operation_date`; las anuladas se excluyen. Nunca se suman cantidades de productos "
    "distintos: `mixed_base_units = true` advierte que el ranking compara unidades distintas. Importes por moneda. "
    "`format=csv` descarga el mismo contenido. Permisos: `perm:business-reporting:top_selling_products:read` y, en "
    "Sales, `perm:sales:sales:read`."
)
PURCHASES_DESCRIPTION = (
    "Compras no borrador por `operation_date`, con `category` `RECEIVED` (recibida), `PENDING_RECEIPT` (pendiente "
    "de recepción: no es mercancía recibida) o `CANCELLED` (anulada). `totals` es del período completo por moneda: "
    "`effective_total` = recibidas + pendientes; las anuladas se informan y nunca suman. `received_at` es "
    "informativa. `format=csv` descarga todas las páginas (máximo 50.000 filas). Permisos: "
    "`perm:business-reporting:purchases:read` y, en Purchase, `perm:purchase:purchases:read`."
)
BRANCH_NOTE = (
    "Ruta por sucursal: `company_id` y `branch_id` obligatorios en la ruta (la principal, con su UUID); solo esa "
    "sucursal, que debe ser de la empresa (`404` si no). `branch_id` por consulta no se admite (`422`)."
)


def _named(report: str, branch_id: UUID | None) -> str:
    return report if branch_id is None else f"{report}-{branch_id}"


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_REPORTS], responses=REPORT_ERRORS)

    def runtime(request: Request, query: Common):
        settings = request.app.state.settings
        budget_seconds = settings.csv_budget_seconds if query.format == "csv" else settings.json_budget_seconds
        budget = RequestBudget(budget_seconds, settings.max_parallel_calls)
        limits = {"now": request.app.state.clock(), "max_days": settings.max_period_days,
                  "default_timezone": settings.default_timezone}
        return settings, budget, limits

    # ------------------------------------------------------------------ R1

    @router.get(
        "/companies/{company_id}/reports/top-selling-products",
        response_model=TopProductsOut,
        summary="Productos más vendidos del período",
        description=TOP_DESCRIPTION + " Sin `branch_id`: todas las sucursales de la empresa; con `branch_id` "
        "(repetible): esas sucursales.",
        dependencies=[auth.permission(SERVICE, "top_selling_products", "read")],
    )
    async def top_selling_products(company_id: UUID, request: Request, query: Annotated[TopQuery, Query()]):
        return await run_top(company_id, list(dict.fromkeys(query.branch_id)), None, request, query)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/reports/top-selling-products",
        response_model=TopProductsOut,
        summary="Productos más vendidos de una sucursal",
        description=TOP_DESCRIPTION + " " + BRANCH_NOTE,
        dependencies=[auth.permission(SERVICE, "top_selling_products", "read")],
    )
    async def branch_top_selling_products(company_id: UUID, branch_id: UUID, request: Request,
                                          query: Annotated[TopBase, Query()]):
        return await run_top(company_id, [branch_id], branch_id, request, query)

    async def run_top(company_id: UUID, branch_ids: list[UUID], branch_id: UUID | None, request: Request,
                      query: TopBase):
        settings, budget, limits = runtime(request, query)
        with request_budget(budget):
            report = await reports.top_selling_products(
                ports_of(request), company_id, branch_ids, query.date_from, query.date_to,
                rank_by=query.rank_by, limit=query.limit, include_presentations=query.include_presentations, **limits,
            )
        header = _header("top-selling-products", company_id, report.period, limits["now"],
                         {"sales_status": "CONFIRMED", "date_basis": "operation_date", "rank_by": query.rank_by})
        if query.format == "json":
            return TopProductsOut(
                **header, branch_ids=report.scope.branch_ids if report.scope.explicit else [],
                mixed_base_units=report.mixed_base_units,
                items=[
                    TopProductOut(
                        rank=item.rank, company_product_id=item.sales.company_product_id,
                        product_code=item.sales.product_code, product_name=item.sales.product_name,
                        base_unit=_unit(item.base_unit), quantity_base=qty(item.sales.quantity_base),
                        currency_code=item.sales.currency_code, amount=money(item.sales.amount),
                        sales_count=item.sales.sales_count,
                        presentations=None if item.sales.presentations is None else [
                            PresentationOut(company_product_presentation_id=p.company_product_presentation_id,
                                            code=p.code, name=p.name, quantity=qty(p.quantity),
                                            quantity_base=qty(p.quantity_base), amount=money(p.amount))
                            for p in item.sales.presentations
                        ],
                    )
                    for item in report.items
                ],
                totals=[SalesTotalOut(currency_code=t.currency_code, amount=money(t.amount), sales_count=t.sales_count)
                        for t in report.totals],
            )
        rows = [[Number(i.rank), i.sales.product_code, i.sales.product_name,
                 i.base_unit.code if i.base_unit else None, Number(qty(i.sales.quantity_base)),
                 Number(money(i.sales.amount)), i.sales.currency_code, Number(i.sales.sales_count),
                 str(i.sales.company_product_id)] for i in report.items]
        plan = CsvPlan(
            header=["Puesto", "Código", "Producto", "Unidad base", "Cantidad (unidad base)", "Importe", "Moneda",
                    "Ventas", "ID producto"],
            first_rows=rows, next_pages=None,
            totals=lambda: [["TOTAL", None, None, None, None, Number(money(t.amount)), t.currency_code,
                             Number(t.sales_count), None] for t in report.totals],
        )
        return _csv(plan, _filename(_named("top-selling-products", branch_id), company_id, report.period), query.bom)

    # ------------------------------------------------------------------ R2

    @router.get(
        "/companies/{company_id}/reports/sales-by-branch",
        response_model=SalesByBranchOut,
        summary="Ventas por sucursal del período",
        description=(
            "Compara sucursales: número de ventas, total vendido y participación por sucursal y moneda; las "
            "sucursales del alcance sin ventas aparecen con cero. `share_percentage` = total de la sucursal ÷ suma de "
            "los totales de **las sucursales de la respuesta** en la misma moneda × 100: sin `branch_id`, sobre toda "
            "la empresa; con `branch_id`, solo sobre las filtradas (una sola sucursal con ventas da 100). Solo "
            "ventas `CONFIRMED` por `operation_date`. `format=csv` descarga el mismo contenido. Permisos: "
            "`perm:business-reporting:sales_by_branch:read` y, en Sales, `perm:sales:sales:read`."
        ),
        dependencies=[auth.permission(SERVICE, "sales_by_branch", "read")],
    )
    async def sales_by_branch(company_id: UUID, request: Request, query: Annotated[BranchQuery, Query()]):
        settings, budget, limits = runtime(request, query)
        with request_budget(budget):
            report = await reports.sales_by_branch(ports_of(request), company_id, list(dict.fromkeys(query.branch_id)),
                                                   query.date_from, query.date_to, **limits)
        header = _header("sales-by-branch", company_id, report.period, limits["now"],
                         {"sales_status": "CONFIRMED", "date_basis": "operation_date"})
        if query.format == "json":
            return SalesByBranchOut(
                **header, branch_ids=report.scope.branch_ids if report.scope.explicit else [],
                items=[BranchSalesOut(branch_id=r.branch.id, branch_code=r.branch.code, branch_name=r.branch.name,
                                      currency_code=r.currency_code, sales_count=r.sales_count,
                                      total_amount=money(r.total_amount), share_percentage=qty(r.share_percentage))
                       for r in report.items],
                totals=[BranchTotalOut(currency_code=c, sales_count=n, total_amount=money(a)) for c, n, a in report.totals],
            )
        plan = CsvPlan(
            header=["Código de sucursal", "Sucursal", "Moneda", "Ventas", "Total vendido", "Participación (%)",
                    "ID sucursal"],
            first_rows=[[r.branch.code, r.branch.name, r.currency_code, Number(r.sales_count),
                         Number(money(r.total_amount)), Number(qty(r.share_percentage)), str(r.branch.id)]
                        for r in report.items],
            next_pages=None,
            totals=lambda: [["TOTAL", None, c, Number(n), Number(money(a)), None, None] for c, n, a in report.totals],
        )
        return _csv(plan, _filename("sales-by-branch", company_id, report.period), query.bom)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/reports/sales-by-branch",
        response_model=BranchSalesReportOut,
        summary="Ventas de una sucursal del período",
        description=(
            "Número de ventas y total vendido **solo** de la sucursal de la ruta, por moneda, también con cero "
            "ventas. Sin `share_percentage`: con una sola sucursal no hay comparación (la participación entre "
            "sucursales está en la ruta de la empresa). Mismo caso de uso que la ruta de la empresa con un único "
            "`branch_id`. " + BRANCH_NOTE + " Permisos: `perm:business-reporting:sales_by_branch:read` y, en Sales, "
            "`perm:sales:sales:read`."
        ),
        dependencies=[auth.permission(SERVICE, "sales_by_branch", "read")],
    )
    async def branch_sales(company_id: UUID, branch_id: UUID, request: Request, query: Annotated[Common, Query()]):
        settings, budget, limits = runtime(request, query)
        with request_budget(budget):
            report = await reports.sales_by_branch(ports_of(request), company_id, [branch_id], query.date_from,
                                                   query.date_to, **limits)
        branch = report.scope.branches[0]
        header = _header("sales-by-branch", company_id, report.period, limits["now"],
                         {"sales_status": "CONFIRMED", "date_basis": "operation_date"})
        if query.format == "json":
            return BranchSalesReportOut(
                **header, branch_id=branch.id, branch_code=branch.code, branch_name=branch.name,
                items=[BranchOnlySalesOut(currency_code=r.currency_code, sales_count=r.sales_count,
                                          total_amount=money(r.total_amount)) for r in report.items],
            )
        plan = CsvPlan(
            header=["Código de sucursal", "Sucursal", "Moneda", "Ventas", "Total vendido", "ID sucursal"],
            first_rows=[[branch.code, branch.name, r.currency_code, Number(r.sales_count),
                         Number(money(r.total_amount)), str(branch.id)] for r in report.items],
            next_pages=None, totals=lambda: [],
        )
        return _csv(plan, _filename(_named("sales-by-branch", branch.id), company_id, report.period), query.bom)

    # ------------------------------------------------------------------ R3

    def purchase_row(scope, row) -> list:
        branch = scope.branch(row.branch_id)
        return [row.operation_date.isoformat(), row.received_at.isoformat() if row.received_at else None,
                branch.name if branch else None, row.supplier_name, row.supplier_identification, row.number,
                row.supplier_document_number, row.status, row.category, row.currency_code, Number(money(row.total)),
                str(row.id)]

    @router.get(
        "/companies/{company_id}/reports/purchases",
        response_model=PurchasesOut,
        summary="Compras del período",
        description=PURCHASES_DESCRIPTION + " Sin `branch_id`: todas las sucursales de la empresa (también las "
        "inactivas); con `branch_id` (repetible): esas sucursales.",
        dependencies=[auth.permission(SERVICE, "purchases", "read")],
    )
    async def purchases(company_id: UUID, request: Request, query: Annotated[PurchasesQuery, Query()]):
        return await run_purchases(company_id, list(dict.fromkeys(query.branch_id)), None, request, query)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/reports/purchases",
        response_model=PurchasesOut,
        summary="Compras del período de una sucursal",
        description=PURCHASES_DESCRIPTION + " " + BRANCH_NOTE + " `totals` es de esa sucursal.",
        dependencies=[auth.permission(SERVICE, "purchases", "read")],
    )
    async def branch_purchases(company_id: UUID, branch_id: UUID, request: Request,
                               query: Annotated[PurchasesBase, Query()]):
        return await run_purchases(company_id, [branch_id], branch_id, request, query)

    async def run_purchases(company_id: UUID, branch_ids: list[UUID], branch_id: UUID | None, request: Request,
                            query: PurchasesBase):
        settings, budget, limits = runtime(request, query)
        categories = list(dict.fromkeys(query.category))
        ports = ports_of(request)
        page_size = CSV_PAGE_SIZE if query.format == "csv" else query.page_size
        page_number = 1 if query.format == "csv" else query.page
        with request_budget(budget):
            scope, period = await reports.purchases_scope(ports, company_id, branch_ids, query.date_from,
                                                          query.date_to, **limits)
            first = await reports.purchases_page(ports, scope, period, categories=categories, page=page_number,
                                                 page_size=page_size)
        header = _header("purchases", company_id, period, limits["now"],
                         {"date_basis": "operation_date", "categories": categories or ["RECEIVED", "PENDING_RECEIPT",
                                                                                       "CANCELLED"]})
        totals = first.page.totals
        if query.format == "json":
            return PurchasesOut(
                **header, branch_ids=scope.branch_ids if scope.explicit else [],
                items=[PurchaseOut(purchase_id=r.id, operation_date=r.operation_date, received_at=r.received_at,
                                   branch_id=r.branch_id, branch_name=scope.branch(r.branch_id).name,
                                   supplier_name=r.supplier_name, supplier_identification=r.supplier_identification,
                                   number=r.number, supplier_document_number=r.supplier_document_number,
                                   status=r.status, category=r.category, receipt_status=r.receipt_status,
                                   currency_code=r.currency_code, total=money(r.total)) for r in first.page.items],
                totals=[PurchaseTotalsOut(
                    currency_code=t.currency_code, received_count=t.received_count, received_total=money(t.received_total),
                    pending_receipt_count=t.pending_receipt_count, pending_receipt_total=money(t.pending_receipt_total),
                    cancelled_count=t.cancelled_count, cancelled_total=money(t.cancelled_total),
                    effective_total=money(t.effective_total)) for t in totals],
                page=page_number, page_size=page_size, total_records=first.page.total_records,
                total_pages=total_pages(first.page.total_records, page_size),
            )
        _check_rows(first.page.total_records, settings.csv_max_rows)

        async def next_pages() -> AsyncIterator[list]:
            pages = total_pages(first.page.total_records, CSV_PAGE_SIZE)
            for number in range(2, pages + 1):
                with request_budget(budget):
                    page = await reports.purchases_page(ports, scope, period, categories=categories, page=number,
                                                        page_size=CSV_PAGE_SIZE)
                yield [purchase_row(scope, row) for row in page.page.items]

        def totals_rows():
            for t in totals:
                yield ["TOTAL RECIBIDAS", None, None, None, None, None, None, None, None, t.currency_code,
                       Number(money(t.received_total)), None]
                yield ["TOTAL PENDIENTES DE RECEPCIÓN", None, None, None, None, None, None, None, None,
                       t.currency_code, Number(money(t.pending_receipt_total)), None]
                yield ["TOTAL ANULADAS (no suma)", None, None, None, None, None, None, None, None, t.currency_code,
                       Number(money(t.cancelled_total)), None]
                yield ["TOTAL EFECTIVO", None, None, None, None, None, None, None, None, t.currency_code,
                       Number(money(t.effective_total)), None]

        plan = CsvPlan(
            header=["Fecha", "Recepción", "Sucursal", "Proveedor", "Identificación del proveedor", "Número",
                    "Documento del proveedor", "Estado", "Categoría", "Moneda", "Total", "ID compra"],
            first_rows=[purchase_row(scope, row) for row in first.page.items],
            next_pages=next_pages, totals=totals_rows,
        )
        return _csv(plan, _filename(_named("purchases", branch_id), company_id, period), query.bom)

    # ------------------------------------------------------------------ R4

    QUANTITY_FIELDS = ("opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals",
                       "positive_adjustments", "negative_adjustments", "closing_quantity")
    STOCK_HEADER = ["Código", "Producto", "Unidad base", "Existencia inicial", "Entradas", "Salidas",
                    "Reversos de entrada", "Reversos de salida", "Ajustes positivos", "Ajustes negativos",
                    "Existencia final", "Movimientos"]

    def stock_row(row, *, consolidated: bool = False) -> list:
        e = row.evolution
        return [row.product_code, row.product_name, row.base_unit.code if row.base_unit else None,
                *(Number(qty(getattr(e, name))) for name in QUANTITY_FIELDS), Number(e.movement_count),
                *([Number(e.branch_count)] if consolidated else []), str(e.company_product_id)]

    @router.get(
        "/companies/{company_id}/reports/stock-evolution",
        response_model=CompanyStockEvolutionOut,
        summary="Evolución de existencias consolidada de la empresa",
        description=(
            "Por producto, en su unidad base: existencias y movimientos **sumados** sobre las sucursales del alcance "
            "(sin `branch_id`: todas las de la empresa, también las inactivas, que pueden conservar existencias; con "
            "`branch_id`, esas). La consolidación la calcula Inventory en SQL (INV-R1C): una consulta por página. "
            "Cada fila es un producto: nunca se suman productos distintos. `branch_count` = sucursales que aportan. "
            "Los días se cuentan en la zona horaria de la empresa. Se verifica la identidad de cada fila. **Sin "
            "costos.** `format=csv` descarga todas las páginas. Permisos: "
            "`perm:business-reporting:stock_evolution:read` y, en Inventory, `perm:inventory:stock_evolution:read`."
        ),
        dependencies=[auth.permission(SERVICE, "stock_evolution", "read")],
    )
    async def company_stock_evolution(company_id: UUID, request: Request,
                                      query: Annotated[CompanyStockQuery, Query()]):
        settings, budget, limits = runtime(request, query)
        ports = ports_of(request)
        product_ids = list(dict.fromkeys(query.company_product_id))
        page_size = CSV_PAGE_SIZE if query.format == "csv" else query.page_size
        page_number = 1 if query.format == "csv" else query.page
        with request_budget(budget):
            scope, period, timezone, from_at, to_at = await reports.company_stock_evolution_scope(
                ports, company_id, list(dict.fromkeys(query.branch_id)), query.date_from, query.date_to, **limits)
            first = await reports.company_stock_evolution_page(ports, scope, period, timezone, from_at, to_at,
                                                               product_ids=product_ids, page=page_number,
                                                               page_size=page_size)
        header = _header("stock-evolution", company_id, period, limits["now"],
                         {"date_basis": "created_at", "from": from_at.isoformat(), "to": to_at.isoformat(),
                          "consolidation": "by_product"})
        if query.format == "json":
            return CompanyStockEvolutionOut(
                **header, branch_ids=scope.branch_ids, timezone=timezone,
                items=[ConsolidatedStockOut(
                    company_product_id=r.evolution.company_product_id, product_code=r.product_code,
                    product_name=r.product_name, base_unit=_unit(r.base_unit),
                    **{name: qty(getattr(r.evolution, name)) for name in QUANTITY_FIELDS},
                    movement_count=r.evolution.movement_count, branch_count=r.evolution.branch_count)
                    for r in first.items],
                page=page_number, page_size=page_size, total_records=first.total_records,
                total_pages=total_pages(first.total_records, page_size),
            )
        _check_rows(first.total_records, settings.csv_max_rows)

        async def next_pages() -> AsyncIterator[list]:
            for number in range(2, total_pages(first.total_records, CSV_PAGE_SIZE) + 1):
                with request_budget(budget):
                    page = await reports.company_stock_evolution_page(ports, scope, period, timezone, from_at, to_at,
                                                                      product_ids=product_ids, page=number,
                                                                      page_size=CSV_PAGE_SIZE)
                yield [stock_row(row, consolidated=True) for row in page.items]

        plan = CsvPlan(header=[*STOCK_HEADER, "Sucursales", "ID producto"],
                       first_rows=[stock_row(row, consolidated=True) for row in first.items], next_pages=next_pages,
                       totals=lambda: [])
        return _csv(plan, _filename("stock-evolution", company_id, period), query.bom)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/reports/stock-evolution",
        response_model=StockEvolutionReportOut,
        summary="Evolución de existencias de una sucursal",
        description=(
            "Por producto, en su unidad base: existencia inicial, entradas, salidas, reversos de entrada y de "
            "salida, ajustes positivos y negativos y existencia final del período (días en la zona horaria de la "
            "sucursal). Se verifica la identidad `final = inicial + entradas − salidas − reversos de entrada + "
            "reversos de salida + ajustes positivos − ajustes negativos`. **Sin costos.** La sucursal es "
            "obligatoria en la ruta (la principal, con su UUID). `format=csv` descarga todas las páginas. Permisos: "
            "`perm:business-reporting:stock_evolution:read` y, en Inventory, `perm:inventory:stock_evolution:read`."
        ),
        dependencies=[auth.permission(SERVICE, "stock_evolution", "read")],
    )
    async def stock_evolution(company_id: UUID, branch_id: UUID, request: Request,
                              query: Annotated[StockQuery, Query()]):
        settings, budget, limits = runtime(request, query)
        ports = ports_of(request)
        product_ids = list(dict.fromkeys(query.company_product_id))
        page_size = CSV_PAGE_SIZE if query.format == "csv" else query.page_size
        page_number = 1 if query.format == "csv" else query.page
        with request_budget(budget):
            scope, period, branch, from_at, to_at = await reports.stock_evolution_scope(
                ports, company_id, branch_id, query.date_from, query.date_to, **limits)
            first = await reports.stock_evolution_page(ports, scope, period, branch, from_at, to_at,
                                                       product_ids=product_ids, page=page_number, page_size=page_size)
        header = _header("stock-evolution", company_id, period, limits["now"],
                         {"date_basis": "created_at", "from": from_at.isoformat(), "to": to_at.isoformat()})
        if query.format == "json":
            return StockEvolutionReportOut(
                **header, branch_id=branch.id, branch_code=branch.code, branch_name=branch.name,
                timezone=str(from_at.tzinfo),
                items=[StockEvolutionOut(
                    company_product_id=r.evolution.company_product_id, product_code=r.product_code,
                    product_name=r.product_name, base_unit=_unit(r.base_unit),
                    **{name: qty(getattr(r.evolution, name)) for name in QUANTITY_FIELDS},
                    movement_count=r.evolution.movement_count) for r in first.items],
                page=page_number, page_size=page_size, total_records=first.total_records,
                total_pages=total_pages(first.total_records, page_size),
            )
        _check_rows(first.total_records, settings.csv_max_rows)

        async def next_pages() -> AsyncIterator[list]:
            for number in range(2, total_pages(first.total_records, CSV_PAGE_SIZE) + 1):
                with request_budget(budget):
                    page = await reports.stock_evolution_page(ports, scope, period, branch, from_at, to_at,
                                                              product_ids=product_ids, page=number,
                                                              page_size=CSV_PAGE_SIZE)
                yield [stock_row(row) for row in page.items]

        plan = CsvPlan(
            header=[*STOCK_HEADER, "ID producto"],
            first_rows=[stock_row(row) for row in first.items], next_pages=next_pages, totals=lambda: [],
        )
        return _csv(plan, _filename(f"stock-evolution-{branch.id}", company_id, period), query.bom)

    return router


def _check_rows(total: int, maximum: int) -> None:
    if total > maximum:
        raise ValidationFailedError(
            "El reporte supera el máximo de filas del CSV.",
            errors=[{"field": "format", "message": f"El CSV admite como máximo {maximum} filas; reduzca el período "
                     "o use los filtros.", "code": "CSV_TOO_LARGE"}],
        )
