"""Router de identificadores del producto (`contracts/rest-api.md` §6.5).

No existe `PUT`: valor, tipo y presentación son inmutables (FR-060).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.dependents import IdentifierResponse
from product_catalog_service.api.schemas.presentation import IdentifierCreate
from product_catalog_service.api.security import permission
from product_catalog_service.application.identifier_service import IdentifierService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de identificadores."""
    router = APIRouter(prefix="/products/{product_id}/identifiers", tags=["Productos: identificadores"])

    def get_service(session: Session = Depends(get_db_session)) -> IdentifierService:
        return IdentifierService(session)

    @router.get(
        "",
        response_model=list[IdentifierResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los identificadores del producto",
    )
    def list_identifiers(
        product_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: IdentifierService = Depends(get_service),
    ):
        return [IdentifierResponse.model_validate(item) for item in service.list(product_id, status_filter)]

    @router.post(
        "",
        response_model=IdentifierResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Registrar un identificador (GTIN, EAN, UPC, BARCODE u OTHER)",
    )
    def create_identifier(
        product_id: UUID,
        body: IdentifierCreate,
        response: Response,
        actor: CurrentSubject,
        service: IdentifierService = Depends(get_service),
    ):
        identifier = service.create(product_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/products/{product_id}/identifiers/{identifier.id}"
        return IdentifierResponse.model_validate(identifier)

    @router.post(
        "/{identifier_id}/set-primary",
        response_model=IdentifierResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Marcar el identificador como principal de su tipo y contexto",
    )
    def set_primary(
        product_id: UUID,
        identifier_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: IdentifierService = Depends(get_service),
    ):
        return IdentifierResponse.model_validate(
            service.set_primary(product_id, identifier_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{identifier_id}/deactivate",
        response_model=IdentifierResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar un identificador (el código no se libera)",
    )
    def deactivate_identifier(
        product_id: UUID,
        identifier_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: IdentifierService = Depends(get_service),
    ):
        return IdentifierResponse.model_validate(
            service.deactivate(product_id, identifier_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{identifier_id}/reactivate",
        response_model=IdentifierResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar un identificador",
    )
    def reactivate_identifier(
        product_id: UUID,
        identifier_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: IdentifierService = Depends(get_service),
    ):
        return IdentifierResponse.model_validate(
            service.reactivate(product_id, identifier_id, version=body.version, actor=actor)
        )

    return router
