"""Router de imágenes por presentación (spec 024, `contracts/product-catalog-presentation-images.md`).

Prefijo `/products/{product_id}/presentations/{presentation_id}/assets`. Permisos `products:*` (DD-024-4).

La carga directa (`POST …/upload`) lee el cuerpo **acotado**: corta con `413` en cuanto lo recibido supera
`ASSET_UPLOAD_MAX_BYTES` más un margen fijo para el formulario. Después analiza el multipart ya en memoria y
exige un único campo `file` (research R3). No quedan copias del archivo fuera del almacenamiento de objetos.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from product_catalog_service.api.assets import RESOURCE, get_asset_storage, stream_asset_content
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.presentation_image import (
    PresentationImageReference,
    PresentationImageResponse,
    PresentationImageUpdate,
)
from product_catalog_service.api.security import permission
from product_catalog_service.application.exceptions import FileTooLargeError, ValidationError
from product_catalog_service.application.image_urls import asset_image_url
from product_catalog_service.application.ports import AssetStorage
from product_catalog_service.application.presentation_image_service import PresentationImageService
from product_catalog_service.config import Settings
from product_catalog_service.domain.image_upload import validate_image
from product_catalog_service.infrastructure.database import get_db_session

MULTIPART_OVERHEAD = 64 * 1024
"""Margen para las cabeceras y delimitadores del formulario por encima del tamaño máximo del archivo."""

BASE_PATH = "/api/v1/products/{product_id}/presentations/{presentation_id}/assets"

UPLOAD_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {
                            "type": "string",
                            "format": "binary",
                            "description": "Imagen JPEG, PNG o WebP (el tipo se toma del contenido real).",
                        }
                    },
                    "additionalProperties": False,
                }
            }
        },
    }
}

_ERRORS = {
    404: {"description": "Producto, presentación o imagen inexistente"},
    409: {"description": "`VERSION_CONFLICT` o `DUPLICATE_ASSET_CONTENT` (con `existing_asset_id`)"},
    422: {"description": "Validación, `PRODUCT_INACTIVE`, `PRESENTATION_INACTIVE` o `PRESENTATION_OF_OTHER_PRODUCT`"},
    503: {"description": "Almacenamiento de objetos o base de datos no disponibles"},
}


def present(settings: Settings, product_id: UUID, asset) -> PresentationImageResponse:
    """Imagen con `content_url` e `image_url`, sin referencia física (FR-024-20)."""
    return PresentationImageResponse.model_validate(
        {
            "id": asset.id,
            "version": asset.version,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
            "created_by": asset.created_by,
            "updated_by": asset.updated_by,
            "status": asset.status,
            "global_product_id": asset.global_product_id,
            "global_product_presentation_id": asset.global_product_presentation_id,
            "file_name": asset.file_name,
            "mime_type": asset.mime_type,
            "is_primary": asset.is_primary,
            "content_url": BASE_PATH.format(product_id=product_id, presentation_id=asset.global_product_presentation_id)
            + f"/{asset.id}/content",
            "image_url": asset_image_url(settings, asset),
        }
    )


async def read_upload(request: Request, max_bytes: int) -> tuple[bytes, str | None]:
    """Contenido y nombre del único campo `file` de un `multipart/form-data`, con lectura acotada (FR-024-10)."""
    limit = max_bytes + MULTIPART_OVERHEAD
    too_large = FileTooLargeError(
        f"El archivo supera el tamaño máximo permitido ({max_bytes} bytes).", extra={"max_bytes": max_bytes}
    )
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise too_large
    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise ValidationError("Envíe la imagen como multipart/form-data en el campo file.", field="file")

    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise too_large

    async def receive() -> dict:
        return {"type": "http.request", "body": bytes(body), "more_body": False}

    try:
        form = await Request(request.scope, receive).form(max_files=2, max_fields=10)
    except Exception as exc:  # multipart mal formado
        raise ValidationError("El formulario multipart no es válido.", field="file") from exc
    try:
        fields = form.multi_items()
        unknown = sorted({name for name, _ in fields if name != "file"})
        if unknown:
            raise ValidationError(f"Campo no permitido: {', '.join(unknown)}. Solo se acepta file.", field=unknown[0])
        files = [value for name, value in fields if name == "file"]
        if len(files) != 1 or not isinstance(files[0], UploadFile):
            raise ValidationError("Envíe exactamente un archivo en el campo file.", field="file")
        upload = files[0]
        content = await upload.read(max_bytes + 1)
        return content, upload.filename
    finally:
        await form.close()


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de imágenes por presentación."""
    router = APIRouter(
        prefix="/products/{product_id}/presentations/{presentation_id}/assets",
        tags=["Productos: imágenes por presentación"],
    )

    def get_service(request: Request, session: Session = Depends(get_db_session)) -> PresentationImageService:
        return PresentationImageService(
            session, bucket=request.app.state.settings.asset_storage_bucket, storage=request.app.state.asset_storage
        )

    def settings_of(request: Request) -> Settings:
        return request.app.state.settings

    @router.get(
        "",
        response_model=list[PresentationImageResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar las imágenes de la presentación",
        description="Por defecto solo las `ACTIVE`; con `status=INACTIVE`, solo las inactivas. Principal primero.",
        responses={404: _ERRORS[404]},
    )
    def list_images(
        product_id: UUID,
        presentation_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        return [present(settings, product_id, item) for item in service.list(product_id, presentation_id, status_filter)]

    @router.post(
        "/upload",
        response_model=PresentationImageResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Cargar una imagen a la presentación (multipart, campo file)",
        description=(
            "Sube una imagen JPEG, PNG o WebP. Product Catalog la guarda en el almacenamiento de SIO y la deja como "
            "**principal** de la presentación. `201` imagen nueva; `200` el mismo contenido estaba `INACTIVE` y se "
            "reactivó (mismo id); `409 DUPLICATE_ASSET_CONTENT` si ya está `ACTIVE`. Límites: "
            "`ASSET_UPLOAD_MAX_BYTES` y `ASSET_UPLOAD_MAX_PIXELS`."
        ),
        openapi_extra=UPLOAD_OPENAPI,
        responses={
            200: {"description": "Mismo contenido `INACTIVE`: reactivado y principal", "model": PresentationImageResponse},
            413: {"description": "`FILE_TOO_LARGE`"},
            415: {"description": "`UNSUPPORTED_MEDIA_TYPE`"},
            **_ERRORS,
        },
    )
    async def upload_image(
        product_id: UUID,
        presentation_id: UUID,
        request: Request,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        content, file_name = await read_upload(request, settings.asset_upload_max_bytes)
        image = await run_in_threadpool(
            validate_image, content, max_bytes=settings.asset_upload_max_bytes, max_pixels=settings.asset_upload_max_pixels
        )
        asset, created = await run_in_threadpool(
            service.upload, product_id, presentation_id, image, file_name=file_name, actor=actor
        )
        body = present(settings, product_id, asset)
        if not created:
            return JSONResponse(status_code=status.HTTP_200_OK, content=body.model_dump(mode="json"))
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=body.model_dump(mode="json"),
            headers={"Location": f"{BASE_PATH.format(product_id=product_id, presentation_id=presentation_id)}/{asset.id}"},
        )

    @router.post(
        "",
        response_model=PresentationImageResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Registrar una imagen ya almacenada en SIO (registro por referencia)",
        description=(
            "Para el loader de migración: `storage_uri` debe ser `s3://<bucket>/assets/<sha256>.<ext>` de un objeto "
            "existente con la metadata `sha256` de su clave. Un duplicado en la presentación, activo o inactivo, "
            "responde `409`."
        ),
        responses=_ERRORS,
    )
    def register_image(
        product_id: UUID,
        presentation_id: UUID,
        body: PresentationImageReference,
        response: Response,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        asset = service.register(product_id, presentation_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"{BASE_PATH.format(product_id=product_id, presentation_id=presentation_id)}/{asset.id}"
        return present(settings, product_id, asset)

    @router.get(
        "/{asset_id}/content",
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Descargar el contenido de una imagen de la presentación (streaming)",
        response_class=StreamingResponse,
        responses={
            200: {"description": "Contenido de la imagen", "content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}},
            304: {"description": "No modificado (If-None-Match coincide con el ETag)"},
            404: {"description": "Imagen de otra presentación, inactiva o sin contenido"},
            503: {"description": "Almacenamiento de objetos no disponible"},
        },
    )
    def image_content(
        product_id: UUID,
        presentation_id: UUID,
        asset_id: UUID,
        service: PresentationImageService = Depends(get_service),
        storage: AssetStorage = Depends(get_asset_storage),
        if_none_match: str | None = Header(default=None),
    ):
        asset, key = service.content_key(product_id, presentation_id, asset_id)
        return stream_asset_content(asset, key, storage, if_none_match)

    @router.put(
        "/{asset_id}",
        response_model=PresentationImageResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Cambiar el nombre de archivo de una imagen (único campo modificable)",
        responses=_ERRORS,
    )
    def rename_image(
        product_id: UUID,
        presentation_id: UUID,
        asset_id: UUID,
        body: PresentationImageUpdate,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        asset = service.rename(product_id, presentation_id, asset_id, version=body.version, file_name=body.file_name,
                               actor=actor)
        return present(settings, product_id, asset)

    @router.post(
        "/{asset_id}/set-primary",
        response_model=PresentationImageResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Marcar la imagen como principal de la presentación",
        responses=_ERRORS,
    )
    def set_primary(
        product_id: UUID,
        presentation_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        asset = service.set_primary(product_id, presentation_id, asset_id, version=body.version, actor=actor)
        return present(settings, product_id, asset)

    @router.post(
        "/{asset_id}/deactivate",
        response_model=PresentationImageResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Eliminar lógicamente una imagen (el objeto no se borra; sucesión del principal)",
        responses=_ERRORS,
    )
    def deactivate_image(
        product_id: UUID,
        presentation_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        asset = service.deactivate(product_id, presentation_id, asset_id, version=body.version, actor=actor)
        return present(settings, product_id, asset)

    @router.post(
        "/{asset_id}/reactivate",
        response_model=PresentationImageResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar una imagen (no la marca como principal)",
        responses=_ERRORS,
    )
    def reactivate_image(
        product_id: UUID,
        presentation_id: UUID,
        asset_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: PresentationImageService = Depends(get_service),
        settings: Settings = Depends(settings_of),
    ):
        asset = service.reactivate(product_id, presentation_id, asset_id, version=body.version, actor=actor)
        return present(settings, product_id, asset)

    return router
