"""Conteos físicos (`contracts/rest-api.md` rutas 14–20; 013).

- Rutas 14–18: `perm:inventory:counts:create`, **usuario humano** y asignación `ACTIVE`
  a la sucursal del conteo.
- Rutas 19–20: `perm:inventory:counts:read` y alcance por empresa.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sio_auth import SIOAuth

from inventory_service.api.dependencies import access_directory, lock_timeout_ms
from inventory_service.api.identity import SERVICE, HumanIdentity, require_human_user
from inventory_service.api.openapi import COUNT_RESPONSES, QUERY_RESPONSES, TAG_COUNTS
from inventory_service.api.schemas.counts import (
    CountCancelIn,
    CountPage,
    CountCompleteIn,
    CountCreateIn,
    CountDetailIn,
    CountTransitionIn,
    InventoryCountDetailResponse,
    InventoryCountResponse,
)
from inventory_service.api.schemas.queries import PageQuery, total_pages
from inventory_service.api.scope import company_scope
from inventory_service.api.services import build_validator
from inventory_service.application.count_service import CountService, CountView
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.repository import AdjustmentQueries, SqlCountRepository, SqlInventoryRepository


def get_count_service(request: Request):
    for session in get_db_session(request):
        timeout = lock_timeout_ms(request)
        engine = SqlInventoryRepository(session, lock_timeout_ms=timeout)
        yield CountService(
            SqlCountRepository(session, engine, lock_timeout_ms=timeout),
            engine,
            AdjustmentQueries(session),
            build_validator(request),
            access_directory(request),
            request_id=request.app.state.request_id,
        )


Service = Annotated[CountService, Depends(get_count_service)]
Human = Annotated[HumanIdentity, Depends(require_human_user)]
Company = Annotated[UUID, Depends(company_scope)]


class CountQuery(PageQuery):
    branch_id: UUID | None = None
    status: Literal["DRAFT", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = None


def count_response(view: CountView) -> InventoryCountResponse:
    return InventoryCountResponse.of(view.count, view.details, view.adjustments)


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_COUNTS], responses=COUNT_RESPONSES)
    create = [auth.permission(SERVICE, "counts", "create")]
    base = "/companies/{company_id}/inventory-counts"

    @router.post(
        base,
        status_code=status.HTTP_201_CREATED,
        response_model=InventoryCountResponse,
        summary="Crear un conteo físico (DRAFT)",
        dependencies=create,
    )
    def create_count(company_id: UUID, body: CountCreateIn, identity: Human, service: Service) -> InventoryCountResponse:
        return count_response(service.create(company_id, body, identity.subject))

    @router.post(
        f"{base}/{{count_id}}/start",
        response_model=InventoryCountResponse,
        summary="Iniciar el conteo (uno en curso por sucursal)",
        dependencies=create,
    )
    def start_count(
        company_id: UUID, count_id: UUID, body: CountTransitionIn, identity: Human, service: Service
    ) -> InventoryCountResponse:
        return count_response(service.start(company_id, count_id, body, identity.subject))

    @router.put(
        f"{base}/{{count_id}}/details/{{company_product_id}}",
        response_model=InventoryCountDetailResponse,
        summary="Registrar (o reemplazar) la cantidad contada de un producto",
        dependencies=create,
    )
    def register_detail(
        company_id: UUID,
        count_id: UUID,
        company_product_id: UUID,
        body: CountDetailIn,
        identity: Human,
        service: Service,
    ) -> InventoryCountDetailResponse:
        return InventoryCountDetailResponse.of(
            service.register_detail(company_id, count_id, company_product_id, body, identity.subject)
        )

    @router.post(
        f"{base}/{{count_id}}/complete",
        response_model=InventoryCountResponse,
        summary="Completar: aplica todas las diferencias como ajustes, todo o nada",
        dependencies=create,
    )
    def complete_count(
        company_id: UUID, count_id: UUID, body: CountCompleteIn, identity: Human, service: Service
    ) -> InventoryCountResponse:
        return count_response(service.complete(company_id, count_id, body, identity.subject))

    @router.post(
        f"{base}/{{count_id}}/cancel",
        response_model=InventoryCountResponse,
        summary="Cancelar el conteo (DRAFT o IN_PROGRESS) con motivo",
        dependencies=create,
    )
    def cancel_count(
        company_id: UUID, count_id: UUID, body: CountCancelIn, identity: Human, service: Service
    ) -> InventoryCountResponse:
        return count_response(service.cancel(company_id, count_id, body, identity.subject))

    read = [auth.permission(SERVICE, "counts", "read")]

    @router.get(base, response_model=CountPage, summary="Conteos de la empresa", responses=QUERY_RESPONSES, dependencies=read)
    def list_counts(company_id: Company, query: Annotated[CountQuery, Query()], service: Service) -> CountPage:
        result = service.list(company_id, branch_id=query.branch_id, status=query.status, page=query.page, page_size=query.page_size)
        return CountPage(
            items=[InventoryCountResponse.of(row) for row in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        f"{base}/{{count_id}}",
        response_model=InventoryCountResponse,
        summary="Conteo con sus detalles y, si está completado, sus ajustes",
        responses=QUERY_RESPONSES,
        dependencies=read,
    )
    def get_count(company_id: Company, count_id: UUID, service: Service) -> InventoryCountResponse:
        return count_response(service.view(company_id, count_id))

    return router
