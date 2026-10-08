"""Ventas y líneas (`contracts/rest-api.md` rutas 1–8).

La rentabilidad se omite sin `perm:sales:sales:read-profitability` (FR-027a).

Todas exigen usuario humano (RC-05). Escrituras: permiso del recurso y asignación
`ACTIVE` a la sucursal de la venta (DS-09). Lecturas: permiso y membresía.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sio_auth import FORBIDDEN_DETAIL, SIOAuth, SioPermission, evaluate_permission
from sio_auth.dependencies import get_current_claims

from sales_service.api.dependencies import ActorDep, CompanyReader, ServicesDep
from sales_service.api.identity import SERVICE, logger
from sales_service.api.openapi import READ_RESPONSES, TAG_SALES, WRITE_RESPONSES
from sales_service.api.profitability import present, present_list
from sales_service.api.schemas.sales import (
    LineCreateIn,
    SaleCreateIn,
    SaleDetailResponse,
    SalePage,
    SaleQuery,
    SaleResponse,
    SaleUpdateIn,
    total_pages,
)


def require_also(request: Request, resource: str, action: str) -> None:
    """Permiso adicional evaluado sobre el cuerpo (crear con líneas exige `sale_details:create`)."""
    claims = get_current_claims(request)
    if not evaluate_permission(claims.roles, SioPermission(service=SERVICE, resource=resource, action=action)):
        logger.warning("Permiso adicional denegado permiso=perm:%s:%s:%s ruta=%s", SERVICE, resource, action, request.url.path)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_SALES])
    base = "/companies/{company_id}/sales"

    @router.post(
        base,
        status_code=status.HTTP_201_CREATED,
        response_model=SaleResponse,
        summary="Crear una venta en borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "create")],
    )
    def create_sale(
        company_id: UUID, body: SaleCreateIn, request: Request, actor: ActorDep, services: ServicesDep
    ) -> Response:
        if body.lines:
            require_also(request, "sale_details", "create")
        view = services.sales().create(company_id, body.to_header(), [line.to_data() for line in body.lines], actor)
        return present(request, SaleResponse.of(view), status_code=status.HTTP_201_CREATED)

    @router.get(
        base,
        response_model=SalePage,
        response_model_exclude_none=False,
        summary="Listar ventas de la empresa",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def list_sales(
        company_id: CompanyReader, query: Annotated[SaleQuery, Query()], request: Request, services: ServicesDep
    ) -> Response:
        result = services.queries().list(
            company_id,
            status=query.status,
            branch_id=query.branch_id,
            customer_id=query.company_customer_id,
            date_from=query.operation_date_from,
            date_to=query.operation_date_to,
            number=query.number,
            page=query.page,
            page_size=query.page_size,
        )
        page = SalePage(
            items=[SaleResponse.of(view, with_lines=False) for view in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )
        return present(request, page)

    @router.get(
        base + "/{sale_id}",
        response_model=SaleResponse,
        summary="Consultar una venta con sus líneas",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def get_sale(company_id: CompanyReader, sale_id: UUID, request: Request, services: ServicesDep) -> Response:
        return present(request, SaleResponse.of(services.queries().sale(company_id, sale_id)))

    @router.put(
        base + "/{sale_id}",
        response_model=SaleResponse,
        summary="Editar la cabecera de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "update")],
    )
    def update_sale(
        company_id: UUID, sale_id: UUID, body: SaleUpdateIn, request: Request, actor: ActorDep, services: ServicesDep
    ) -> Response:
        view = services.sales().update_header(company_id, sale_id, body.to_header(), body.version, actor)
        return present(request, SaleResponse.of(view))

    @router.post(
        base + "/{sale_id}/details",
        status_code=status.HTTP_201_CREATED,
        response_model=SaleResponse,
        summary="Agregar una línea a un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_details", "create")],
    )
    def add_line(
        company_id: UUID, sale_id: UUID, body: LineCreateIn, request: Request, actor: ActorDep, services: ServicesDep
    ) -> Response:
        view = services.sales().add_line(company_id, sale_id, body.to_data(), body.version, actor)
        return present(request, SaleResponse.of(view), status_code=status.HTTP_201_CREATED)

    @router.put(
        base + "/{sale_id}/details/{detail_id}",
        response_model=SaleResponse,
        summary="Modificar una línea de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_details", "update")],
    )
    def update_line(
        company_id: UUID,
        sale_id: UUID,
        detail_id: UUID,
        body: LineCreateIn,
        request: Request,
        actor: ActorDep,
        services: ServicesDep,
    ) -> Response:
        view = services.sales().update_line(company_id, sale_id, detail_id, body.to_data(), body.version, actor)
        return present(request, SaleResponse.of(view))

    @router.delete(
        base + "/{sale_id}/details/{detail_id}",
        response_model=SaleResponse,
        summary="Eliminar una línea de un borrador",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_details", "delete")],
    )
    def delete_line(
        company_id: UUID,
        sale_id: UUID,
        detail_id: UUID,
        version: Annotated[int, Query(ge=1)],
        request: Request,
        actor: ActorDep,
        services: ServicesDep,
    ) -> Response:
        view = services.sales().delete_line(company_id, sale_id, detail_id, version, actor)
        return present(request, SaleResponse.of(view))

    @router.get(
        base + "/{sale_id}/details",
        response_model=list[SaleDetailResponse],
        summary="Líneas de una venta",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_details", "read")],
    )
    def list_lines(company_id: CompanyReader, sale_id: UUID, request: Request, services: ServicesDep) -> Response:
        view = services.queries().sale(company_id, sale_id)
        return present_list(request, [SaleDetailResponse.of(line) for line in view.lines])

    return router
