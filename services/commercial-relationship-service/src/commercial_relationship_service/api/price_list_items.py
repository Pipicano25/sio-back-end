"""Rutas de precios de lista (`contracts/rest-api.md` §5 de la 010, contrato Provider).

`currency_code` de cada precio es el de su lista (solo lectura) y `unit_price`
se presenta con los decimales de esa moneda (DS-10, R-11).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_price_list_item_repository,
    get_price_list_item_service,
    get_price_list_repository,
    get_scope_service,
)
from commercial_relationship_service.api.filters.price_list_item_filters import (
    PriceListItemFilters,
)
from commercial_relationship_service.api.openapi import TAG_PRICE_LIST_ITEMS
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.price_list_item import (
    PriceChangeRequest,
    PriceChangeResponse,
    PriceListItemCreate,
    PriceListItemResponse,
    PriceListItemUpdate,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.price_list_item_service import (
    PriceListItemService,
)

RESOURCE = "price_list_items"
BASE = "/price-list-items"
_FIELDS = tuple(name for name in PriceListItemResponse.model_fields if name != "currency_code")


def item_response(model, currency_code: str) -> PriceListItemResponse:
    """Representación de un precio con la moneda de su lista."""
    return PriceListItemResponse(
        **{name: getattr(model, name) for name in _FIELDS}, currency_code=currency_code
    )


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        price_list_item_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_price_list_item_repository),
    ):
        return load_scoped(
            repository.get,
            price_list_item_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de precios de lista."""
    router = APIRouter(tags=[TAG_PRICE_LIST_ITEMS])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    def currencies(list_repository, list_ids) -> dict[UUID, str]:
        return {row.id: row.currency_code for row in list_repository.get_many(list(set(list_ids)))}

    @router.get(
        "/companies/{company_id}" + BASE,
        response_model=PaginatedResponse[PriceListItemResponse],
        dependencies=[permission("read")],
        summary="Listar los precios de lista de una empresa",
    )
    def list_items(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        filters: PriceListItemFilters = Depends(),
        repository=Depends(get_price_list_item_repository),
        list_repository=Depends(get_price_list_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=None,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
            conditions=() if filters.applicable_at is None else repository.applicable_at(filters.applicable_at),
        )
        currency_by_list = currencies(list_repository, [item.price_list_id for item in page.items])
        return PaginatedResponse[PriceListItemResponse](
            items=[item_response(item, currency_by_list[item.price_list_id]) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}" + BASE,
        response_model=PriceListItemResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Registrar un precio en una lista",
    )
    def create_item(
        body: PriceListItemCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: PriceListItemService = Depends(get_price_list_item_service),
        list_repository=Depends(get_price_list_repository),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return item_response(model, list_repository.get(model.price_list_id).currency_code)

    @router.get(
        BASE + "/{price_list_item_id}",
        response_model=PriceListItemResponse,
        dependencies=[permission("read")],
        summary="Consultar un precio de lista por UUID (Provider)",
    )
    def get_item(
        current=Depends(_resource(write=False, lookup=True)),
        list_repository=Depends(get_price_list_repository),
    ):
        return item_response(current, list_repository.get(current.price_list_id).currency_code)

    @router.put(
        BASE + "/{price_list_item_id}",
        response_model=PriceListItemResponse,
        dependencies=[permission("update")],
        summary="Modificar un precio (futuro: valor y vigencia; en vigencia: solo su fin)",
    )
    def update_item(
        body: PriceListItemUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PriceListItemService = Depends(get_price_list_item_service),
        list_repository=Depends(get_price_list_repository),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return item_response(model, list_repository.get(model.price_list_id).currency_code)

    @router.post(
        BASE + "/{price_list_item_id}/change-price",
        response_model=PriceChangeResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("update")],
        summary="Cambiar el precio: cierra el vigente y crea el nuevo en una sola operación",
    )
    def change_price(
        body: PriceChangeRequest,
        response: Response,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PriceListItemService = Depends(get_price_list_item_service),
        list_repository=Depends(get_price_list_repository),
    ):
        new, previous = service.change_price(
            current,
            unit_price=body.unit_price,
            effective_from=body.effective_from,
            version=body.version,
            actor=actor,
        )
        currency_code = list_repository.get(new.price_list_id).currency_code
        response.headers["Location"] = f"/api/v1{BASE}/{new.id}"
        return PriceChangeResponse(
            item=item_response(new, currency_code), previous=item_response(previous, currency_code)
        )

    @router.post(
        BASE + "/{price_list_item_id}/deactivate",
        response_model=PriceListItemResponse,
        dependencies=[permission("delete")],
        summary="Inactivar un precio de lista",
    )
    def deactivate_item(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: PriceListItemService = Depends(get_price_list_item_service),
        list_repository=Depends(get_price_list_repository),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return item_response(model, list_repository.get(model.price_list_id).currency_code)

    @router.post(
        BASE + "/{price_list_item_id}/reactivate",
        response_model=PriceListItemResponse,
        dependencies=[permission("update")],
        summary="Reactivar un precio de lista",
    )
    def reactivate_item(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PriceListItemService = Depends(get_price_list_item_service),
        list_repository=Depends(get_price_list_repository),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return item_response(model, list_repository.get(model.price_list_id).currency_code)

    return router
