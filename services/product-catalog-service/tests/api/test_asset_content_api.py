"""GET /products/{id}/assets/{asset_id}/content: entrega del contenido por la API (streaming).

El frontend solo conoce SIO: Product Catalog lee el objeto del almacenamiento S3 (MinIO) y lo
entrega con Content-Type, Content-Length, ETag y Cache-Control; nunca expone bucket, clave ni
credenciales.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.application.exceptions import AssetStorageUnavailableError
from product_catalog_service.application.ports import StoredObject
from product_catalog_service.config import Settings
from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient

BUCKET = "sio-product-assets"
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 600  # ~150 KB: varios trozos
SHA = hashlib.sha256(PNG).hexdigest()
KEY = f"assets/{SHA}.png"


class FakeAssetStorage:
    def __init__(self) -> None:
        self.bucket = BUCKET
        self.objects: dict[str, tuple[bytes, str, dict[str, str]]] = {}
        self.unavailable = False
        self.calls: list[str] = []

    def _info(self, key: str) -> StoredObject:
        data, content_type, metadata = self.objects[key]
        return StoredObject(key=key, size=len(data), content_type=content_type, etag="s3-etag", metadata=metadata)

    def head(self, key: str) -> StoredObject | None:
        self.calls.append("head")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        return self._info(key) if key in self.objects else None

    def exists(self, key: str) -> bool:
        return self.head(key) is not None

    def get(self, key: str):
        self.calls.append("get")
        if self.unavailable:
            raise AssetStorageUnavailableError("caído")
        if key not in self.objects:
            return None
        data = self.objects[key][0]

        def chunks() -> Iterator[bytes]:
            for start in range(0, len(data), 65536):
                yield data[start:start + 65536]

        return self._info(key), chunks()

    def put(self, key, data, *, content_type, metadata=None):
        self.objects[key] = (data, content_type, metadata or {})
        return self._info(key)


@pytest.fixture
def storage() -> FakeAssetStorage:
    fake = FakeAssetStorage()
    fake.put(KEY, PNG, content_type="image/png", metadata={"sha256": SHA})
    return fake


def _settings(test_database_url: str) -> Settings:
    return Settings(docs_enabled=True, database_url=test_database_url, party_identity_service_base_url="http://pi.test",
                    party_identity_timeout_seconds=1.0)


@pytest.fixture
def client(test_database_url, clean_database, test_auth, fake_manufacturer_directory, storage):
    app = create_app(_settings(test_database_url), auth=test_auth, manufacturer_directory_factory=lambda r: fake_manufacturer_directory,
                     asset_storage=storage)
    with TestClient(app) as test_client:
        yield test_client


def _as(client, make_token, *permissions) -> ApiClient:
    return ApiClient(client, make_token(*permissions) if permissions else None)


def _asset(client, make_token, session_factory, storage_uri=f"s3://{BUCKET}/{KEY}", mime="image/png", unit_code="UND"):
    unit = factories.unit(session_factory, unit_code)
    product = factories.product(session_factory, unit.id)
    admin = _as(client, make_token, "perm:product-catalog:all:all")
    asset = admin.post(f"/api/v1/products/{product.id}/assets", json={
        "asset_type": "IMAGE", "file_name": "BOX-20__frente.png", "storage_uri": storage_uri, "mime_type": mime, "is_primary": True}).json()
    return product, asset, admin


def _url(product, asset) -> str:
    return f"/api/v1/products/{product.id}/assets/{asset['id']}/content"


def test_streams_content_with_headers(client, make_token, session_factory, storage) -> None:
    product, asset, _ = _asset(client, make_token, session_factory)
    reader = _as(client, make_token, "perm:product-catalog:products:read")

    response = reader.get(_url(product, asset))

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-length"] == str(len(PNG))
    assert response.headers["etag"] == f'"{SHA}"'
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert response.headers["x-content-type-options"] == "nosniff"
    for secret in (BUCKET, KEY, "s3://"):
        assert secret not in str(response.headers)


def test_if_none_match_returns_304_without_body(client, make_token, session_factory, storage) -> None:
    product, asset, admin = _asset(client, make_token, session_factory)
    storage.calls.clear()

    response = admin.get(_url(product, asset), headers={"If-None-Match": f'"{SHA}"'})

    assert response.status_code == 304 and response.content == b""
    assert response.headers["etag"] == f'"{SHA}"'
    assert storage.calls == ["head"]  # no se descarga el contenido
    assert admin.get(_url(product, asset), headers={"If-None-Match": '"otro"'}).status_code == 200


def test_requires_token_and_permission(client, make_token, session_factory) -> None:
    product, asset, _ = _asset(client, make_token, session_factory)

    assert _as(client, make_token).get(_url(product, asset)).status_code == 401
    assert _as(client, make_token, "perm:product-catalog:brands:read").get(_url(product, asset)).status_code == 403


def test_not_found_cases(client, make_token, session_factory, storage) -> None:
    product, asset, admin = _asset(client, make_token, session_factory)
    other, other_asset, _ = _asset(client, make_token, session_factory, unit_code="KG")

    assert admin.get(f"/api/v1/products/{product.id}/assets/{other_asset['id']}/content").status_code == 404
    assert admin.get(f"/api/v1/products/00000000-0000-0000-0000-000000000000/assets/{asset['id']}/content").status_code == 404
    storage.objects.clear()
    missing = admin.get(_url(product, asset))
    assert missing.status_code == 404
    admin.post(f"/api/v1/products/{product.id}/assets/{asset['id']}/deactivate", json={"version": asset["version"]})
    assert admin.get(_url(product, asset)).status_code == 404


def test_storage_unavailable_is_503(client, make_token, session_factory, storage) -> None:
    product, asset, admin = _asset(client, make_token, session_factory)
    storage.unavailable = True

    response = admin.get(_url(product, asset))

    assert response.status_code == 503
    assert response.json()["code"] == "PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE"
    assert response.json()["dependency"] == "asset-storage"


def test_storage_not_configured_is_503(test_database_url, clean_database, test_auth, fake_manufacturer_directory, make_token, session_factory) -> None:
    app = create_app(_settings(test_database_url), auth=test_auth, manufacturer_directory_factory=lambda r: fake_manufacturer_directory)
    assert app.state.asset_storage is None
    with TestClient(app) as test_client:
        product, asset, admin = _asset(test_client, make_token, session_factory)
        assert admin.get(_url(product, asset)).status_code == 503


def test_historic_external_assets_stay_valid_but_content_is_not_served(client, make_token, session_factory) -> None:
    product, asset, admin = _asset(client, make_token, session_factory, storage_uri="https://cdn.example.com/frente.png")

    assert admin.get(f"/api/v1/products/{product.id}/assets").json()[0]["storage_uri"] == "https://cdn.example.com/frente.png"
    response = admin.get(_url(product, asset))
    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.ASSET_CONTENT_NOT_STORED"


def test_object_in_other_bucket_is_not_served(client, make_token, session_factory) -> None:
    product, asset, admin = _asset(client, make_token, session_factory, storage_uri=f"s3://otro-bucket/{KEY}")
    assert admin.get(_url(product, asset)).status_code == 409
