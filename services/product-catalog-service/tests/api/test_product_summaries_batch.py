"""PC-1: resumen del catálogo por lotes (spec 022, FR-022-82, FR-022-45, FR-022-96; T028, CP-10, CP-11)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.domain.image_ref import verify_ref
from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient
from tests.spec022_support import IMAGE_SECRET, PUBLIC_BASE, image_asset, sha_of, spec022_settings

URL = "/api/v1/products/summaries/batch-lookup"
PUBLIC_PATH = "/api/v1/public/product-images"


@pytest.fixture
def client(test_database_url, clean_database, test_auth, fake_manufacturer_directory):
    app = create_app(
        spec022_settings(test_database_url),
        auth=test_auth,
        manufacturer_directory_factory=lambda request: fake_manufacturer_directory,
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def reader(client, make_token) -> ApiClient:
    return ApiClient(client, make_token("perm:product-catalog:products:read"))


def _lookup(reader, *ids):
    response = reader.post(URL, json={"ids": [str(i) for i in ids]})
    assert response.status_code == 200, response.text
    return {item["id"]: item for item in response.json()["items"]}


def test_summary_fields(reader, session_factory) -> None:
    unit = factories.unit(session_factory, "TAB")
    brand = factories.brand(session_factory, "COLGATE")
    product = factories.product(session_factory, unit.id, "Crema dental 100 ml", brand_id=brand.id)
    primary = factories.category(session_factory, "HIGIENE")
    secondary = factories.category(session_factory, "ORAL")
    retired = factories.category(session_factory, "RETIRADA")
    factories.product_category(session_factory, product.id, primary.id, is_primary=True)
    factories.product_category(session_factory, product.id, secondary.id, is_primary=False)
    factories.product_category(session_factory, product.id, retired.id, is_primary=False, status="INACTIVE")
    presentation = factories.presentation(session_factory, product.id, "CAJA")
    factories.identifier(session_factory, product.id, "7702010000017", presentation_id=presentation.id)
    factories.identifier(session_factory, product.id, "ABCOLD", "OTHER", status="INACTIVE")

    item = _lookup(reader, product.id)[str(product.id)]

    assert item["found"] is True
    assert item["canonical_name"] == "Crema dental 100 ml"
    assert item["product_type"] == "GOOD"
    assert item["status"] == "ACTIVE"
    assert item["brand"] == {"id": str(brand.id), "code": "COLGATE", "name": "Colgate"}
    assert item["base_unit"] == {"id": str(unit.id), "code": "TAB", "name": "Tab"}
    assert {(c["code"], c["is_primary"]) for c in item["categories"]} == {("HIGIENE", True), ("ORAL", False)}
    assert item["identifiers"] == [
        {"type": "GTIN", "value": "7702010000017", "is_primary": False,
         "global_product_presentation_id": str(presentation.id)}
    ]
    assert item["has_image"] is False and item["image_url"] is None


def test_product_without_brand_or_image(reader, session_factory) -> None:
    product = factories.product(session_factory, factories.unit(session_factory).id, "Sin marca")
    item = _lookup(reader, product.id)[str(product.id)]
    assert item["brand"] is None
    assert item["categories"] == [] and item["identifiers"] == []
    assert item["has_image"] is False and item["image_url"] is None


def test_eligible_primary_image_gets_absolute_signed_url(reader, session_factory) -> None:
    product = factories.product(session_factory, factories.unit(session_factory).id, "Con imagen")
    content = b"\x89PNG\r\n\x1a\nimagen"
    asset = image_asset(session_factory, product.id, content=content)

    item = _lookup(reader, product.id)[str(product.id)]

    assert item["has_image"] is True
    url = urlparse(item["image_url"])
    assert f"{url.scheme}://{url.netloc}" == PUBLIC_BASE
    assert url.path == PUBLIC_PATH
    query = parse_qs(url.query)
    assert set(query) == {"ref"}
    assert verify_ref(query["ref"][0], [IMAGE_SECRET]) == (asset.id, sha_of(content)[:16])
    for internal in ("s3://", "sio-product-assets", "assets/"):
        assert internal not in item["image_url"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mime": "image/svg+xml"},
        {"status": "INACTIVE", "is_primary": False},
        {"is_primary": False},
        {"asset_type": "TECHNICAL_SHEET"},
        {"storage_uri": "https://cdn.example.com/a.png"},
        {"storage_uri": "s3://sio-product-assets/assets/sin-sha.png"},
    ],
    ids=["svg", "inactiva", "no-principal", "ficha", "externa", "sin-sha"],
)
def test_ineligible_images_give_no_image(reader, session_factory, kwargs) -> None:
    product = factories.product(session_factory, factories.unit(session_factory).id, "Imagen no apta")
    image_asset(session_factory, product.id, **kwargs)
    item = _lookup(reader, product.id)[str(product.id)]
    assert item["has_image"] is False and item["image_url"] is None


def test_without_secret_has_image_is_computed_but_no_url(test_database_url, clean_database, test_auth,
                                                         fake_manufacturer_directory, make_token, session_factory) -> None:
    """Sin `PRODUCT_IMAGE_REF_SECRET` la ruta pública no existe: no se entrega URL (FR-022-99)."""
    app = create_app(spec022_settings(test_database_url, image_ref_secret=None), auth=test_auth,
                     manufacturer_directory_factory=lambda request: fake_manufacturer_directory)
    product = factories.product(session_factory, factories.unit(session_factory).id, "Con imagen")
    image_asset(session_factory, product.id)
    with TestClient(app) as test_client:
        reader = ApiClient(test_client, make_token("perm:product-catalog:products:read"))
        item = _lookup(reader, product.id)[str(product.id)]
    assert item["has_image"] is True
    assert item["image_url"] is None


def test_not_found_limits_and_permission(reader, client, make_token, session_factory) -> None:
    missing = uuid4()
    absent = _lookup(reader, missing)[str(missing)]
    assert absent["found"] is False and absent["id"] == str(missing)
    assert all(value is None for key, value in absent.items() if key not in {"id", "found"})
    assert reader.post(URL, json={"ids": [str(uuid4()) for _ in range(101)]}).status_code == 422
    assert reader.post(URL, json={"ids": []}).status_code == 422
    assert ApiClient(client, make_token("perm:product-catalog:brands:read")).post(URL, json={"ids": [str(missing)]}).status_code == 403
    assert ApiClient(client, None).post(URL, json={"ids": [str(missing)]}).status_code == 401


def test_constant_number_of_queries(reader, session_factory) -> None:
    """Un lote de 1 o de 30 productos ejecuta las mismas consultas (sin N+1)."""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    unit = factories.unit(session_factory)
    products = [factories.product(session_factory, unit.id, f"Producto {i}") for i in range(30)]
    for product in products:
        image_asset(session_factory, product.id, content=f"imagen {product.id}".encode())

    def count(ids) -> int:
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(Engine, "before_cursor_execute", listener)
        try:
            _lookup(reader, *ids)
        finally:
            event.remove(Engine, "before_cursor_execute", listener)
        return len(statements)

    assert count([products[0].id]) == count([p.id for p in products])
