"""Rutas de clientes (`contracts/rest-api.md` §2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import check_company, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_customer_repository,
    get_customer_service,
    get_identity,
    get_scope_service,
)
from commercial_relationship_service.api.filters.company_customer_filters import CompanyCustomerFilters
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.company_customer import (
    CompanyCustomerCreate,
    CompanyCustomerResponse,
    CompanyCustomerUpdate,
)
from commercial_relationship_service.application.company_customer_service import (
    CompanyCustomerService,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)

RESOURCE = "company_customers"


def _company(*, write: bool):
    def dependency(
        company_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
    ) -> UUID:
        check_company(company_id, identity=identity, scope=scope, write=write)
        return company_id

    return dependency


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        company_customer_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_customer_repository),
    ):
        return load_scoped(
            repository.get,
            company_customer_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de clientes."""
    router = APIRouter(tags=["Clientes"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}/company-customers",
        response_model=PaginatedResponse[CompanyCustomerResponse],
        dependencies=[permission("read")],
        summary="Listar los clientes de una empresa",
    )
    def list_customers(
        company_id: UUID = Depends(_company(write=False)),
        pagination: PaginationParams = Depends(),
        filters: CompanyCustomerFilters = Depends(),
        repository=Depends(get_customer_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[CompanyCustomerResponse](
            items=[CompanyCustomerResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}/company-customers",
        response_model=CompanyCustomerResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Incorporar un cliente",
    )
    def create_customer(
        body: CompanyCustomerCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(_company(write=True)),
        service: CompanyCustomerService = Depends(get_customer_service),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1/company-customers/{model.id}"
        return CompanyCustomerResponse.model_validate(model)

    @router.get(
        "/company-customers/{company_customer_id}",
        response_model=CompanyCustomerResponse,
        dependencies=[permission("read")],
        summary="Consultar un cliente por UUID (Provider)",
    )
    def get_customer(current=Depends(_resource(write=False, lookup=True))):
        return CompanyCustomerResponse.model_validate(current)

    @router.put(
        "/company-customers/{company_customer_id}",
        response_model=CompanyCustomerResponse,
        dependencies=[permission("update")],
        summary="Modificar un cliente (en cualquier estado)",
    )
    def update_customer(
        body: CompanyCustomerUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyCustomerService = Depends(get_customer_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return CompanyCustomerResponse.model_validate(model)

    @router.post(
        "/company-customers/{company_customer_id}/deactivate",
        response_model=CompanyCustomerResponse,
        dependencies=[permission("delete")],
        summary="Inactivar un cliente",
    )
    def deactivate_customer(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: CompanyCustomerService = Depends(get_customer_service),
    ):
        return CompanyCustomerResponse.model_validate(
            service.deactivate(current, version=body.version, actor=actor)
        )

    @router.post(
        "/company-customers/{company_customer_id}/reactivate",
        response_model=CompanyCustomerResponse,
        dependencies=[permission("update")],
        summary="Reactivar un cliente",
    )
    def reactivate_customer(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyCustomerService = Depends(get_customer_service),
    ):
        return CompanyCustomerResponse.model_validate(
            service.reactivate(current, version=body.version, actor=actor)
        )

    return router
