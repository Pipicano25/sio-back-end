"""Router de productos (`contracts/rest-api.md` §6.1)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.dependencies import get_manufacturer_directory
from product_catalog_service.api.pagination import PaginationParams
from product_catalog_service.api.product_views import presentation_view, product_view
from product_catalog_service.api.schemas.attribute import ApplicableAttributeResponse
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.catalog_query import (
    BatchLookupRequest,
    IdentifierLookupResponse,
    ProductLookupResponse,
)
from product_catalog_service.api.schemas.dependents import IdentifierResponse
from product_catalog_service.api.schemas.pagination import PaginatedResponse
from product_catalog_service.api.schemas.product import (
    CompletenessResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from product_catalog_service.api.security import permission
from product_catalog_service.application.catalog_query_service import CatalogQueryService
from product_catalog_service.application.category_attribute_service import CategoryAttributeService
from product_catalog_service.application.completeness_service import CompletenessService
from product_catalog_service.application.ports import ManufacturerDirectory
from product_catalog_service.application.product_service import ProductService
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.infrastructure.product_query_repository import ProductSearchFilters

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de productos."""
    router = APIRouter(prefix="/products", tags=["Productos"])

    def get_service(
        session: Session = Depends(get_db_session),
        directory: ManufacturerDirectory = Depends(get_manufacturer_directory),
    ) -> ProductService:
        return ProductService(session, directory)

    def get_completeness(session: Session = Depends(get_db_session)) -> CompletenessService:
        return CompletenessService(session)

    def get_queries(session: Session = Depends(get_db_session)) -> CatalogQueryService:
        return CatalogQueryService(session)

    def respond(product, completeness_service: CompletenessService, warnings=()) -> ProductResponse:
        return product_view(product, completeness_service.for_product(product.id), warnings=warnings)

    @router.get(
        "",
        response_model=PaginatedResponse[ProductResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar y buscar productos",
    )
    def list_products(
        pagination: PaginationParams = Depends(),
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        search: str | None = Query(default=None, max_length=200),
        category_id: UUID | None = Query(default=None),
        include_descendants: bool = Query(default=False),
        brand_id: UUID | None = Query(default=None),
        manufacturer_organization_id: UUID | None = Query(default=None),
        group_id: UUID | None = Query(default=None),
        identifier: str | None = Query(default=None, max_length=120),
        attribute_filters: list[str] = Query(
            default=[],
            description="Filtros `CODIGO:valor` sobre atributos filtrables; repetible.",
        ),
        queries: CatalogQueryService = Depends(get_queries),
    ):
        filters = ProductSearchFilters(
            status=status_filter,
            search=search,
            category_id=category_id,
            include_descendants=include_descendants,
            brand_id=brand_id,
            manufacturer_organization_id=manufacturer_organization_id,
            group_id=group_id,
            identifier=identifier,
        )
        result = queries.search(
            filters,
            attribute_filters,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        completeness = queries.completeness.for_products([item.id for item in result.items])
        return PaginatedResponse.from_page(result, lambda item: product_view(item, completeness[item.id]))

    @router.post(
        "/batch-lookup",
        response_model=ProductLookupResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar hasta 100 productos por identificador",
    )
    def batch_lookup(body: BatchLookupRequest, queries: CatalogQueryService = Depends(get_queries)):
        return ProductLookupResponse(items=queries.lookup_products(body.ids))

    @router.get(
        "/by-identifier/{value}",
        response_model=IdentifierLookupResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Buscar producto y presentación por código escaneado",
    )
    def by_identifier(value: str, queries: CatalogQueryService = Depends(get_queries)):
        found = queries.by_identifier(value)
        completeness = queries.completeness.for_product(found.product.id)
        return IdentifierLookupResponse(
            product=product_view(found.product, completeness),
            presentation=(
                presentation_view(found.presentation, found.product.status, completeness)
                if found.presentation is not None
                else None
            ),
            identifier=IdentifierResponse.model_validate(found.identifier),
            is_current=found.is_current,
        )

    @router.get(
        "/{product_id}",
        response_model=ProductResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar un producto",
    )
    def get_product(
        product_id: UUID,
        request: Request,
        expand: Literal["detail"] | None = Query(default=None),
        service: ProductService = Depends(get_service),
        queries: CatalogQueryService = Depends(get_queries),
    ):
        product = service.get(product_id)
        return product_view(
            product,
            queries.completeness.for_product(product.id),
            queries=queries,
            expand_detail=expand == "detail",
            # Spec 024 (FR-024-32): en la entrega 2 las imágenes se consultan solo por presentación.
            include_images=not request.app.state.settings.image_migration_completed,
        )

    @router.get(
        "/{product_id}/applicable-attributes",
        response_model=list[ApplicableAttributeResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Atributos aplicables al producto (sin herencia entre categorías)",
    )
    def applicable_attributes(product_id: UUID, session: Session = Depends(get_db_session)):
        return [
            ApplicableAttributeResponse(
                attribute_definition_id=item.definition.id,
                code=item.definition.code,
                name=item.definition.name,
                data_type=item.definition.data_type,
                unit_of_measure_id=item.definition.unit_of_measure_id,
                is_required=item.is_required,
                is_filterable=item.is_filterable,
                display_order=item.display_order,
                category_ids=item.category_ids,
            )
            for item in CategoryAttributeService(session).applicable_attributes(product_id)
        ]

    @router.get(
        "/{product_id}/completeness",
        response_model=CompletenessResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar la completitud derivada del producto",
    )
    def get_completeness_indicator(
        product_id: UUID,
        completeness_service: CompletenessService = Depends(get_completeness),
    ):
        return CompletenessResponse.from_domain(completeness_service.for_product(product_id))

    @router.post(
        "",
        response_model=ProductResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "create")],
        summary="Crear un producto global",
    )
    def create_product(
        body: ProductCreate,
        response: Response,
        actor: CurrentSubject,
        service: ProductService = Depends(get_service),
        completeness_service: CompletenessService = Depends(get_completeness),
    ):
        result = service.create(actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/products/{result.product.id}"
        return respond(result.product, completeness_service, result.warnings)

    @router.put(
        "/{product_id}",
        response_model=ProductResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar un producto global",
    )
    def update_product(
        product_id: UUID,
        body: ProductUpdate,
        actor: CurrentSubject,
        service: ProductService = Depends(get_service),
        completeness_service: CompletenessService = Depends(get_completeness),
    ):
        result = service.update(product_id, actor=actor, **body.model_dump())
        return respond(result.product, completeness_service, result.warnings)

    @router.post(
        "/{product_id}/deactivate",
        response_model=ProductResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar un producto (sin cascada)",
    )
    def deactivate_product(
        product_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: ProductService = Depends(get_service),
        completeness_service: CompletenessService = Depends(get_completeness),
    ):
        return respond(service.deactivate(product_id, version=body.version, actor=actor), completeness_service)

    @router.post(
        "/{product_id}/reactivate",
        response_model=ProductResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar un producto",
    )
    def reactivate_product(
        product_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: ProductService = Depends(get_service),
        completeness_service: CompletenessService = Depends(get_completeness),
    ):
        return respond(service.reactivate(product_id, version=body.version, actor=actor), completeness_service)

    return router
