"""Ayudas de las pruebas de la spec 022 (PC-1, PC-2 y la ruta pública de imágenes)."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy.orm import sessionmaker

from product_catalog_service.config import Settings
from product_catalog_service.infrastructure import models
from tests import factories

BUCKET = "sio-product-assets"
IMAGE_SECRET = "image-ref-secret-for-tests-0123456789abcdef"
PUBLIC_BASE = "https://catalogo.sio.test"


def spec022_settings(test_database_url: str, **overrides) -> Settings:
    values = dict(
        docs_enabled=True,
        database_url=test_database_url,
        party_identity_service_base_url="http://pi.test",
        party_identity_timeout_seconds=1.0,
        public_base_url=PUBLIC_BASE,
        image_ref_secret=IMAGE_SECRET,
    )
    values.update(overrides)
    return Settings(**values)


def sha_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def image_asset(
    factory: sessionmaker,
    product_id: UUID,
    *,
    content: bytes = b"\x89PNG\r\n\x1a\n" + b"x" * 64,
    mime: str | None = "image/png",
    asset_type: str = "IMAGE",
    status: str = "ACTIVE",
    is_primary: bool = True,
    storage_uri: str | None = None,
    file_name: str = "frente.png",
):
    """Activo registrado directamente (sin pasar por la API de activos)."""
    uri = storage_uri or f"s3://{BUCKET}/assets/{sha_of(content)}.png"
    return factories._save(
        factory,
        models.ProductAssetModel(
            global_product_id=product_id,
            asset_type=asset_type,
            file_name=file_name,
            storage_uri=uri,
            mime_type=mime,
            is_primary=is_primary,
            status=status,
        ),
    )
