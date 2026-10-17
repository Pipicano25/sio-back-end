"""Rutas de presentaciones empresariales (`contracts/rest-api.md` §1 de la 010, contrato Provider)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_presentation_repository,
    get_presentation_service,
    get_scope_service,
)
from commercial_relationship_service.api.filters.company_product_presentation_filters import (
    CompanyProductPresentationFilters,
)
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.company_product_presentation import (
    CompanyProductPresentationCreate,
    CompanyProductPresentationResponse,
    CompanyProductPresentationUpdate,
    PresentationBatchLookupItem,
    PresentationBatchLookupRequest,
    PresentationBatchLookupResponse,
    PresentationByProductItem,
    PresentationsByProductsRequest,
    PresentationsByProductsResponse,
)
from commercial_relationship_service.application.company_product_presentation_service import (
    CompanyProductPresentationService,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)

RESOURCE = "company_product_presentations"
BASE = "/company-product-presentations"
_BATCH_FIELDS = (
    "company_id",
    "company_product_id",
    "global_product_presentation_id",
    "is_purchasable",
    "is_sellable",
    "is_default_purchase",
    "is_default_sale",
    "status",
    "version",
    # Spec 022 (CR-2): aditivos.
    "internal_code",
    "sku",
    "reference_code",
)


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        presentation_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_presentation_repository),
    ):
        return load_scoped(
            repository.get,
            presentation_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de presentaciones empresariales."""
    router = APIRouter(tags=["Presentaciones empresariales"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}" + BASE,
        response_model=PaginatedResponse[CompanyProductPresentationResponse],
        dependencies=[permission("read")],
        summary="Listar las presentaciones empresariales de una empresa",
    )
    def list_presentations(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        filters: CompanyProductPresentationFilters = Depends(),
        repository=Depends(get_presentation_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[CompanyProductPresentationResponse](
            items=[CompanyProductPresentationResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}" + BASE,
        response_model=CompanyProductPresentationResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Adoptar una presentación global para un producto empresarial",
    )
    def adopt_presentation(
        body: CompanyProductPresentationCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: CompanyProductPresentationService = Depends(get_presentation_service),
    ):
        model = service.adopt(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return CompanyProductPresentationResponse.model_validate(model)

    @router.post(
        "/companies/{company_id}" + BASE + "/by-products",
        response_model=PresentationsByProductsResponse,
        dependencies=[permission("read")],
        summary="Presentaciones de varios productos empresariales (spec 022, CR-2)",
        description=(
            "Todas las presentaciones de hasta 100 productos de la empresa, en orden `company_product_id, id`. "
            "Los productos de otra empresa no aparecen. `status` por defecto `ALL`."
        ),
    )
    def presentations_by_products(
        body: PresentationsByProductsRequest,
        company_id: UUID = Depends(company_dependency(write=False, lookup=True)),
        repository=Depends(get_presentation_repository),
    ):
        rows = repository.list_by_products(company_id, body.company_product_ids, status=body.status)
        return PresentationsByProductsResponse(items=[PresentationByProductItem.model_validate(row) for row in rows])

    @router.post(
        BASE + "/batch-lookup",
        response_model=PresentationBatchLookupResponse,
        dependencies=[permission("read")],
        summary="Consultar presentaciones empresariales por lotes (Provider)",
    )
    def batch_lookup(
        body: PresentationBatchLookupRequest,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        service: CompanyProductPresentationService = Depends(get_presentation_service),
    ):
        items = service.batch_lookup(body.ids, identity=identity, scope=scope)
        return PresentationBatchLookupResponse(
            items=[
                PresentationBatchLookupItem(id=item.id, found=False)
                if item.model is None
                else PresentationBatchLookupItem(
                    id=item.id,
                    found=True,
                    **{name: getattr(item.model, name) for name in _BATCH_FIELDS},
                )
                for item in items
            ]
        )

    @router.get(
        BASE + "/{presentation_id}",
        response_model=CompanyProductPresentationResponse,
        dependencies=[permission("read")],
        summary="Consultar una presentación empresarial por UUID (Provider)",
    )
    def get_presentation(current=Depends(_resource(write=False, lookup=True))):
        return CompanyProductPresentationResponse.model_validate(current)

    @router.put(
        BASE + "/{presentation_id}",
        response_model=CompanyProductPresentationResponse,
        dependencies=[permission("update")],
        summary="Modificar una presentación empresarial (en cualquier estado)",
    )
    def update_presentation(
        body: CompanyProductPresentationUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyProductPresentationService = Depends(get_presentation_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return CompanyProductPresentationResponse.model_validate(model)

    @router.post(
        BASE + "/{presentation_id}/deactivate",
        response_model=CompanyProductPresentationResponse,
        dependencies=[permission("delete")],
        summary="Inactivar una presentación empresarial",
    )
    def deactivate_presentation(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: CompanyProductPresentationService = Depends(get_presentation_service),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return CompanyProductPresentationResponse.model_validate(model)

    @router.post(
        BASE + "/{presentation_id}/reactivate",
        response_model=CompanyProductPresentationResponse,
        dependencies=[permission("update")],
        summary="Reactivar una presentación empresarial",
    )
    def reactivate_presentation(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: CompanyProductPresentationService = Depends(get_presentation_service),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return CompanyProductPresentationResponse.model_validate(model)

    return router
