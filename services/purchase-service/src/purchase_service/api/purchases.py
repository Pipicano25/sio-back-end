"""Compras y líneas (`contracts/rest-api.md` rutas 1–8).

Todas exigen usuario humano (RC-05). Escrituras: permiso del recurso y asignación
`ACTIVE` a la sucursal de la compra (DS-09). Lecturas: permiso y membresía.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sio_auth import FORBIDDEN_DETAIL, SIOAuth, SioPermission, evaluate_permission
from sio_auth.dependencies import get_current_claims

from purchase_service.api.dependencies import ActorDep, CompanyReader, ServicesDep
from purchase_service.api.identity import SERVICE, logger
from purchase_service.api.openapi import READ_RESPONSES, TAG_PURCHASES, WRITE_RESPONSES
from purchase_service.api.schemas.purchases import (
    LineCreateIn,
    PurchaseCreateIn,
    PurchaseDetailResponse,
    PurchasePage,
    PurchaseQuery,
    PurchaseResponse,
    PurchaseUpdateIn,
    total_pages,
)


def require_also(request: Request, resource: str, action: str) -> None:
    """Permiso adicional evaluado sobre el cuerpo (crear con líneas exige `purchase_details:create`)."""
    claims = get_current_claims(request)
    if not evaluate_permission(claims.roles, SioPermission(service=SERVICE, resource=resource, action=action)):
        logger.warning("Permiso adicional denegado permiso=perm:%s:%s:%s ruta=%s", SERVICE, resource, action, request.url.path)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_PURCHASES])
    base = "/companies/{company_id}/purchases"

    @router.post(
        base,
        status_code=status.HTTP_201_CREATED,
        response_model=PurchaseResponse,
        summary="Crear una compra en borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "create")],
    )
    def create_purchase(
        company_id: UUID, body: PurchaseCreateIn, request: Request, actor: ActorDep, services: ServicesDep
    ) -> PurchaseResponse:
        if body.lines:
            require_also(request, "purchase_details", "create")
        view = services.purchases().create(company_id, body.to_header(), [line.to_data() for line in body.lines], actor)
        return PurchaseResponse.of(view)

    @router.get(
        base,
        response_model=PurchasePage,
        response_model_exclude_none=False,
        summary="Listar compras de la empresa",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "read")],
    )
    def list_purchases(
        company_id: CompanyReader, query: Annotated[PurchaseQuery, Query()], services: ServicesDep
    ) -> PurchasePage:
        result = services.queries().list(
            company_id,
            status=query.status,
            branch_id=query.branch_id,
            supplier_id=query.company_supplier_id,
            date_from=query.operation_date_from,
            date_to=query.operation_date_to,
            number=query.number,
            page=query.page,
            page_size=query.page_size,
        )
        return PurchasePage(
            items=[PurchaseResponse.of(view, with_lines=False) for view in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        base + "/{purchase_id}",
        response_model=PurchaseResponse,
        summary="Consultar una compra con sus líneas",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "read")],
    )
    def get_purchase(company_id: CompanyReader, purchase_id: UUID, services: ServicesDep) -> PurchaseResponse:
        return PurchaseResponse.of(services.queries().purchase(company_id, purchase_id))

    @router.put(
        base + "/{purchase_id}",
        response_model=PurchaseResponse,
        summary="Editar la cabecera de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "update")],
    )
    def update_purchase(
        company_id: UUID, purchase_id: UUID, body: PurchaseUpdateIn, actor: ActorDep, services: ServicesDep
    ) -> PurchaseResponse:
        view = services.purchases().update_header(company_id, purchase_id, body.to_header(), body.version, actor)
        return PurchaseResponse.of(view)

    @router.post(
        base + "/{purchase_id}/details",
        status_code=status.HTTP_201_CREATED,
        response_model=PurchaseResponse,
        summary="Agregar una línea a un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_details", "create")],
    )
    def add_line(
        company_id: UUID, purchase_id: UUID, body: LineCreateIn, actor: ActorDep, services: ServicesDep
    ) -> PurchaseResponse:
        view = services.purchases().add_line(company_id, purchase_id, body.to_data(), body.version, actor)
        return PurchaseResponse.of(view)

    @router.put(
        base + "/{purchase_id}/details/{detail_id}",
        response_model=PurchaseResponse,
        summary="Modificar una línea de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_details", "update")],
    )
    def update_line(
        company_id: UUID,
        purchase_id: UUID,
        detail_id: UUID,
        body: LineCreateIn,
        actor: ActorDep,
        services: ServicesDep,
    ) -> PurchaseResponse:
        view = services.purchases().update_line(company_id, purchase_id, detail_id, body.to_data(), body.version, actor)
        return PurchaseResponse.of(view)

    @router.delete(
        base + "/{purchase_id}/details/{detail_id}",
        response_model=PurchaseResponse,
        summary="Eliminar una línea de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_details", "delete")],
    )
    def delete_line(
        company_id: UUID,
        purchase_id: UUID,
        detail_id: UUID,
        version: Annotated[int, Query(ge=1)],
        actor: ActorDep,
        services: ServicesDep,
    ) -> PurchaseResponse:
        return PurchaseResponse.of(services.purchases().delete_line(company_id, purchase_id, detail_id, version, actor))

    @router.get(
        base + "/{purchase_id}/details",
        response_model=list[PurchaseDetailResponse],
        summary="Líneas de una compra",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_details", "read")],
    )
    def list_lines(company_id: CompanyReader, purchase_id: UUID, services: ServicesDep) -> list[PurchaseDetailResponse]:
        view = services.queries().purchase(company_id, purchase_id)
        return [PurchaseDetailResponse.of(line) for line in view.lines]

    return router
