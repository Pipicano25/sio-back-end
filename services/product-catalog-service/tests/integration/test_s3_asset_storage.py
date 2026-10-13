"""Adaptador S3 (MinIO real): lectura en streaming, metadatos, inexistentes y caída.

Requiere un almacenamiento levantado y estas variables (se omite si faltan):
  ASSET_STORAGE_ENDPOINT, ASSET_STORAGE_BUCKET,
  ASSET_STORAGE_ACCESS_KEY / ASSET_STORAGE_SECRET_KEY            (cuenta de solo lectura de Product Catalog)
  ASSET_STORAGE_WRITER_ACCESS_KEY / ASSET_STORAGE_WRITER_SECRET_KEY (cuenta de escritura, para preparar el objeto)
"""

from __future__ import annotations

import hashlib
import os
import secrets

import pytest

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.infrastructure.s3_asset_storage import S3AssetStorage

pytestmark = pytest.mark.integration
REQUIRED = ("ASSET_STORAGE_ENDPOINT", "ASSET_STORAGE_ACCESS_KEY", "ASSET_STORAGE_SECRET_KEY",
            "ASSET_STORAGE_WRITER_ACCESS_KEY", "ASSET_STORAGE_WRITER_SECRET_KEY")


def _storage(access: str, secret: str, endpoint: str | None = None) -> S3AssetStorage:
    return S3AssetStorage(endpoint=endpoint or os.environ["ASSET_STORAGE_ENDPOINT"],
                          bucket=os.environ.get("ASSET_STORAGE_BUCKET", "sio-product-assets"),
                          access_key=access, secret_key=secret, region="us-east-1", timeout_seconds=3)


@pytest.fixture(scope="module")
def stores():
    if any(not os.environ.get(name) for name in REQUIRED):
        pytest.skip("Almacenamiento de objetos no configurado para integración")
    return (_storage(os.environ["ASSET_STORAGE_ACCESS_KEY"], os.environ["ASSET_STORAGE_SECRET_KEY"]),
            _storage(os.environ["ASSET_STORAGE_WRITER_ACCESS_KEY"], os.environ["ASSET_STORAGE_WRITER_SECRET_KEY"]))


def test_put_head_get_stream_and_idempotent_key(stores) -> None:
    reader, writer = stores
    data = secrets.token_bytes(200_000)
    digest = hashlib.sha256(data).hexdigest()
    key = f"assets/{digest}.png"

    writer.put(key, data, content_type="image/png", metadata={"sha256": digest})
    writer.put(key, data, content_type="image/png", metadata={"sha256": digest})  # misma clave: no duplica

    info = reader.head(key)
    assert info is not None and info.size == len(data) and info.content_type == "image/png"
    assert info.metadata["sha256"] == digest
    found = reader.get(key)
    assert found is not None
    meta, chunks = found
    parts = list(chunks)
    assert b"".join(parts) == data and len(parts) > 1  # streaming por trozos
    assert reader.exists(key) and not reader.exists(f"assets/{'0' * 64}.png")
    assert reader.get(f"assets/{'0' * 64}.png") is None


def test_reader_cannot_write(stores) -> None:
    reader, _ = stores
    with pytest.raises(AssetStorageUnavailableError):
        reader.put("assets/no-permitido.png", b"x", content_type="image/png")


def test_unreachable_storage_raises_unavailable() -> None:
    dead = _storage("x", "y", endpoint="http://127.0.0.1:1")
    with pytest.raises(AssetStorageUnavailableError):
        dead.head("assets/a.png")
