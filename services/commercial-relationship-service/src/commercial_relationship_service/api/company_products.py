"""Rutas de productos empresariales (`contracts/rest-api.md` §1, contrato Provider)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import check_company, company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_product_repository,
    get_product_service,
    get_scope_service,
)
from commercial_relationship_service.api.filters.company_product_filters import CompanyProductFilters
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.company_product import (
    BatchLookupItem,
    BatchLookupRequest,
    BatchLookupResponse,
    CompanyProductCreate,
    CompanyProductResponse,
    CompanyProductSearchItem,
    CompanyProductSearchRequest,
    CompanyProductSearchResponse,
    CompanyProductUpdate,
    SearchPosition,
)
from commercial_relationship_service.application.company_product_service import (
    CompanyProductService,
    ProductSearchCriteria,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)

RESOURCE = "company_products"
_BATCH_FIELDS = (
    "company_id",
    "global_product_id",
    "internal_code",
    "display_name",
    "currency_code",
    "inventory_control_enabled",
    "lot_tracking_enabled",
    "expiration_tracking_enabled",
    "is_purchasable",
    "is_sellable",
    "purchase_tax_percentage",  # spec 021 (FR-021-08)
    "status",
    "version",
)


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
        company_product_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_product_repository),
    ):
        return load_scoped(
            repository.get,
            company_product_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def _position_value(model, key: str) -> str:
    value = getattr(model, key)
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _criteria(body: CompanyProductSearchRequest) -> ProductSearchCriteria:
    after = None

    if body.after is not None:
        raw = body.after.k[0]
        after = (datetime.fromisoformat(raw) if body.sort.key == "created_at" else raw, body.after.id)

    return ProductSearchCriteria(
        status=body.status,
        limit=body.limit,
        sort_key=body.sort.key,
        descending=body.sort.direction == "desc",
        search=body.search,
        internal_code=body.internal_code,
        sku=body.sku,
        is_purchasable=body.is_purchasable,
        is_sellable=body.is_sellable,
        inventory_control_enabled=body.inventory_control_enabled,
        company_product_ids=body.company_product_ids,
        global_product_ids=body.global_product_ids,
        after=after,
    )


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de productos empresariales."""
    router = APIRouter(tags=["Productos empresariales"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}/company-products",
        response_model=PaginatedResponse[CompanyProductResponse],
        dependencies=[permission("read")],
        summary="Listar los productos de una empresa",
    )
    def list_products(
        company_id: UUID = Depends(_company(write=False)),
        pagination: PaginationParams = Depends(),
        filters: CompanyProductFilters = Depends(),
        repository=Depends(get_product_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[CompanyProductResponse](
            items=[CompanyProductResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}/company-products/search",
        response_model=CompanyProductSearchResponse,
        dependencies=[permission("read")],
        summary="Buscar productos empresariales con continuación por posición (spec 022, CR-1)",
        description=(
            "Lectura progresiva para consumidores que paginan sin conteo. Mismos filtros que el listado, `search` "
            "extendido al SKU de las presentaciones, `internal_code` y `sku` exactos y modo evaluador con hasta 100 "
            "ids. Orden `<clave>, id`; cada elemento trae su `position`, que se reenvía en `after`. Sin "
            "`total_records`: `has_more` indica si hay más. El listado `GET` no cambia."
        ),
    )
    def search_products(
        body: CompanyProductSearchRequest,
        company_id: UUID = Depends(company_dependency(write=False, lookup=True)),
        service: CompanyProductService = Depends(get_product_service),
    ):
        rows, has_more = service.search(company_id, _criteria(body))
        return CompanyProductSearchResponse(
            items=[
                CompanyProductSearchItem.model_validate(
                    {
                        **CompanyProductResponse.model_validate(row).model_dump(),
                        "position": SearchPosition(k=[_position_value(row, body.sort.key)], id=row.id),
                    }
                )
                for row in rows
            ],
            has_more=has_more,
        )

    @router.post(
        "/companies/{company_id}/company-products",
        response_model=CompanyProductResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Adoptar un producto global en la empresa",
    )
    def adopt_product(
        body: CompanyProductCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(_company(write=True)),
        service: CompanyProductService = Depends(get_product_service),
    ):
        model = service.adopt(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1/company-products/{model.id}"
        return CompanyProductResponse.model_validate(model)

    @router.post(
        "/company-products/batch-lookup",
        response_model=BatchLookupResponse,
        dependencies=[permission("read")],
        summary="Consultar productos empresariales por lotes (Provider)",
    )
    def batch_lookup(
        body: BatchLookupRequest,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        service: CompanyProductService = Depends(get_product_service),
    ):
        items = service.batch_lookup(body.ids, identity=identity, scope=scope)
        return BatchLookupResponse(
            items=[
                BatchLookupItem(id=item.id, found=False)
                if item.model is None
                else BatchLookupItem(
                    id=item.id,
                    found=True,
                    **{name: getattr(item.model, name) for name in _BATCH_FIELDS},
                )
                for item in items
            ]
        )

    @router.get(
        "/company-products/{company_product_id}",
        response_model=CompanyProductResponse,
        dependencies=[permission("read")],
        summary="Consultar un producto empresarial por UUID (Provider)",
    )
    def get_product(current=Depends(_resource(write=False, lookup=True))):
        return CompanyProductResponse.model_validate(current)

    @router.put(
        "/company-products/{company_product_id}",
        response_model=CompanyProductResponse,
        dependencies=[permission("update")],
        summary="Modificar un producto empresarial (en cualquier estado)",
    )
    def update_product(
        body: CompanyProductUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyProductService = Depends(get_product_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return CompanyProductResponse.model_validate(model)

    @router.post(
        "/company-products/{company_product_id}/deactivate",
        response_model=CompanyProductResponse,
        dependencies=[permission("delete")],
        summary="Inactivar un producto empresarial",
    )
    def deactivate_product(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: CompanyProductService = Depends(get_product_service),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return CompanyProductResponse.model_validate(model)

    @router.post(
        "/company-products/{company_product_id}/reactivate",
        response_model=CompanyProductResponse,
        dependencies=[permission("update")],
        summary="Reactivar un producto empresarial",
    )
    def reactivate_product(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyProductService = Depends(get_product_service),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return CompanyProductResponse.model_validate(model)

    return router
