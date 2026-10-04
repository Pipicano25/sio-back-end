"""Rutas de proveedores (`contracts/rest-api.md` §3; DS-10, DS-16, DS-17)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import check_company, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_scope_service,
    get_supplier_repository,
    get_supplier_service,
)
from commercial_relationship_service.api.filters.company_supplier_filters import CompanySupplierFilters
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.company_supplier import (
    CompanySupplierCreate,
    CompanySupplierResponse,
    CompanySupplierUpdate,
    SupplierBlockRequest,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.company_supplier_service import (
    CompanySupplierService,
)

RESOURCE = "company_suppliers"


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
        company_supplier_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_supplier_repository),
    ):
        return load_scoped(
            repository.get,
            company_supplier_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de proveedores."""
    router = APIRouter(tags=["Proveedores"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    def respond(model) -> CompanySupplierResponse:
        return CompanySupplierResponse.model_validate(model)

    @router.get(
        "/companies/{company_id}/company-suppliers",
        response_model=PaginatedResponse[CompanySupplierResponse],
        dependencies=[permission("read")],
        summary="Listar los proveedores de una empresa",
    )
    def list_suppliers(
        company_id: UUID = Depends(_company(write=False)),
        pagination: PaginationParams = Depends(),
        filters: CompanySupplierFilters = Depends(),
        repository=Depends(get_supplier_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[CompanySupplierResponse](
            items=[respond(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}/company-suppliers",
        response_model=CompanySupplierResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Seleccionar un proveedor",
    )
    def create_supplier(
        body: CompanySupplierCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(_company(write=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1/company-suppliers/{model.id}"
        return respond(model)

    @router.get(
        "/company-suppliers/{company_supplier_id}",
        response_model=CompanySupplierResponse,
        dependencies=[permission("read")],
        summary="Consultar un proveedor por UUID (Provider)",
    )
    def get_supplier(current=Depends(_resource(write=False, lookup=True))):
        return respond(current)

    @router.put(
        "/company-suppliers/{company_supplier_id}",
        response_model=CompanySupplierResponse,
        dependencies=[permission("update")],
        summary="Modificar un proveedor (en cualquier estado)",
    )
    def update_supplier(
        body: CompanySupplierUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        values = body.model_dump(exclude={"version"})
        return respond(service.update(current, values, version=body.version, actor=actor))

    @router.post(
        "/company-suppliers/{company_supplier_id}/deactivate",
        response_model=CompanySupplierResponse,
        dependencies=[permission("delete")],
        summary="Inactivar un proveedor",
    )
    def deactivate_supplier(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        return respond(service.deactivate(current, version=body.version, actor=actor))

    @router.post(
        "/company-suppliers/{company_supplier_id}/reactivate",
        response_model=CompanySupplierResponse,
        dependencies=[permission("update")],
        summary="Reactivar un proveedor",
    )
    def reactivate_supplier(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        return respond(service.reactivate(current, version=body.version, actor=actor))

    @router.post(
        "/company-suppliers/{company_supplier_id}/block",
        response_model=CompanySupplierResponse,
        dependencies=[permission("delete")],
        summary="Bloquear un proveedor (motivo obligatorio)",
    )
    def block_supplier(
        body: SupplierBlockRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        return respond(
            service.block(current, block_reason=body.block_reason, version=body.version, actor=actor)
        )

    @router.post(
        "/company-suppliers/{company_supplier_id}/unblock",
        response_model=CompanySupplierResponse,
        dependencies=[permission("update")],
        summary="Desbloquear un proveedor",
    )
    def unblock_supplier(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanySupplierService = Depends(get_supplier_service),
    ):
        return respond(service.unblock(current, version=body.version, actor=actor))

    return router
