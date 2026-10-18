"""Ruta pública exacta de imágenes (spec 022, FR-022-90 a FR-022-98; `contracts/product-catalog.md`).

`GET /api/v1/public/product-images?ref=<ref>`, sin token, para `<img src={image_url}>`. Solo existe si
`PRODUCT_IMAGE_REF_SECRET` y `PRODUCT_CATALOG_PUBLIC_BASE_URL` están configurados (FR-022-99).

Orden de validación (FR-022-92): único parámetro `ref` bien formado → firma en tiempo constante (secreto actual
o anterior) → activo `IMAGE` y `ACTIVE`, apto para URL (tipo permitido, almacenamiento de SIO, clave con
SHA-256) y con el mismo prefijo de SHA-256 que la referencia → `If-None-Match` (`304` sin leer el
almacenamiento) → lectura **solo** por la clave registrada → metadatos y primeros bytes coherentes.

Cualquier falla responde el **mismo** `404` vacío (FR-022-93). No hay redirecciones, listado ni búsqueda, y la
respuesta no contiene bucket, clave, `storage_uri`, empresa ni auditoría (FR-022-95). La causa del rechazo solo
va al log, sin la referencia.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from product_catalog_service.api.assets import _matches
from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.domain.image_content import SNIFF_BYTES, matches_declared_type
from product_catalog_service.domain.image_ref import eligible_image_sha, verify_ref
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.infrastructure.models import ProductAssetModel

PUBLIC_IMAGE_PATH = "/api/v1/public/product-images"
PUBLIC_CACHE = "public, max-age=31536000, immutable"

logger = logging.getLogger("product_catalog_service")


def _not_found(cause: str) -> Response:
    logger.info("Imagen pública rechazada causa=%s", cause)
    return Response(status_code=status.HTTP_404_NOT_FOUND, headers={"Cache-Control": "no-store"})


def _filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "imagen")[:120]


def _with_head(head: bytes, rest: Iterator[bytes]) -> Iterator[bytes]:
    if head:
        yield head
    yield from rest


def _read_head(chunks: Iterator[bytes]) -> tuple[bytes, Iterator[bytes]]:
    """Lee trozos hasta tener `SNIFF_BYTES` (sin cargar el objeto completo); devuelve lo leído y el resto del flujo."""
    head = b""
    for chunk in chunks:
        head += chunk
        if len(head) >= SNIFF_BYTES:
            break
    return head, chunks


def build_router() -> APIRouter:
    """Router de la ruta pública. No declara permiso: se publica por ruta exacta en `sio-auth`."""
    router = APIRouter(tags=["Imágenes públicas"])

    @router.get(
        PUBLIC_IMAGE_PATH,
        summary="Imagen de un producto por referencia firmada, sin token (spec 022)",
        description=(
            "Entrega **una** imagen `ACTIVE` y apta (JPEG, PNG o WebP) identificada por `ref`, para usar en "
            "`<img src>`. Cualquier referencia inválida, alterada, de otro tipo de activo o inactiva responde el "
            "mismo `404`. Caché pública inmutable con `ETag`; `If-None-Match` coincidente → `304`."
        ),
        response_class=StreamingResponse,
        responses={
            200: {"description": "Contenido de la imagen", "content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}},
            304: {"description": "No modificada"},
            404: {"description": "Referencia no válida (sin detalle)"},
            503: {"description": "Almacenamiento no disponible"},
        },
        include_in_schema=True,
    )
    def public_image(request: Request, session: Session = Depends(get_db_session)):
        settings = request.app.state.settings
        params = request.query_params.multi_items()
        if len(params) != 1 or params[0][0] != "ref":
            return _not_found("parametros")

        verified = verify_ref(params[0][1], settings.image_ref_secrets)
        if verified is None:
            return _not_found("firma")
        asset_id, sha_prefix = verified

        asset = session.get(ProductAssetModel, asset_id)
        sha = eligible_image_sha(asset, settings.asset_storage_bucket, require_primary=False) if asset is not None else None
        if sha is None or not sha.startswith(sha_prefix):
            return _not_found("activo")

        etag = f'"{sha}"'
        cache = {"ETag": etag, "Cache-Control": PUBLIC_CACHE, "X-Content-Type-Options": "nosniff",
                 "Cross-Origin-Resource-Policy": "cross-origin"}
        if _matches(request.headers.get("if-none-match"), etag):
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=cache)

        storage = request.app.state.asset_storage
        if storage is None:
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, headers={"Cache-Control": "no-store"})
        key = asset.storage_uri.split("/", 3)[3]
        try:
            found = storage.get(key)
        except AssetStorageUnavailableError:
            logger.warning("Almacenamiento de objetos no disponible para la imagen pública")
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, headers={"Cache-Control": "no-store"})
        if found is None:
            return _not_found("objeto")

        info, chunks = found
        stored_sha = info.metadata.get("sha256")
        if stored_sha is not None and stored_sha != sha:
            return _not_found("sha")
        head, rest = _read_head(chunks)
        if not matches_declared_type(head, asset.mime_type):
            return _not_found("contenido")

        headers = {
            **cache,
            "Content-Length": str(info.size),
            "Content-Disposition": f'inline; filename="{_filename(asset.file_name)}"',
        }
        return StreamingResponse(_with_head(head, rest), media_type=asset.mime_type, headers=headers)

    return router

