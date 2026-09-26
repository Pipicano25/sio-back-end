"""Router de categorías (`contracts/rest-api.md` §4)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.pagination import PaginationParams
from product_catalog_service.api.schemas.attribute import (
    CategoryAttributeCreate,
    CategoryAttributeResponse,
    CategoryAttributeUpdate,
)
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from product_catalog_service.api.schemas.pagination import PaginatedResponse
from product_catalog_service.api.security import permission
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.category_attribute_service import CategoryAttributeService
from product_catalog_service.application.category_service import CategoryService
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.infrastructure.models import GlobalCategoryModel

RESOURCE = "categories"


def _tree_filters(
    parent_category_id: UUID | None = Query(default=None),
    root_only: bool = Query(default=False),
):
    if parent_category_id is None and not root_only:
        return None

    def apply(statement):
        if parent_category_id is not None:
            statement = statement.where(GlobalCategoryModel.parent_category_id == parent_category_id)
        if root_only:
            statement = statement.where(GlobalCategoryModel.parent_category_id.is_(None))
        return statement

    return apply


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de categorías."""
    router = APIRouter(prefix="/categories", tags=["Categorías"])

    def get_service(session: Session = Depends(get_db_session)) -> CategoryService:
        return CategoryService(session)

    @router.get(
        "/{category_id}/children",
        response_model=PaginatedResponse[CategoryResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar las hijas directas de una categoría",
    )
    def list_children(
        category_id: UUID,
        pagination: PaginationParams = Depends(),
        service: CategoryService = Depends(get_service),
    ):
        result = service.children(category_id, page=pagination.page, page_size=pagination.page_size)
        return PaginatedResponse.from_page(result, CategoryResponse.model_validate)

    @router.get(
        "/{category_id}/descendants",
        response_model=PaginatedResponse[CategoryResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los descendientes de una categoría",
    )
    def list_descendants(
        category_id: UUID,
        pagination: PaginationParams = Depends(),
        service: CategoryService = Depends(get_service),
    ):
        result = service.descendants(category_id, page=pagination.page, page_size=pagination.page_size)
        return PaginatedResponse.from_page(result, CategoryResponse.model_validate)

    @router.get(
        "/{category_id}/ancestors",
        response_model=list[CategoryResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Ruta de ancestros de la raíz a la categoría",
    )
    def list_ancestors(category_id: UUID, service: CategoryService = Depends(get_service)):
        return [CategoryResponse.model_validate(item) for item in service.ancestors(category_id)]

    def get_attribute_service(session: Session = Depends(get_db_session)) -> CategoryAttributeService:
        return CategoryAttributeService(session)

    attributes_path = "/{category_id}/attributes"

    @router.get(
        attributes_path,
        response_model=list[CategoryAttributeResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los atributos asociados a la categoría",
    )
    def list_attributes(
        category_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: CategoryAttributeService = Depends(get_attribute_service),
    ):
        return [CategoryAttributeResponse.model_validate(item) for item in service.list(category_id, status_filter)]

    @router.post(
        attributes_path,
        response_model=CategoryAttributeResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Asociar una definición de atributo a la categoría",
    )
    def associate_attribute(
        category_id: UUID,
        body: CategoryAttributeCreate,
        response: Response,
        actor: CurrentSubject,
        service: CategoryAttributeService = Depends(get_attribute_service),
    ):
        association, created = service.associate(category_id, actor=actor, **body.model_dump())
        if not created:
            response.status_code = status.HTTP_200_OK
        return CategoryAttributeResponse.model_validate(association)

    @router.put(
        attributes_path + "/{association_id}",
        response_model=CategoryAttributeResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar obligatoriedad, filtrado u orden",
    )
    def update_attribute(
        category_id: UUID,
        association_id: UUID,
        body: CategoryAttributeUpdate,
        actor: CurrentSubject,
        service: CategoryAttributeService = Depends(get_attribute_service),
    ):
        return CategoryAttributeResponse.model_validate(
            service.update(category_id, association_id, actor=actor, **body.model_dump())
        )

    @router.post(
        attributes_path + "/{association_id}/deactivate",
        response_model=CategoryAttributeResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar la asociación categoría–atributo",
    )
    def deactivate_attribute(
        category_id: UUID,
        association_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: CategoryAttributeService = Depends(get_attribute_service),
    ):
        return CategoryAttributeResponse.model_validate(
            service.deactivate(category_id, association_id, version=body.version, actor=actor)
        )

    @router.post(
        attributes_path + "/{association_id}/reactivate",
        response_model=CategoryAttributeResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar la asociación categoría–atributo",
    )
    def reactivate_attribute(
        category_id: UUID,
        association_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: CategoryAttributeService = Depends(get_attribute_service),
    ):
        return CategoryAttributeResponse.model_validate(
            service.reactivate(category_id, association_id, version=body.version, actor=actor)
        )

    return build_simple_catalog_router(
        auth=auth,
        prefix="/categories",
        resource=RESOURCE,
        tag="Categorías",
        service_class=CategoryService,
        create_schema=CategoryCreate,
        update_schema=CategoryUpdate,
        response_schema=CategoryResponse,
        extra_filters=_tree_filters,
        router=router,
    )
