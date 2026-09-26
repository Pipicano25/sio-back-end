"""Router de tipos de grupo y grupos (`contracts/rest-api.md` §7)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.pagination import PaginationParams
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupTypeCreate,
    GroupTypeResponse,
    GroupTypeUpdate,
    GroupUpdate,
)
from product_catalog_service.api.schemas.pagination import PaginatedResponse
from product_catalog_service.api.security import permission
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.group_service import GroupService, GroupTypeService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "group-types"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de tipos de grupo y grupos."""
    router = APIRouter(tags=["Grupos"])

    def get_groups(session: Session = Depends(get_db_session)) -> GroupService:
        return GroupService(session)

    @router.get(
        "/group-types/{group_type_id}/groups",
        response_model=PaginatedResponse[GroupResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los grupos de un tipo",
    )
    def list_groups(
        group_type_id: UUID,
        pagination: PaginationParams = Depends(),
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        code: str | None = Query(default=None, max_length=100),
        search: str | None = Query(default=None, max_length=200),
        parent_group_id: UUID | None = Query(default=None),
        root_only: bool = Query(default=False),
        service: GroupService = Depends(get_groups),
    ):
        result = service.list(
            group_type_id,
            page=pagination.page,
            page_size=pagination.page_size,
            status=status_filter,
            code=code,
            search=search,
            parent_group_id=parent_group_id,
            root_only=root_only,
        )
        return PaginatedResponse.from_page(result, GroupResponse.model_validate)

    @router.post(
        "/group-types/{group_type_id}/groups",
        response_model=GroupResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "create")],
        summary="Crear un grupo dentro del tipo",
    )
    def create_group(
        group_type_id: UUID,
        body: GroupCreate,
        response: Response,
        actor: CurrentSubject,
        service: GroupService = Depends(get_groups),
    ):
        group = service.create(group_type_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/groups/{group.id}"
        return GroupResponse.model_validate(group)

    @router.get(
        "/groups/{group_id}",
        response_model=GroupResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar un grupo",
    )
    def get_group(group_id: UUID, service: GroupService = Depends(get_groups)):
        return GroupResponse.model_validate(service.get(group_id))

    @router.get(
        "/groups/{group_id}/children",
        response_model=list[GroupResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los hijos directos de un grupo",
    )
    def group_children(group_id: UUID, service: GroupService = Depends(get_groups)):
        return [GroupResponse.model_validate(item) for item in service.children(group_id)]

    @router.get(
        "/groups/{group_id}/ancestors",
        response_model=list[GroupResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Ruta de ancestros de un grupo",
    )
    def group_ancestors(group_id: UUID, service: GroupService = Depends(get_groups)):
        return [GroupResponse.model_validate(item) for item in service.ancestors(group_id)]

    @router.put(
        "/groups/{group_id}",
        response_model=GroupResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar un grupo",
    )
    def update_group(
        group_id: UUID,
        body: GroupUpdate,
        actor: CurrentSubject,
        service: GroupService = Depends(get_groups),
    ):
        return GroupResponse.model_validate(service.update(group_id, actor=actor, **body.model_dump()))

    @router.post(
        "/groups/{group_id}/deactivate",
        response_model=GroupResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar un grupo",
    )
    def deactivate_group(
        group_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: GroupService = Depends(get_groups),
    ):
        return GroupResponse.model_validate(service.deactivate(group_id, version=body.version, actor=actor))

    @router.post(
        "/groups/{group_id}/reactivate",
        response_model=GroupResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar un grupo",
    )
    def reactivate_group(
        group_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: GroupService = Depends(get_groups),
    ):
        return GroupResponse.model_validate(service.reactivate(group_id, version=body.version, actor=actor))

    types_router = build_simple_catalog_router(
        auth=auth,
        prefix="/group-types",
        resource=RESOURCE,
        tag="Grupos",
        service_class=GroupTypeService,
        create_schema=GroupTypeCreate,
        update_schema=GroupTypeUpdate,
        response_schema=GroupTypeResponse,
    )
    router.include_router(types_router)
    return router
