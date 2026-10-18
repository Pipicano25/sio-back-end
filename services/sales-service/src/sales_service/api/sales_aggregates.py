"""Agregaciones de ventas para reportes (spec 023, SAL-R1 y SAL-R2; solo lectura).

Mismas reglas que las lecturas de ventas: usuario humano, `perm:sales:sales:read` y membresía `ACTIVE` en la
empresa (no se exige asignación a la sucursal, DS-09). Solo ventas `CONFIRMED` con `operation_date` en el período
(spec 023, DR-01 y DR-02). No devuelven costos ni márgenes, así que `read-profitability` no cambia la respuesta.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sio_auth import SIOAuth

from sales_service.api.dependencies import CompanyReader, ServicesDep
from sales_service.api.identity import SERVICE
from sales_service.api.openapi import READ_RESPONSES, TAG_REPORTS
from sales_service.api.schemas.sales import MONEY, fmt
from sales_service.api.schemas.sales_aggregates import (
    AggregateQuery,
    BranchAggregateOut,
    BranchTotalOut,
    ByBranchOut,
    ByProductOut,
    ByProductQuery,
    CurrencyTotalOut,
    ProductAggregateOut,
)

SCOPE = (
    "Solo ventas `CONFIRMED` (las anuladas se excluyen según su estado actual y los borradores nunca cuentan) con "
    "`operation_date` entre `date_from` y `date_to` (incluidas; como máximo 366 días). Importes agrupados por "
    "`currency_code`; sin costos ni márgenes. Permiso: `perm:sales:sales:read` y membresía en la empresa."
)


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_REPORTS])
    base = "/companies/{company_id}/sales-aggregates"

    @router.get(
        base + "/by-product",
        response_model=ByProductOut,
        summary="Ventas efectivas agrupadas por producto (spec 023, SAL-R1)",
        description=(
            "Cantidad en unidad base (Σ `quantity × base_quantity_factor_snapshot`, el factor guardado al vender), "
            "importe (Σ `subtotal − discount_amount`) y número de ventas por producto, con el último código y nombre "
            "del período. Ordenado por `quantity_base` (por defecto) o por `amount` (dentro de cada moneda) y "
            "limitado en la base; `include_presentations` agrega el desglose por presentación. `totals` cubre todas "
            "las ventas efectivas del alcance, no solo las filas devueltas. " + SCOPE
        ),
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def by_product(company_id: CompanyReader, query: Annotated[ByProductQuery, Query()],
                   services: ServicesDep) -> ByProductOut:
        repository = services.aggregates()
        branch_ids = query.branch_ids
        rows = repository.by_product(
            company_id, date_from=query.date_from, date_to=query.date_to, branch_ids=branch_ids,
            order_by=query.order_by, limit=query.limit, include_presentations=query.include_presentations,
        )
        totals = repository.product_totals(company_id, date_from=query.date_from, date_to=query.date_to,
                                           branch_ids=branch_ids)
        return ByProductOut(
            company_id=company_id, date_from=query.date_from, date_to=query.date_to, branch_ids=branch_ids,
            order_by=query.order_by, items=[ProductAggregateOut.of(row) for row in rows],
            totals=[CurrencyTotalOut(currency_code=t.currency_code, amount=fmt(t.amount, MONEY),
                                     sales_count=t.sales_count) for t in totals],
        )

    @router.get(
        base + "/by-branch",
        response_model=ByBranchOut,
        summary="Ventas efectivas agrupadas por sucursal (spec 023, SAL-R2)",
        description=(
            "Número de ventas y total (Σ `total` del documento) por sucursal y moneda; `totals` por moneda. Una "
            "sucursal sin ventas efectivas no aparece (quien consume completa las sucursales del alcance). " + SCOPE
        ),
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def by_branch(company_id: CompanyReader, query: Annotated[AggregateQuery, Query()],
                  services: ServicesDep) -> ByBranchOut:
        branch_ids = query.branch_ids
        rows = services.aggregates().by_branch(company_id, date_from=query.date_from, date_to=query.date_to,
                                               branch_ids=branch_ids)
        totals: dict[str, list] = defaultdict(lambda: [0, Decimal("0")])
        for row in rows:
            totals[row.currency_code][0] += row.sales_count
            totals[row.currency_code][1] += row.total_amount
        return ByBranchOut(
            company_id=company_id, date_from=query.date_from, date_to=query.date_to, branch_ids=branch_ids,
            items=[BranchAggregateOut(branch_id=row.branch_id, currency_code=row.currency_code,
                                      sales_count=row.sales_count, total_amount=fmt(row.total_amount, MONEY))
                   for row in rows],
            totals=[BranchTotalOut(currency_code=code, sales_count=count, total_amount=fmt(amount, MONEY))
                    for code, (count, amount) in sorted(totals.items())],
        )

    return router
