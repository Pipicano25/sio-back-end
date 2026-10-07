"""Políticas de inventario (`contracts/rest-api.md` rutas 21–28; 013).

- Política de la empresa (21–23): `company-policies:read` / `:update`.
- Políticas de producto (24–28): `product-policies:read` / `:update`.
- Escritura solo por **usuarios humanos** miembros de la empresa; lectura con alcance
  por empresa (membresía o `platform:lookup`).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sio_auth import SIOAuth

from inventory_service.api.dependencies import access_directory, lock_timeout_ms
from inventory_service.api.identity import SERVICE, HumanIdentity, require_human_user
from inventory_service.api.openapi import POLICY_RESPONSES, TAG_POLICIES
from inventory_service.api.schemas.policies import (
    CompanyPolicyIn,
    CompanyPolicyResponse,
    CompanyPolicyUpdateIn,
    ProductPolicyIn,
    ProductPolicyPage,
    ProductPolicyResponse,
    ProductPolicyUpdateIn,
    VersionIn,
)
from inventory_service.api.schemas.queries import PageQuery, total_pages
from inventory_service.api.scope import company_scope
from inventory_service.api.services import build_validator
from inventory_service.application.policy_service import PolicyService
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.repository import SqlPolicyRepository

Company = Annotated[UUID, Depends(company_scope)]
Human = Annotated[HumanIdentity, Depends(require_human_user)]


def get_policy_service(request: Request):
    for session in get_db_session(request):
        yield PolicyService(
            SqlPolicyRepository(session, lock_timeout_ms=lock_timeout_ms(request)),
            build_validator(request),
            access_directory(request),
            request_id=request.app.state.request_id,
        )


Service = Annotated[PolicyService, Depends(get_policy_service)]


class ProductPolicyQuery(PageQuery):
    branch_id: UUID | None = None
    company_product_id: UUID | None = None
    is_active: bool | None = None


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_POLICIES], responses=POLICY_RESPONSES)
    company_read = [auth.permission(SERVICE, "company-policies", "read")]
    company_update = [auth.permission(SERVICE, "company-policies", "update")]
    product_read = [auth.permission(SERVICE, "product-policies", "read")]
    product_update = [auth.permission(SERVICE, "product-policies", "update")]
    company_path = "/companies/{company_id}/inventory-policy"
    product_path = "/companies/{company_id}/inventory-policies"

    @router.get(
        company_path,
        response_model=CompanyPolicyResponse,
        summary="Política de la empresa (o la política por defecto si no la registró)",
        dependencies=company_read,
    )
    def get_company_policy(company_id: Company, service: Service) -> CompanyPolicyResponse:
        return CompanyPolicyResponse.of(company_id, service.company_policy(company_id))

    @router.post(
        company_path,
        status_code=status.HTTP_201_CREATED,
        response_model=CompanyPolicyResponse,
        summary="Registrar la política de la empresa (una por empresa; solo FIFO)",
        dependencies=company_update,
    )
    def create_company_policy(company_id: UUID, body: CompanyPolicyIn, identity: Human, service: Service) -> CompanyPolicyResponse:
        return CompanyPolicyResponse.of(company_id, service.create_company_policy(company_id, body, identity.subject))

    @router.put(
        company_path,
        response_model=CompanyPolicyResponse,
        summary="Actualizar la política de la empresa con control de versión",
        dependencies=company_update,
    )
    def update_company_policy(
        company_id: UUID, body: CompanyPolicyUpdateIn, identity: Human, service: Service
    ) -> CompanyPolicyResponse:
        return CompanyPolicyResponse.of(company_id, service.update_company_policy(company_id, body, identity.subject))

    @router.get(product_path, response_model=ProductPolicyPage, summary="Políticas de producto", dependencies=product_read)
    def list_product_policies(
        company_id: Company, query: Annotated[ProductPolicyQuery, Query()], service: Service
    ) -> ProductPolicyPage:
        result = service.list_product_policies(
            company_id,
            branch_id=query.branch_id,
            product_id=query.company_product_id,
            is_active=query.is_active,
            page=query.page,
            page_size=query.page_size,
        )
        return ProductPolicyPage(
            items=[ProductPolicyResponse.of(row) for row in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        f"{product_path}/{{policy_id}}",
        response_model=ProductPolicyResponse,
        summary="Política de producto por id",
        dependencies=product_read,
    )
    def get_product_policy(company_id: Company, policy_id: UUID, service: Service) -> ProductPolicyResponse:
        return ProductPolicyResponse.of(service.product_policy(company_id, policy_id))

    @router.post(
        product_path,
        status_code=status.HTTP_201_CREATED,
        response_model=ProductPolicyResponse,
        summary="Crear la política de un producto en una sucursal (una activa)",
        dependencies=product_update,
    )
    def create_product_policy(company_id: UUID, body: ProductPolicyIn, identity: Human, service: Service) -> ProductPolicyResponse:
        return ProductPolicyResponse.of(service.create_product_policy(company_id, body, identity.subject))

    @router.put(
        f"{product_path}/{{policy_id}}",
        response_model=ProductPolicyResponse,
        summary="Actualizar una política de producto con control de versión",
        dependencies=product_update,
    )
    def update_product_policy(
        company_id: UUID, policy_id: UUID, body: ProductPolicyUpdateIn, identity: Human, service: Service
    ) -> ProductPolicyResponse:
        return ProductPolicyResponse.of(service.update_product_policy(company_id, policy_id, body, identity.subject))

    @router.post(
        f"{product_path}/{{policy_id}}/deactivate",
        response_model=ProductPolicyResponse,
        summary="Inactivar una política de producto (sin eliminarla)",
        dependencies=product_update,
    )
    def deactivate_product_policy(
        company_id: UUID, policy_id: UUID, body: VersionIn, identity: Human, service: Service
    ) -> ProductPolicyResponse:
        return ProductPolicyResponse.of(service.deactivate_product_policy(company_id, policy_id, body, identity.subject))

    return router

