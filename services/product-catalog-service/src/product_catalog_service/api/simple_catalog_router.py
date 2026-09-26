"""Constructor de routers para catálogos codificados simples.

Genera `GET` (colección y detalle), `POST`, `PUT`, `POST …/deactivate` y
`POST …/reactivate` con los permisos `{recurso}:{read,create,update,deactivate}`.
"""


from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.pagination import PaginationParams
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.pagination import PaginatedResponse
from product_catalog_service.api.security import permission
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.infrastructure.database import get_db_session


def build_simple_catalog_router(
    *,
    auth: SIOAuth,
    prefix: str,
    resource: str,
    tag: str,
    service_class: type[SimpleCatalogService],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    response_schema: type[BaseModel],
    extra_filters: Callable[..., Callable[[Any], Any] | None] | None = None,
    router: APIRouter | None = None,
) -> APIRouter:
    """Construye el router estándar de un catálogo codificado."""
    router = router or APIRouter(prefix=prefix, tags=[tag])

    def get_service(session: Session = Depends(get_db_session)) -> SimpleCatalogService:
        return service_class(session)

    filters_dependency = extra_filters or (lambda: None)

    @router.get(
        "",
        response_model=PaginatedResponse[response_schema],
        dependencies=[permission(auth, resource, "read")],
        summary=f"Listar {tag.lower()}",
    )
    def list_items(
        pagination: PaginationParams = Depends(),
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        code: str | None = Query(default=None, max_length=100),
        search: str | None = Query(default=None, max_length=200),
        extra=Depends(filters_dependency),
        service: SimpleCatalogService = Depends(get_service),
    ):
        result = service.list(
            page=pagination.page,
            page_size=pagination.page_size,
            status=status_filter,
            code=code,
            search=search,
            extra_filters=extra,
        )
        return PaginatedResponse.from_page(result, response_schema.model_validate)

    @router.get(
        "/{item_id}",
        response_model=response_schema,
        dependencies=[permission(auth, resource, "read")],
        summary=f"Consultar un registro de {tag.lower()}",
    )
    def get_item(item_id: UUID, service: SimpleCatalogService = Depends(get_service)):
        return response_schema.model_validate(service.get(item_id))

    @router.post(
        "",
        response_model=response_schema,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, resource, "create")],
        summary=f"Crear un registro de {tag.lower()}",
    )
    def create_item(
        body: create_schema,  # type: ignore[valid-type]
        response: Response,
        actor: CurrentSubject,
        service: SimpleCatalogService = Depends(get_service),
    ):
        entity = service.create(actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1{prefix}/{entity.id}"
        return response_schema.model_validate(entity)

    @router.put(
        "/{item_id}",
        response_model=response_schema,
        dependencies=[permission(auth, resource, "update")],
        summary=f"Modificar un registro de {tag.lower()}",
    )
    def update_item(
        item_id: UUID,
        body: update_schema,  # type: ignore[valid-type]
        actor: CurrentSubject,
        service: SimpleCatalogService = Depends(get_service),
    ):
        entity = service.update(item_id, actor=actor, **body.model_dump())
        return response_schema.model_validate(entity)

    @router.post(
        "/{item_id}/deactivate",
        response_model=response_schema,
        dependencies=[permission(auth, resource, "deactivate")],
        summary=f"Inactivar un registro de {tag.lower()}",
    )
    def deactivate_item(
        item_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: SimpleCatalogService = Depends(get_service),
    ):
        return response_schema.model_validate(
            service.deactivate(item_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{item_id}/reactivate",
        response_model=response_schema,
        dependencies=[permission(auth, resource, "deactivate")],
        summary=f"Reactivar un registro de {tag.lower()}",
    )
    def reactivate_item(
        item_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: SimpleCatalogService = Depends(get_service),
    ):
        return response_schema.model_validate(
            service.reactivate(item_id, version=body.version, actor=actor)
        )

    return router
