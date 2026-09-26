"""Router de clasificación del producto en categorías (`contracts/rest-api.md` §6.2)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.product import (
    ProductCategoryAssign,
    ProductCategoryDeactivate,
    ProductCategoryResponse,
)
from product_catalog_service.api.security import permission
from product_catalog_service.application.product_category_service import ProductCategoryService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de categorías del producto."""
    router = APIRouter(prefix="/products/{product_id}/categories", tags=["Productos: categorías"])

    def get_service(session: Session = Depends(get_db_session)) -> ProductCategoryService:
        return ProductCategoryService(session)

    def as_list(service: ProductCategoryService, product_id: UUID) -> list[ProductCategoryResponse]:
        return [ProductCategoryResponse.model_validate(item) for item in service.list(product_id)]

    @router.get(
        "",
        response_model=list[ProductCategoryResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar las categorías del producto",
    )
    def list_categories(
        product_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: ProductCategoryService = Depends(get_service),
    ):
        return [
            ProductCategoryResponse.model_validate(item)
            for item in service.list(product_id, status_filter)
        ]

    @router.post(
        "",
        response_model=ProductCategoryResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Asignar una categoría (la primera queda como principal)",
    )
    def assign_category(
        product_id: UUID,
        body: ProductCategoryAssign,
        response: Response,
        actor: CurrentSubject,
        service: ProductCategoryService = Depends(get_service),
    ):
        association, created = service.assign(product_id, body.global_category_id, actor)
        if not created:
            response.status_code = status.HTTP_200_OK
        return ProductCategoryResponse.model_validate(association)

    @router.post(
        "/{association_id}/set-primary",
        response_model=list[ProductCategoryResponse],
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Cambiar la categoría principal",
    )
    def set_primary(
        product_id: UUID,
        association_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: ProductCategoryService = Depends(get_service),
    ):
        service.set_primary(product_id, association_id, body.version, actor)
        return as_list(service, product_id)

    @router.post(
        "/{association_id}/deactivate",
        response_model=ProductCategoryResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Retirar una categoría del producto",
    )
    def deactivate_category(
        product_id: UUID,
        association_id: UUID,
        body: ProductCategoryDeactivate,
        actor: CurrentSubject,
        service: ProductCategoryService = Depends(get_service),
    ):
        return ProductCategoryResponse.model_validate(
            service.deactivate(
                product_id,
                association_id,
                body.version,
                actor,
                body.new_primary_association_id,
            )
        )

    return router
