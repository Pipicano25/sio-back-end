"""Clientes que pueden comprar en la empresa (selección del cliente al crear la venta).

Lectura con membresía (sin asignación a la sucursal). Lista identidades `ACTIVE` de Party Identity con su estado
como cliente de la empresa: `ACTIVE`, `INACTIVE` (no puede comprar, con el motivo) o `NOT_CUSTOMER` (se registra
automáticamente al crear la venta con su `person_identity_id` u `organization_identity_id`).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sio_auth import SIOAuth

from sales_service.api.dependencies import ActorDep, CompanyReader, ServicesDep
from sales_service.api.identity import SERVICE
from sales_service.api.openapi import READ_RESPONSES, TAG_SALES
from sales_service.api.schemas.sales import SaleCustomerPage, SaleCustomerQuery, SaleCustomerResponse, total_pages


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_SALES])

    @router.get(
        "/companies/{company_id}/sale-customers",
        response_model=SaleCustomerPage,
        summary="Listar las personas u organizaciones a las que se puede vender",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def list_sale_customers(
        company_id: CompanyReader,
        query: Annotated[SaleCustomerQuery, Query()],
        actor: ActorDep,
        services: ServicesDep,
    ) -> SaleCustomerPage:
        company = services.resolver().company(company_id)
        result = services.sale_customers(actor).list(
            company, query.customer_kind, query.search, query.page, query.page_size
        )
        return SaleCustomerPage(
            items=[SaleCustomerResponse.of(item) for item in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    return router
