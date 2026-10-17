"""Lecturas de la spec 022 (`contracts/inventory.md` de la spec 022): INV-1, INV-2 e INV-3.

Solo lectura, con el alcance por empresa de `api/scope.py` (membresía o `platform:lookup`); las reglas de
escritura por sucursal no cambian (A-08). Nunca devuelven costos unitarios, costo promedio ni FIFO.

- INV-1 `POST /companies/{c}/branches/{b}/inventory-policies/lookup`: `product-policies:read`.
- INV-2 `POST /companies/{c}/inventory-product-sets`: `balances:read` y `product-policies:read`.
- INV-3 `POST /companies/{c}/inventory-summary`: `balances:read` y `product-policies:read`; con
  `include_valuation`, además `valuation:read`.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sio_auth import FORBIDDEN_DETAIL, SIOAuth, SioPermission, evaluate_permission
from sio_auth.dependencies import get_current_claims

from inventory_service.api.identity import SERVICE
from inventory_service.api.openapi import QUERY_RESPONSES, TAG_QUERIES
from inventory_service.api.schemas.inventory_reads import (
    BranchSummary,
    InventorySummaryIn,
    InventorySummaryResponse,
    PairSetItem,
    PolicyLookupIn,
    PolicyLookupItem,
    PolicyLookupResponse,
    PolicySummary,
    ProductSetItem,
    ProductSetsIn,
    ProductSetsResponse,
    SetPosition,
    SummaryCounts,
)
from inventory_service.api.scope import company_scope
from inventory_service.domain.quantities import format_decimal, format_money
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.inventory_read_repository import InventoryReadRepository, SummaryRow
from inventory_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
Company = Annotated[UUID, Depends(company_scope)]
VALUATION_READ = SioPermission(service=SERVICE, resource="valuation", action="read")


def get_read_repository(request: Request):
    for session in get_db_session(request):
        yield InventoryReadRepository(session)


Repository = Annotated[InventoryReadRepository, Depends(get_read_repository)]


def _counts(row: SummaryRow | None, *, with_value: bool) -> dict:
    values = {
        "products_with_positive_balance": row.positive if row else 0,
        "products_with_zero_balance": row.zero if row else 0,
        "products_with_policy": row.with_policy if row else 0,
        "products_below_minimum": row.below_minimum if row else 0,
    }
    if with_value:
        values["inventory_value"] = format_money(row.inventory_value if row else Decimal("0"))
    return values


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES], responses=QUERY_RESPONSES)
    policies_read = [auth.permission(SERVICE, "product-policies", "read")]
    sets_read = [auth.permission(SERVICE, "balances", "read"), auth.permission(SERVICE, "product-policies", "read")]

    @router.post(
        "/companies/{company_id}/branches/{branch_id}/inventory-policies/lookup",
        response_model=PolicyLookupResponse,
        summary="Política activa de 1 a 100 productos en una sucursal (spec 022, INV-1)",
        dependencies=policies_read,
    )
    def lookup_policies(
        company_id: Company, branch_id: UUID, body: PolicyLookupIn, repository: Repository
    ) -> PolicyLookupResponse:
        rows = repository.active_policies(company_id, branch_id, body.company_product_ids)
        return PolicyLookupResponse(
            items=[
                PolicyLookupItem(
                    company_product_id=product,
                    policy=(
                        PolicySummary(id=rows[product].id, minimum_stock=format_decimal(rows[product].minimum_stock),
                                      status="ACTIVE")
                        if product in rows
                        else None
                    ),
                )
                for product in body.company_product_ids
            ]
        )

    @router.post(
        "/companies/{company_id}/inventory-product-sets",
        response_model=ProductSetsResponse,
        summary="Productos (o pares) por estado de existencias y frente al mínimo, por posición (spec 022, INV-2)",
        description=(
            "Modo conductor: `IN_STOCK` es la suma de las sucursales pedidas `> 0`; `minimum_state` se cumple si al "
            "menos una sucursal tiene ese estado (un par sin saldo cuenta con 0). Productos en orden "
            "`company_product_id`; con `unit = PAIRS` (solo `BELOW_MINIMUM`), pares por faltante descendente. Sin "
            "conteos ni costos."
        ),
        dependencies=sets_read,
    )
    def product_sets(company_id: Company, body: ProductSetsIn, repository: Repository) -> ProductSetsResponse:
        if body.unit == "PAIRS":
            after = (Decimal(body.after.k[0]), body.after.id, body.after.branch_id) if body.after else None
            rows, has_more = repository.below_minimum_pairs(company_id, body.branch_ids, after=after, limit=body.limit)
            return ProductSetsResponse(
                items=[
                    PairSetItem(
                        company_product_id=row.company_product_id,
                        branch_id=row.branch_id,
                        base_quantity=format_decimal(row.base_quantity),
                        minimum_stock=format_decimal(row.minimum_stock),
                        shortfall=format_decimal(row.shortfall),
                        position=SetPosition(k=[format_decimal(row.shortfall)], id=row.company_product_id,
                                             branch_id=row.branch_id),
                    )
                    for row in rows
                ],
                has_more=has_more,
            )
        products, has_more = repository.product_set(
            company_id,
            body.branch_ids,
            stock_state=body.stock_state,
            minimum_state=body.minimum_state,
            after=body.after.id if body.after else None,
            limit=body.limit,
        )
        return ProductSetsResponse(
            items=[ProductSetItem(company_product_id=product, position=SetPosition(k=[], id=product)) for product in products],
            has_more=has_more,
        )

    @router.post(
        "/companies/{company_id}/inventory-summary",
        response_model=InventorySummaryResponse,
        response_model_exclude_none=True,
        summary="Indicadores de inventario por sucursal y consolidados (spec 022, INV-3)",
        description=(
            "Calculados en una sola consulta agregada sobre los saldos y las políticas de Inventory, sin límite de "
            "productos y sin filtrar por estado comercial. `inventory_value` solo con `include_valuation` y "
            "`perm:inventory:valuation:read`."
        ),
        dependencies=sets_read,
    )
    def inventory_summary(
        company_id: Company, body: InventorySummaryIn, request: Request, repository: Repository
    ) -> InventorySummaryResponse:
        if body.include_valuation and not evaluate_permission(get_current_claims(request).roles, VALUATION_READ):
            logger.warning("Valoración denegada en el resumen: falta %s", VALUATION_READ)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)

        rows = repository.summary(company_id, body.branch_ids)
        by_branch = {row.branch_id: row for row in rows if row.branch_id is not None}
        consolidated = next(row for row in rows if row.branch_id is None)
        return InventorySummaryResponse(
            branches=[
                BranchSummary(branch_id=branch, **_counts(by_branch.get(branch), with_value=body.include_valuation))
                for branch in body.branch_ids
            ],
            consolidated=SummaryCounts(**_counts(consolidated, with_value=body.include_valuation)),
        )

    return router
