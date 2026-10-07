"""Ajustes manuales (`contracts/rest-api.md` rutas 11–13; 013).

- Ruta 11: `perm:inventory:adjustments:create`, **usuario humano** (una cuenta de
  servicio recibe `403` aunque tenga el permiso) y asignación `ACTIVE` a la sucursal.
- Rutas 12–13: `perm:inventory:adjustments:read` y alcance por empresa.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sio_auth import SIOAuth

from inventory_service.api.dependencies import access_directory, lock_timeout_ms
from inventory_service.api.identity import SERVICE, HumanIdentity, require_human_user
from inventory_service.api.openapi import ADJUSTMENT_RESPONSES, QUERY_RESPONSES, TAG_ADJUSTMENTS
from inventory_service.api.schemas.adjustments import (
    AdjustmentIn,
    AdjustmentPage,
    AdjustmentQuery,
    InventoryAdjustmentResponse,
)
from inventory_service.api.schemas.queries import total_pages
from inventory_service.api.scope import company_scope
from inventory_service.application.exceptions import NotFoundError
from inventory_service.api.services import build_validator
from inventory_service.application.adjustment_service import AdjustmentService
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.repository import AdjustmentQueries, SqlInventoryRepository


def get_adjustment_service(request: Request):
    for session in get_db_session(request):
        yield AdjustmentService(
            SqlInventoryRepository(session, lock_timeout_ms=lock_timeout_ms(request)),
            AdjustmentQueries(session),
            build_validator(request),
            access_directory(request),
            request_id=request.app.state.request_id,
        )


Service = Annotated[AdjustmentService, Depends(get_adjustment_service)]
Company = Annotated[UUID, Depends(company_scope)]


def get_adjustment_queries(request: Request):
    for session in get_db_session(request):
        yield AdjustmentQueries(session)


Queries = Annotated[AdjustmentQueries, Depends(get_adjustment_queries)]


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_ADJUSTMENTS])
    create = [auth.permission(SERVICE, "adjustments", "create")]

    @router.post(
        "/companies/{company_id}/inventory-adjustments",
        status_code=status.HTTP_201_CREATED,
        response_model=InventoryAdjustmentResponse,
        summary="Registrar y aplicar un ajuste manual (usuario asignado a la sucursal)",
        responses=ADJUSTMENT_RESPONSES,
        dependencies=create,
    )
    def register_adjustment(
        company_id: UUID,
        body: AdjustmentIn,
        response: Response,
        identity: Annotated[HumanIdentity, Depends(require_human_user)],
        service: Service,
    ) -> InventoryAdjustmentResponse:
        result = service.register(company_id, body, identity.subject)
        if not result.created:
            response.status_code = status.HTTP_200_OK
        return InventoryAdjustmentResponse.of(result.adjustment, result.movement)

    read = [auth.permission(SERVICE, "adjustments", "read")]

    @router.get(
        "/companies/{company_id}/inventory-adjustments",
        response_model=AdjustmentPage,
        summary="Ajustes de la empresa (más recientes primero)",
        responses=QUERY_RESPONSES,
        dependencies=read,
    )
    def list_adjustments(company_id: Company, query: Annotated[AdjustmentQuery, Query()], queries: Queries) -> AdjustmentPage:
        result = queries.list(
            company_id,
            branch_id=query.branch_id,
            product_id=query.company_product_id,
            adjustment_type=query.adjustment_type,
            count_id=query.inventory_count_id,
            created_from=query.created_at_from,
            created_to=query.created_at_to,
            page=query.page,
            page_size=query.page_size,
        )
        return AdjustmentPage(
            items=[InventoryAdjustmentResponse.of(row, movement) for row, movement in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        "/companies/{company_id}/inventory-adjustments/{adjustment_id}",
        response_model=InventoryAdjustmentResponse,
        summary="Ajuste por id con su movimiento",
        responses=QUERY_RESPONSES,
        dependencies=read,
    )
    def get_adjustment(company_id: Company, adjustment_id: UUID, queries: Queries) -> InventoryAdjustmentResponse:
        found = queries.get(company_id, adjustment_id)
        if found is None:
            raise NotFoundError()
        return InventoryAdjustmentResponse.of(*found)

    return router
