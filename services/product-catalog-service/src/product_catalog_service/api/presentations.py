"""Router de presentaciones (`contracts/rest-api.md` §6.4).

T088 creó el archivo con `batch-lookup`; T119 agrega el resto de las rutas.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.product_views import presentation_view
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.catalog_query import (
    BatchLookupRequest,
    PresentationLookupResponse,
)
from product_catalog_service.api.schemas.dependents import PresentationResponse
from product_catalog_service.api.schemas.presentation import PresentationCreate, PresentationUpdate
from product_catalog_service.api.security import permission
from product_catalog_service.application.catalog_query_service import CatalogQueryService
from product_catalog_service.application.completeness_service import CompletenessService
from product_catalog_service.application.presentation_service import PresentationService
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.infrastructure.models import GlobalProductModel

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de presentaciones."""
    router = APIRouter(tags=["Productos: presentaciones"])

    def get_service(session: Session = Depends(get_db_session)) -> PresentationService:
        return PresentationService(session)

    def views(session: Session, presentations) -> list[PresentationResponse]:
        product_ids = list({item.global_product_id for item in presentations})
        completeness = CompletenessService(session).for_products(product_ids)
        products = {
            product_id: session.get(GlobalProductModel, product_id) for product_id in product_ids
        }
        return [
            presentation_view(item, products[item.global_product_id].status, completeness[item.global_product_id])
            for item in presentations
        ]

    @router.post(
        "/presentations/batch-lookup",
        response_model=PresentationLookupResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar hasta 100 presentaciones por identificador",
    )
    def batch_lookup(body: BatchLookupRequest, session: Session = Depends(get_db_session)):
        return PresentationLookupResponse(items=CatalogQueryService(session).lookup_presentations(body.ids))

    @router.get(
        "/products/{product_id}/presentations",
        response_model=list[PresentationResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar las presentaciones del producto",
    )
    def list_presentations(
        product_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        session: Session = Depends(get_db_session),
    ):
        return views(session, PresentationService(session).list(product_id, status_filter))

    @router.get(
        "/presentations/{presentation_id}",
        response_model=PresentationResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar una presentación",
    )
    def get_presentation(presentation_id: UUID, session: Session = Depends(get_db_session)):
        return views(session, [PresentationService(session).get(presentation_id)])[0]

    @router.post(
        "/products/{product_id}/presentations",
        response_model=PresentationResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Crear una presentación",
    )
    def create_presentation(
        product_id: UUID,
        body: PresentationCreate,
        response: Response,
        actor: CurrentSubject,
        session: Session = Depends(get_db_session),
    ):
        presentation = PresentationService(session).create(product_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/presentations/{presentation.id}"
        return views(session, [presentation])[0]

    @router.put(
        "/presentations/{presentation_id}",
        response_model=PresentationResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar una presentación",
    )
    def update_presentation(
        presentation_id: UUID,
        body: PresentationUpdate,
        actor: CurrentSubject,
        session: Session = Depends(get_db_session),
    ):
        presentation = PresentationService(session).update(presentation_id, actor=actor, **body.model_dump())
        return views(session, [presentation])[0]

    @router.post(
        "/presentations/{presentation_id}/deactivate",
        response_model=PresentationResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar una presentación",
    )
    def deactivate_presentation(
        presentation_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        session: Session = Depends(get_db_session),
    ):
        presentation = PresentationService(session).deactivate(presentation_id, version=body.version, actor=actor)
        return views(session, [presentation])[0]

    @router.post(
        "/presentations/{presentation_id}/reactivate",
        response_model=PresentationResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar una presentación",
    )
    def reactivate_presentation(
        presentation_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        session: Session = Depends(get_db_session),
    ):
        presentation = PresentationService(session).reactivate(presentation_id, version=body.version, actor=actor)
        return views(session, [presentation])[0]

    return router
