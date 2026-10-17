"""Elegibilidad de la imagen principal para URL (spec 022, FR-022-45 a FR-022-47; T027, CP-15 a CP-18)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from product_catalog_service.domain.image_ref import ALLOWED_IMAGE_TYPES, eligible_image_sha

BUCKET = "sio-product-assets"
SHA = hashlib.sha256(b"imagen").hexdigest()


@dataclass
class Asset:
    asset_type: str = "IMAGE"
    status: str = "ACTIVE"
    is_primary: bool = True
    mime_type: str | None = "image/png"
    storage_uri: str = f"s3://{BUCKET}/assets/{SHA}.png"


def test_active_primary_image_in_sio_storage_with_sha_key_is_eligible() -> None:
    assert eligible_image_sha(Asset(), BUCKET) == SHA


@pytest.mark.parametrize("mime", sorted(ALLOWED_IMAGE_TYPES))
def test_allowed_types(mime: str) -> None:
    assert eligible_image_sha(Asset(mime_type=mime), BUCKET) == SHA


@pytest.mark.parametrize(
    "asset",
    [
        Asset(mime_type="image/svg+xml"),
        Asset(mime_type="image/gif"),
        Asset(mime_type=None),
        Asset(status="INACTIVE"),
        Asset(is_primary=False),
        Asset(asset_type="TECHNICAL_SHEET"),
        Asset(storage_uri=f"s3://otro-bucket/assets/{SHA}.png"),
        Asset(storage_uri="https://cdn.example.com/imagen.png"),
        Asset(storage_uri=f"s3://{BUCKET}/assets/sin-sha.png"),
        Asset(storage_uri=f"s3://{BUCKET}/"),
    ],
    ids=["svg", "gif", "sin-tipo", "inactiva", "no-principal", "ficha-tecnica", "otro-bucket", "externa", "sin-sha",
         "sin-clave"],
)
def test_not_eligible(asset: Asset) -> None:
    assert eligible_image_sha(asset, BUCKET) is None
