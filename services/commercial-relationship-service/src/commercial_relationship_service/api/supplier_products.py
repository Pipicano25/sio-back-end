"""Rutas de productos de proveedor (`contracts/rest-api.md` §2 de la 010, contrato Provider)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_scope_service,
    get_supplier_product_repository,
    get_supplier_product_service,
)
from commercial_relationship_service.api.filters.supplier_product_filters import (
    SupplierProductFilters,
)
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.supplier_product import (
    SupplierProductCreate,
    SupplierProductResponse,
    SupplierProductUpdate,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.supplier_product_service import (
    SupplierProductService,
)

RESOURCE = "supplier_products"
BASE = "/supplier-products"


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        supplier_product_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_supplier_product_repository),
    ):
        return load_scoped(
            repository.get,
            supplier_product_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de productos de proveedor."""
    router = APIRouter(tags=["Productos de proveedor"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}" + BASE,
        response_model=PaginatedResponse[SupplierProductResponse],
        dependencies=[permission("read")],
        summary="Listar los productos de proveedor de una empresa",
    )
    def list_supplier_products(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        filters: SupplierProductFilters = Depends(),
        repository=Depends(get_supplier_product_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[SupplierProductResponse](
            items=[SupplierProductResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}" + BASE,
        response_model=SupplierProductResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Registrar que un proveedor suministra un producto empresarial",
    )
    def create_supplier_product(
        body: SupplierProductCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: SupplierProductService = Depends(get_supplier_product_service),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return SupplierProductResponse.model_validate(model)

    @router.get(
        BASE + "/{supplier_product_id}",
        response_model=SupplierProductResponse,
        dependencies=[permission("read")],
        summary="Consultar un producto de proveedor por UUID (Provider)",
    )
    def get_supplier_product(current=Depends(_resource(write=False, lookup=True))):
        return SupplierProductResponse.model_validate(current)

    @router.put(
        BASE + "/{supplier_product_id}",
        response_model=SupplierProductResponse,
        dependencies=[permission("update")],
        summary="Modificar un producto de proveedor (en cualquier estado)",
    )
    def update_supplier_product(
        body: SupplierProductUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: SupplierProductService = Depends(get_supplier_product_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return SupplierProductResponse.model_validate(model)

    @router.post(
        BASE + "/{supplier_product_id}/deactivate",
        response_model=SupplierProductResponse,
        dependencies=[permission("delete")],
        summary="Inactivar un producto de proveedor",
    )
    def deactivate_supplier_product(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: SupplierProductService = Depends(get_supplier_product_service),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return SupplierProductResponse.model_validate(model)

    @router.post(
        BASE + "/{supplier_product_id}/reactivate",
        response_model=SupplierProductResponse,
        dependencies=[permission("update")],
        summary="Reactivar un producto de proveedor",
    )
    def reactivate_supplier_product(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: SupplierProductService = Depends(get_supplier_product_service),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return SupplierProductResponse.model_validate(model)

    return router
