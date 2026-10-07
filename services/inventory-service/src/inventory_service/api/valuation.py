"""Valoración FIFO: valor de la sucursal, capas y consumos (`contracts/rest-api.md` rutas 29–31; 013).

Permiso `perm:inventory:valuation:read` y alcance por empresa (`api/scope.py`):
membresía o cuenta de servicio con `platform:lookup`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sio_auth import SIOAuth

from inventory_service.api.identity import SERVICE
from inventory_service.api.openapi import QUERY_RESPONSES, TAG_VALUATION
from inventory_service.api.schemas.queries import PageQuery
from inventory_service.api.schemas.valuation import (
    BranchValuationResponse,
    CostConsumptionsResponse,
    CostLayer,
    LayersPage,
    LayersQuery,
)
from inventory_service.api.scope import company_scope
from inventory_service.application.valuation import ValuationService
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.valuation_repository import SqlValuationQueries

Company = Annotated[UUID, Depends(company_scope)]


def get_valuation_service(request: Request):
    for session in get_db_session(request):
        yield ValuationService(SqlValuationQueries(session))


Service = Annotated[ValuationService, Depends(get_valuation_service)]


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_VALUATION], responses=QUERY_RESPONSES)
    valuation_read = [auth.permission(SERVICE, "valuation", "read")]
    branch_base = "/companies/{company_id}/branches/{branch_id}/valuation"

    @router.get(
        branch_base,
        response_model=BranchValuationResponse,
        summary="Valor del inventario de una sucursal por producto (capas FIFO abiertas)",
        dependencies=valuation_read,
    )
    def branch_valuation(
        company_id: Company, branch_id: UUID, query: Annotated[PageQuery, Query()], service: Service
    ) -> BranchValuationResponse:
        result = service.branch(company_id, branch_id, page=query.page, page_size=query.page_size)
        return BranchValuationResponse.of(result, query.page, query.page_size)

    @router.get(
        f"{branch_base}/{{company_product_id}}/layers",
        response_model=LayersPage,
        summary="Capas de costo de un producto en orden FIFO",
        dependencies=valuation_read,
    )
    def layers(
        company_id: Company,
        branch_id: UUID,
        company_product_id: UUID,
        query: Annotated[LayersQuery, Query()],
        service: Service,
    ) -> LayersPage:
        rows, total = service.layers(
            company_id,
            branch_id,
            company_product_id,
            include_closed=query.include_closed,
            page=query.page,
            page_size=query.page_size,
        )
        return LayersPage(items=[CostLayer.of(row) for row in rows], page=query.page, page_size=query.page_size, total_records=total)

    @router.get(
        "/companies/{company_id}/inventory-movements/{movement_id}/cost-consumptions",
        response_model=CostConsumptionsResponse,
        summary="Consumos de capas de un movimiento (explican su costo)",
        dependencies=valuation_read,
    )
    def cost_consumptions(company_id: Company, movement_id: UUID, service: Service) -> CostConsumptionsResponse:
        return CostConsumptionsResponse.of(movement_id, service.consumptions(company_id, movement_id))

    return router
