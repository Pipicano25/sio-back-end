"""Router de `inventory-summary` (T115; contrato §1 y §4.4). Sin paginación ni filtros de producto."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from sio_auth import SIOAuth
from sio_auth.tokens import TokenClaims

from product_inventory_query_service.api.dependencies import ports_of, runtime_of
from product_inventory_query_service.api.filters.query_params import openapi_parameters, parse_summary_query
from product_inventory_query_service.api.listing_common import BRANCH_ROUTE_NOTE, SUMMARY_ERRORS, BranchInPath
from product_inventory_query_service.api.openapi import TAG_QUERIES
from product_inventory_query_service.api.schemas.inventory_summary import (
    BranchSummaryOut,
    InventorySummaryOut,
    SummaryCountsOut,
)
from product_inventory_query_service.api.security import SERVICE
from product_inventory_query_service.application.ports import SummaryCounts
from product_inventory_query_service.application.summary_service import inventory_summary


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES])
    permission = auth.permission(SERVICE, "inventory_summary", "read")
    description = (
        "`adopted_products` (Commercial Relationship, solo empresa) y, por sucursal y consolidado, los productos "
        "con saldo positivo, con saldo registrado en cero, con política y bajo mínimo (Inventory). Un producto "
        "sin registro de saldo no cuenta en ninguno; los indicadores de Inventory pueden incluir productos "
        "inactivos o sin control de inventario que conservan saldo. Resumen solo operativo: sin costos ni "
        "valoración económica (fuera del alcance de la spec 022). Permiso: "
        "`perm:product-inventory-query:inventory_summary:read`."
    )

    async def run(company_id: UUID, branch_id: UUID | None, request: Request):
        branch_ids = parse_summary_query(request.query_params.multi_items(), branch_id=branch_id)
        runtime = runtime_of(request)
        result = await inventory_summary(
            company_id, branch_ids, ports_of(request),
            request_budget_seconds=runtime.request_budget_seconds, max_parallel_calls=runtime.max_parallel_calls,
        )

        def counts(values: SummaryCounts) -> dict:
            return {
                "products_with_positive_balance": values.products_with_positive_balance,
                "products_with_zero_balance": values.products_with_zero_balance,
                "products_with_policy": values.products_with_policy,
                "products_below_minimum": values.products_below_minimum,
            }

        return InventorySummaryOut(
            company_id=result.company_id,
            resolved_at=result.resolved_at,
            adopted_products=result.adopted_products,
            branches=[BranchSummaryOut(branch_id=b, **counts(result.summary.branches[b])) for b in result.branch_ids],
            consolidated=SummaryCountsOut(**counts(result.summary.consolidated)),
        )

    @router.get(
        "/companies/{company_id}/inventory-summary",
        response_model=InventorySummaryOut,
        summary="Consultar los indicadores operativos de inventario por sucursal y consolidados",
        description=description,
        responses=SUMMARY_ERRORS,
        openapi_extra={"parameters": openapi_parameters(None)},
    )
    async def get_inventory_summary(company_id: UUID, request: Request, claims: TokenClaims = permission):
        del claims  # solo el permiso funcional: el resumen no tiene bloques condicionados
        return await run(company_id, None, request)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/inventory-summary",
        response_model=InventorySummaryOut,
        summary="Consultar los indicadores operativos de inventario de una sucursal",
        description=description + " " + BRANCH_ROUTE_NOTE + " `adopted_products` sigue siendo de la empresa "
        "(Commercial Relationship no tiene adopción por sucursal); `branches` tiene solo la sucursal de la ruta y "
        "`consolidated` coincide con ella.",
        responses=SUMMARY_ERRORS,
        openapi_extra={"parameters": openapi_parameters(None, branch_in_path=True)},
    )
    async def get_branch_inventory_summary(company_id: UUID, branch_id: BranchInPath, request: Request,
                                           claims: TokenClaims = permission):
        del claims
        return await run(company_id, branch_id, request)

    return router
