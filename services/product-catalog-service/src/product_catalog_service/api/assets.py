"""Router de activos digitales (`contracts/rest-api.md` §6.7)."""

from uuid import UUID

import re

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.asset import AssetCreate, AssetType, AssetUpdate
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.dependents import AssetResponse
from product_catalog_service.api.security import permission
from product_catalog_service.application.asset_service import AssetService
from product_catalog_service.application.exceptions import (
    AssetStorageUnavailableError,
    DependencyUnavailableError,
    NotFoundError,
)
from product_catalog_service.application.ports import AssetStorage, StoredObject
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"
IMMUTABLE_CACHE = "private, max-age=31536000, immutable"
REVALIDATE_CACHE = "private, no-cache"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def get_asset_storage(request: Request) -> AssetStorage:
    """Almacenamiento de objetos configurado (sustituible en pruebas)."""
    storage = request.app.state.asset_storage
    if storage is None:
        raise DependencyUnavailableError(
            "El almacenamiento de objetos de los activos no está configurado.", extra={"dependency": "asset-storage"}
        )
    return storage


def _etag(info: StoredObject) -> tuple[str | None, bool]:
    """ETag fuerte y si el contenido es inmutable (clave derivada de su SHA-256)."""
    digest = info.metadata.get("sha256")
    if digest and _SHA256.match(digest) and digest in info.key:
        return f'"{digest}"', True
    return (f'"{info.etag}"' if info.etag else None), False


def _matches(if_none_match: str | None, etag: str | None) -> bool:
    if not if_none_match or not etag:
        return False
    candidates = {item.strip().removeprefix("W/") for item in if_none_match.split(",")}
    return "*" in candidates or etag in candidates


def _unavailable(exc: Exception) -> DependencyUnavailableError:
    return DependencyUnavailableError(
        "El almacenamiento de objetos de los activos no está disponible.", extra={"dependency": "asset-storage"}
    )


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

    @router.get(
        "/{asset_id}/content",
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Descargar el contenido del activo (streaming desde el almacenamiento de SIO)",
        response_class=StreamingResponse,
        responses={
            200: {"description": "Contenido del activo", "content": {"image/*": {}, "application/octet-stream": {}}},
            304: {"description": "No modificado (If-None-Match coincide con el ETag)"},
            404: {"description": "Producto, activo o contenido inexistente"},
            409: {"description": "El activo referencia un recurso externo (no almacenado en SIO)"},
            503: {"description": "Almacenamiento de objetos no disponible"},
        },
    )
    def asset_content(
        product_id: UUID,
        asset_id: UUID,
        service: AssetService = Depends(get_service),
        storage: AssetStorage = Depends(get_asset_storage),
        if_none_match: str | None = Header(default=None),
    ):
        asset, key = service.content_key(product_id, asset_id, storage.bucket)
        try:
            if if_none_match:
                info = storage.head(key)
                if info is None:
                    raise NotFoundError(f"El contenido del activo {asset_id} no está en el almacenamiento.")
                etag, immutable = _etag(info)
                if _matches(if_none_match, etag):
                    return Response(status_code=status.HTTP_304_NOT_MODIFIED,
                                    headers={"ETag": etag, "Cache-Control": IMMUTABLE_CACHE if immutable else REVALIDATE_CACHE})
            found = storage.get(key)
        except AssetStorageUnavailableError as exc:
            raise _unavailable(exc) from exc
        if found is None:
            raise NotFoundError(f"El contenido del activo {asset_id} no está en el almacenamiento.")
        info, chunks = found
        etag, immutable = _etag(info)
        headers = {
            "Content-Length": str(info.size),
            "Cache-Control": IMMUTABLE_CACHE if immutable else REVALIDATE_CACHE,
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{re.sub(r"[^A-Za-z0-9._-]", "_", asset.file_name)}"',
        }
        if etag:
            headers["ETag"] = etag
        return StreamingResponse(chunks, media_type=asset.mime_type or info.content_type or "application/octet-stream", headers=headers)

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
