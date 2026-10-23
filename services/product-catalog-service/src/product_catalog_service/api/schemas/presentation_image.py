"""Esquemas de las imágenes por presentación (spec 024, `contracts/product-catalog-presentation-images.md`).

La respuesta nunca incluye `storage_uri`, bucket ni clave del objeto (FR-024-20, FR-024-59).
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from product_catalog_service.api.schemas.base import RequestModel, StatusResourceResponse, UpdateModel

ImageMimeType = Literal["image/jpeg", "image/png", "image/webp"]


class PresentationImageResponse(StatusResourceResponse):
    global_product_id: UUID
    global_product_presentation_id: UUID
    asset_type: Literal["IMAGE"] = "IMAGE"
    file_name: str
    mime_type: str | None
    is_primary: bool
    content_url: str = Field(description="Contenido por la API, con token (`products:read`).")
    image_url: str | None = Field(
        description="URL pública firmada para `<img src>`; `null` si la ruta pública está deshabilitada o la imagen "
        "no está `ACTIVE`."
    )


class PresentationImageReference(RequestModel):
    """Registro por referencia de una imagen **ya almacenada en SIO** (DD-024-6, FR-024-22)."""

    file_name: str = Field(min_length=1, max_length=255)
    storage_uri: str = Field(max_length=4000, description="`s3://<bucket>/assets/<sha256>.<jpg|png|webp>`.")
    mime_type: ImageMimeType
    is_primary: bool = False


class PresentationImageUpdate(UpdateModel):
    """Solo `file_name` es modificable (FR-024-21c, DD-024-8)."""

    immutable_fields = frozenset({
        "storage_uri", "mime_type", "global_product_presentation_id", "global_product_id", "asset_type",
        "status", "is_primary",
    })

    file_name: str = Field(min_length=1, max_length=255)
