"""Registro del primer uso (`contracts/first-use.md`, FR-076 a FR-079)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.catalog_query import FirstUseRequest, FirstUseResponse
from product_catalog_service.api.security import permission
from product_catalog_service.application.first_use_service import FirstUseResult, FirstUseService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "first-use"


def _response(result: FirstUseResult) -> FirstUseResponse:
    presentation = result.presentation
    return FirstUseResponse(
        global_product_id=result.product.id,
        product_first_used_at=result.product.first_used_at,
        product_first_use_source=result.product.first_use_source,
        global_product_presentation_id=presentation.id if presentation else None,
        presentation_first_used_at=presentation.first_used_at if presentation else None,
        presentation_first_use_source=presentation.first_use_source if presentation else None,
    )


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de primer uso."""
    router = APIRouter(prefix="/products/{product_id}/first-use", tags=["Primer uso"])

    def get_service(session: Session = Depends(get_db_session)) -> FirstUseService:
        return FirstUseService(session)

    @router.post(
        "",
        response_model=FirstUseResponse,
        dependencies=[permission(auth, RESOURCE, "register")],
        summary="Registrar el primer uso al adoptar (servicios consumidores)",
    )
    def register_adoption(
        product_id: UUID,
        actor: CurrentSubject,
        body: FirstUseRequest | None = None,
        service: FirstUseService = Depends(get_service),
    ):
        presentation_id = body.global_product_presentation_id if body else None
        return _response(service.register_adoption(product_id, presentation_id, actor))

    @router.post(
        "/manual",
        response_model=FirstUseResponse,
        dependencies=[permission(auth, RESOURCE, "register-manual")],
        summary="Registrar manualmente el primer uso (administradores)",
    )
    def register_manual(
        product_id: UUID,
        actor: CurrentSubject,
        body: FirstUseRequest | None = None,
        service: FirstUseService = Depends(get_service),
    ):
        presentation_id = body.global_product_presentation_id if body else None
        return _response(service.register_manual(product_id, presentation_id, actor))

    return router
