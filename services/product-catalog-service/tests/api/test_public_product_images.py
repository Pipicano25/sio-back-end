"""Ruta pública exacta de imágenes (spec 022, FR-022-90 a FR-022-98, historia 2; T050, CP-21 a CP-30).

`GET /api/v1/public/product-images?ref=<ref>` sin token: solo una imagen `ACTIVE` y apta identificada por una
referencia firmada; cualquier falla responde el mismo `404`.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.domain.image_ref import sign_ref
from product_catalog_service.main import create_app
from tests import factories
from tests.api.test_asset_content_api import FakeAssetStorage
from tests.conftest import ApiClient
from tests.spec022_support import BUCKET, IMAGE_SECRET, image_asset, sha_of, spec022_settings

PATH = "/api/v1/public/product-images"
OLD_SECRET = "previous-image-ref-secret-0123456789abcdef"
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 300
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg" * 100


def _key(content: bytes, ext: str = "png") -> str:
    return f"assets/{sha_of(content)}.{ext}"


@pytest.fixture
def storage() -> FakeAssetStorage:
    fake = FakeAssetStorage()
    fake.put(_key(PNG), PNG, content_type="image/png", metadata={"sha256": sha_of(PNG)})
    return fake


def _app(test_database_url, test_auth, fake_manufacturer_directory, storage, **overrides):
    return create_app(
        spec022_settings(test_database_url, **overrides),
        auth=test_auth,
        manufacturer_directory_factory=lambda request: fake_manufacturer_directory,
        asset_storage=storage,
    )


@pytest.fixture
def client(test_database_url, clean_database, test_auth, fake_manufacturer_directory, storage):
    with TestClient(_app(test_database_url, test_auth, fake_manufacturer_directory, storage), follow_redirects=False) as c:
        yield c


@pytest.fixture
def product(session_factory):
    return factories.product(session_factory, factories.unit(session_factory).id, "Crema dental")


def _asset(session_factory, product, content=PNG, **kwargs):
    return image_asset(session_factory, product.id, content=content,
                       storage_uri=kwargs.pop("storage_uri", f"s3://{BUCKET}/{_key(content)}"), **kwargs)


def _ref(asset, content=PNG, secret=IMAGE_SECRET) -> str:
    return sign_ref(asset.id, sha_of(content), secret)


def _image_url(client, make_token, product) -> str:
    reader = ApiClient(client, make_token("perm:product-catalog:products:read"))
    item = reader.post("/api/v1/products/summaries/batch-lookup", json={"ids": [str(product.id)]}).json()["items"][0]
    return item["image_url"]


def _not_found(response) -> None:
    assert response.status_code == 404
    assert response.content == b""
    assert "location" not in response.headers


def test_image_url_works_without_token_with_cache_headers(client, make_token, session_factory, product, storage) -> None:
    """CP-21: `<img src={image_url}>` sin token."""
    _asset(session_factory, product)
    url = urlparse(_image_url(client, make_token, product))

    response = client.get(f"{url.path}?{url.query}")

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-length"] == str(len(PNG))
    assert response.headers["etag"] == f'"{sha_of(PNG)}"'
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == 'inline; filename="frente.png"'
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"
    for internal in (BUCKET, "assets/", "s3://", str(product.id)):
        assert internal not in str(response.headers)


def test_if_none_match_gives_304_without_reading_storage(client, session_factory, product, storage) -> None:
    """CP-22 y RNF-022-6: el `304` no lee el objeto (ni sus metadatos)."""
    asset = _asset(session_factory, product)
    storage.calls.clear()

    response = client.get(PATH, params={"ref": _ref(asset)}, headers={"If-None-Match": f'"{sha_of(PNG)}"'})

    assert response.status_code == 304
    assert response.content == b""
    assert response.headers["etag"] == f'"{sha_of(PNG)}"'
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert storage.calls == []


def test_new_content_gives_new_url_and_old_one_stops_when_inactive(client, make_token, session_factory, product, storage) -> None:
    """CP-23: otra imagen principal → otra URL; la anterior deja de servir si su activo se inactiva."""
    old = _asset(session_factory, product)
    old_url = _image_url(client, make_token, product)
    storage.put(_key(JPEG, "jpg"), JPEG, content_type="image/jpeg", metadata={"sha256": sha_of(JPEG)})
    with session_factory() as session:
        stored = session.get(factories.models.ProductAssetModel, old.id)
        stored.is_primary = False
        stored.status = "INACTIVE"
        session.commit()
    _asset(session_factory, product, content=JPEG, mime="image/jpeg",
           storage_uri=f"s3://{BUCKET}/{_key(JPEG, 'jpg')}", file_name="nueva.jpg")

    new_url = _image_url(client, make_token, product)

    assert new_url != old_url
    new = urlparse(new_url)
    assert client.get(f"{new.path}?{new.query}").content == JPEG
    old_parts = urlparse(old_url)
    _not_found(client.get(f"{old_parts.path}?{old_parts.query}"))


def test_every_invalid_reference_gets_the_same_404(client, session_factory, product, storage) -> None:
    """CP-24 a CP-27: alterada, de otro tipo, inactiva, ausente, con parámetros extra o desconocida."""
    asset = _asset(session_factory, product)
    good = _ref(asset)
    sheet_content = b"%PDF-1.7 ficha"
    storage.put(_key(sheet_content, "pdf"), sheet_content, content_type="application/pdf")
    sheet = image_asset(session_factory, product.id, content=sheet_content, mime="application/pdf",
                        asset_type="TECHNICAL_SHEET", storage_uri=f"s3://{BUCKET}/{_key(sheet_content, 'pdf')}")
    inactive_content = b"\x89PNG\r\n\x1a\ninactiva"
    storage.put(_key(inactive_content), inactive_content, content_type="image/png")
    inactive = _asset(session_factory, product, content=inactive_content, status="INACTIVE", is_primary=False)

    altered = good[:-1] + ("A" if good[-1] != "A" else "B")
    responses = [
        client.get(PATH, params={"ref": altered}),
        client.get(PATH, params={"ref": _ref(sheet, sheet_content)}),
        client.get(PATH, params={"ref": _ref(inactive, inactive_content)}),
        client.get(PATH),
        client.get(PATH, params={"ref": good, "extra": "1"}),
        client.get(f"{PATH}?ref={good}&ref={good}"),
        client.get(PATH, params={"ref": "no-es-una-referencia"}),
        client.get(PATH, params={"ref": sign_ref(asset.id, sha_of(b"otro contenido"), IMAGE_SECRET)}),
        client.get(PATH, params={"ref": _ref(asset, secret="secreto-desconocido-0123456789abcdefgh")}),
    ]
    for response in responses:
        _not_found(response)
    assert len({(r.status_code, r.content, r.headers.get("content-type")) for r in responses}) == 1


def test_object_whose_first_bytes_do_not_match_is_404(client, session_factory, product, storage) -> None:
    """CP-29: contenido declarado PNG que en realidad es HTML."""
    html = b"<html><script>alert(1)</script></html>"
    storage.put(_key(html), html, content_type="image/png", metadata={"sha256": sha_of(html)})
    asset = _asset(session_factory, product, content=html)
    _not_found(client.get(PATH, params={"ref": _ref(asset, html)}))


def test_svg_and_external_assets_are_never_served(client, session_factory, product, storage) -> None:
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>"
    storage.put(_key(svg, "svg"), svg, content_type="image/svg+xml")
    asset = _asset(session_factory, product, content=svg, mime="image/svg+xml", storage_uri=f"s3://{BUCKET}/{_key(svg, 'svg')}")
    _not_found(client.get(PATH, params={"ref": _ref(asset, svg)}))
    external = image_asset(session_factory, product.id, content=b"x", storage_uri="https://cdn.example.com/a.png",
                           is_primary=False)
    _not_found(client.get(PATH, params={"ref": sign_ref(external.id, sha_of(b"x"), IMAGE_SECRET)}))


def test_missing_object_is_404(client, session_factory, product) -> None:
    content = b"\x89PNG\r\n\x1a\nno-subida"
    asset = _asset(session_factory, product, content=content)
    _not_found(client.get(PATH, params={"ref": _ref(asset, content)}))


def test_secret_rotation(test_database_url, clean_database, test_auth, fake_manufacturer_directory, storage,
                         session_factory, product) -> None:
    """CP-30: con el secreto anterior configurado, las URL viejas siguen sirviendo; al retirarlo, dejan de servir."""
    asset = _asset(session_factory, product)
    old_ref = _ref(asset, secret=OLD_SECRET)
    rotating = _app(test_database_url, test_auth, fake_manufacturer_directory, storage, image_ref_secret_previous=OLD_SECRET)
    with TestClient(rotating) as client:
        assert client.get(PATH, params={"ref": old_ref}).status_code == 200
    with TestClient(_app(test_database_url, test_auth, fake_manufacturer_directory, storage)) as client:
        _not_found(client.get(PATH, params={"ref": old_ref}))


def test_only_the_exact_path_is_public(client, session_factory, product) -> None:
    """Sin listado ni búsqueda: cualquier otra ruta bajo `/public/` exige token."""
    asset = _asset(session_factory, product)
    for path in (f"{PATH}/", f"{PATH}/{asset.id}", "/api/v1/public/product-images-list", "/api/v1/public"):
        assert client.get(path).status_code == 401, path
    assert client.post(PATH, params={"ref": _ref(asset)}).status_code in (401, 405)


def test_route_does_not_exist_without_secret(test_database_url, clean_database, test_auth, fake_manufacturer_directory,
                                            storage, session_factory, product) -> None:
    """FR-022-99: sin `PRODUCT_IMAGE_REF_SECRET` no hay ruta pública (exige token como cualquier ruta)."""
    asset = _asset(session_factory, product)
    app = _app(test_database_url, test_auth, fake_manufacturer_directory, storage, image_ref_secret=None)
    with TestClient(app) as client:
        assert client.get(PATH, params={"ref": _ref(asset)}).status_code == 401


def test_query_parameters_of_image_url_are_only_ref(client, make_token, session_factory, product) -> None:
    _asset(session_factory, product)
    assert set(parse_qs(urlparse(_image_url(client, make_token, product)).query)) == {"ref"}
