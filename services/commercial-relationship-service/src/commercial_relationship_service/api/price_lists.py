"""Rutas de listas de precios (`contracts/rest-api.md` §4 de la 010, contrato Provider)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_price_list_repository,
    get_price_list_service,
    get_scope_service,
)
from commercial_relationship_service.api.filters.price_list_filters import PriceListFilters
from commercial_relationship_service.api.openapi import TAG_PRICE_LISTS
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.price_list import (
    PriceListCreate,
    PriceListResponse,
    PriceListUpdate,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.price_list_service import PriceListService

RESOURCE = "price_lists"
BASE = "/price-lists"


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        price_list_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_price_list_repository),
    ):
        return load_scoped(
            repository.get,
            price_list_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de listas de precios."""
    router = APIRouter(tags=[TAG_PRICE_LISTS])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}" + BASE,
        response_model=PaginatedResponse[PriceListResponse],
        dependencies=[permission("read")],
        summary="Listar las listas de precios de una empresa",
    )
    def list_price_lists(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        filters: PriceListFilters = Depends(),
        repository=Depends(get_price_list_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=filters.search,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[PriceListResponse](
            items=[PriceListResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}" + BASE,
        response_model=PriceListResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Crear una lista de precios",
    )
    def create_price_list(
        body: PriceListCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: PriceListService = Depends(get_price_list_service),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return PriceListResponse.model_validate(model)

    @router.get(
        BASE + "/{price_list_id}",
        response_model=PriceListResponse,
        dependencies=[permission("read")],
        summary="Consultar una lista de precios por UUID (Provider)",
    )
    def get_price_list(current=Depends(_resource(write=False, lookup=True))):
        return PriceListResponse.model_validate(current)

    @router.put(
        BASE + "/{price_list_id}",
        response_model=PriceListResponse,
        dependencies=[permission("update")],
        summary="Modificar una lista de precios (en cualquier estado; moneda inmutable)",
    )
    def update_price_list(
        body: PriceListUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PriceListService = Depends(get_price_list_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return PriceListResponse.model_validate(model)

    @router.post(
        BASE + "/{price_list_id}/deactivate",
        response_model=PriceListResponse,
        dependencies=[permission("delete")],
        summary="Inactivar una lista de precios",
    )
    def deactivate_price_list(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: PriceListService = Depends(get_price_list_service),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return PriceListResponse.model_validate(model)

    @router.post(
        BASE + "/{price_list_id}/reactivate",
        response_model=PriceListResponse,
        dependencies=[permission("update")],
        summary="Reactivar una lista de precios",
    )
    def reactivate_price_list(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PriceListService = Depends(get_price_list_service),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return PriceListResponse.model_validate(model)

    return router
