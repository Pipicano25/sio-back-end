"""URL pública firmada de una imagen (spec 022, FR-022-96; spec 024, FR-024-20 y FR-024-37).

Una sola construcción para PC-1, PC-3 y las rutas por presentación: `null` si la ruta pública está deshabilitada
o si el activo no es una imagen `ACTIVE` apta.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from product_catalog_service.config import Settings
from product_catalog_service.domain.image_ref import eligible_image_sha, sign_ref

PUBLIC_IMAGE_PATH = "/api/v1/public/product-images"


def signed_image_url(settings: Settings, asset_id: UUID, sha256_hex: str) -> str | None:
    """URL pública de una versión de contenido de un activo, o `None` con la ruta pública deshabilitada."""
    if not settings.public_images_enabled:
        return None
    ref = sign_ref(asset_id, sha256_hex, settings.image_ref_secret)
    return f"{settings.public_base_url}{PUBLIC_IMAGE_PATH}?{urlencode({'ref': ref})}"


def asset_image_url(settings: Settings, asset: Any) -> str | None:
    """URL pública de cualquier imagen `ACTIVE` apta (principal o no), o `None`."""
    sha = eligible_image_sha(asset, settings.asset_storage_bucket, require_primary=False)
    return signed_image_url(settings, asset.id, sha) if sha is not None else None
