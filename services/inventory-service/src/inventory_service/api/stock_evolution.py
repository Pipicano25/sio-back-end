"""Evolución de existencias de una sucursal (spec 023, INV-R1; solo lectura).

Permiso propio `perm:inventory:stock_evolution:read` (DR-11): autoriza **solo** esta consulta de cantidades
(existencia inicial, entradas, salidas, reversos, ajustes y existencia final por producto, en unidad base). No da
acceso al kardex, a costos ni a capas, que siguen exigiendo `movements:read` y `valuation:read`. Alcance por empresa
como las demás consultas (`api/scope.py`): membresía `ACTIVE` sin asignación a la sucursal.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sio_auth import SIOAuth

from inventory_service.api.identity import SERVICE
from inventory_service.api.openapi import QUERY_RESPONSES, TAG_REPORTS
from inventory_service.api.schemas.queries import total_pages
from inventory_service.api.schemas.stock_evolution import (
    ConsolidatedStockEvolutionPage,
    ConsolidatedStockEvolutionQuery,
    StockEvolutionItem,
    StockEvolutionPage,
    StockEvolutionQuery,
)
from inventory_service.api.scope import company_scope
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.stock_evolution_repository import StockEvolutionRepository

Company = Annotated[UUID, Depends(company_scope)]


def get_stock_evolution_repository(request: Request):
    for session in get_db_session(request):
        yield StockEvolutionRepository(session)


Repository = Annotated[StockEvolutionRepository, Depends(get_stock_evolution_repository)]


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_REPORTS], responses=QUERY_RESPONSES)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/stock-evolution",
        response_model=StockEvolutionPage,
        response_model_by_alias=True,
        response_model_exclude_none=True,
        summary="Evolución de existencias por producto en una sucursal (spec 023, INV-R1)",
        description=(
            "Por producto, en unidad base: `opening_quantity` (saldo al instante `from`), entradas de compra, salidas "
            "de venta, reversos de entrada y de salida, ajustes positivos y negativos de `[from, to)` y "
            "`closing_quantity` (saldo del último movimiento del período). Se cumple `closing = opening + entries − "
            "outputs − entry_reversals + output_reversals + positive_adjustments − negative_adjustments`. Productos "
            "con movimientos en el período o saldo inicial positivo, en orden `company_product_id`. **Sin costos ni "
            "valores.** Período de hasta 366 días. Permiso: `perm:inventory:stock_evolution:read` (solo esta "
            "consulta; no abre el kardex)."
        ),
        dependencies=[auth.permission(SERVICE, "stock_evolution", "read")],
    )
    def stock_evolution(company_id: Company, branch_id: UUID, query: Annotated[StockEvolutionQuery, Query()],
                        repository: Repository) -> StockEvolutionPage:
        result = repository.page(
            company_id, branch_id, from_at=query.from_, to_at=query.to,
            product_ids=list(dict.fromkeys(query.company_product_id)), page=query.page, page_size=query.page_size,
        )
        return StockEvolutionPage(
            company_id=company_id, branch_id=branch_id, from_=query.from_, to=query.to,
            items=[StockEvolutionItem.of(row) for row in result.items],
            page=query.page, page_size=query.page_size, total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        "/companies/{company_id}/stock-evolution",
        response_model=ConsolidatedStockEvolutionPage,
        response_model_by_alias=True,
        response_model_exclude_none=True,
        summary="Evolución de existencias consolidada por producto en varias sucursales (spec 023, INV-R1C)",
        description=(
            "Como INV-R1, pero sumando por producto las sucursales de `branch_id` (repetible, obligatorio, hasta "
            "100): saldo inicial, entradas, salidas, reversos, ajustes y saldo final de cada sucursal, sumados. "
            "Cada fila es un producto (una sola unidad base): nunca se suman productos distintos. `branch_count` "
            "indica cuántas sucursales aportan. Una sola consulta por página. **Sin costos ni valores.** Período de "
            "hasta 366 días. Permiso: `perm:inventory:stock_evolution:read`. Las sucursales que no son de la empresa "
            "no aportan filas (solo se leen movimientos de `company_id`)."
        ),
        dependencies=[auth.permission(SERVICE, "stock_evolution", "read")],
    )
    def consolidated_stock_evolution(company_id: Company, query: Annotated[ConsolidatedStockEvolutionQuery, Query()],
                                     repository: Repository) -> ConsolidatedStockEvolutionPage:
        branch_ids = list(dict.fromkeys(query.branch_id))
        result = repository.consolidated(
            company_id, branch_ids, from_at=query.from_, to_at=query.to,
            product_ids=list(dict.fromkeys(query.company_product_id)), page=query.page, page_size=query.page_size,
        )
        return ConsolidatedStockEvolutionPage(
            company_id=company_id, branch_ids=branch_ids, from_=query.from_, to=query.to,
            items=[StockEvolutionItem.consolidated(row) for row in result.items],
            page=query.page, page_size=query.page_size, total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    return router
