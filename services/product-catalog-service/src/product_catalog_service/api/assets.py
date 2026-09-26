"""Router de activos digitales (`contracts/rest-api.md` §6.7)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.asset import AssetCreate, AssetType, AssetUpdate
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.dependents import AssetResponse
from product_catalog_service.api.security import permission
from product_catalog_service.application.asset_service import AssetService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de activos."""
    router = APIRouter(prefix="/products/{product_id}/assets", tags=["Productos: activos"])

    def get_service(session: Session = Depends(get_db_session)) -> AssetService:
        return AssetService(session)

    @router.get(
        "",
        response_model=list[AssetResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los activos del producto",
    )
    def list_assets(
        product_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        asset_type: AssetType | None = Query(default=None),
        service: AssetService = Depends(get_service),
    ):
        return [AssetResponse.model_validate(item) for item in service.list(product_id, status_filter, asset_type)]

    @router.post(
        "",
        response_model=AssetResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Registrar la referencia a un activo externo",
    )
    def create_asset(
        product_id: UUID,
        body: AssetCreate,
        response: Response,
        actor: CurrentSubject,
        service: AssetService = Depends(get_service),
    ):
        asset = service.create(product_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/products/{product_id}/assets/{asset.id}"
        return AssetResponse.model_validate(asset)

    @router.put(
        "/{asset_id}",
        response_model=AssetResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar los metadatos de un activo",
    )
    def update_asset(
        product_id: UUID,
        asset_id: UUID,
        body: AssetUpdate,
        actor: CurrentSubject,
        service: AssetService = Depends(get_service),
    ):
        return AssetResponse.model_validate(service.update(product_id, asset_id, actor=actor, **body.model_dump()))

    @router.post(
        "/{asset_id}/set-primary",
        response_model=AssetResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Marcar el activo como principal de su tipo",
    )
    def set_primary(
        product_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: AssetService = Depends(get_service),
    ):
        return AssetResponse.model_validate(
            service.set_primary(product_id, asset_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{asset_id}/deactivate",
        response_model=AssetResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar un activo (el archivo externo no se borra)",
    )
    def deactivate_asset(
        product_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: AssetService = Depends(get_service),
    ):
        return AssetResponse.model_validate(
            service.deactivate(product_id, asset_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{asset_id}/reactivate",
        response_model=AssetResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar un activo",
    )
    def reactivate_asset(
        product_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: AssetService = Depends(get_service),
    ):
        return AssetResponse.model_validate(
            service.reactivate(product_id, asset_id, version=body.version, actor=actor)
        )

    return router
