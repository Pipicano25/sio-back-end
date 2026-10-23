"""Rutas por producto frente a las imágenes en las dos entregas (spec 024, caso 31; FR-024-31 a FR-024-33, FR-024-05).

`transition` (entrega 1): el alta de `IMAGE` → `422`; las modificaciones de imágenes → `409`; las lecturas siguen
e informan la presentación. `completed` (entrega 2): ninguna operación sobre imágenes (`422`) y el listado y el
detalle las excluyen. Los demás tipos de activo no cambian en ninguna etapa.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient
from tests.spec022_support import BUCKET, image_asset, sha_of, spec022_settings
from tests.storage_fakes import FakeAssetStorage

V = "/api/v1"
IMAGE_CONTENT = b"\x89PNG\r\n\x1a\nimagen"


@pytest.fixture(params=["transition", "completed"])
def stage(request) -> str:
    return request.param


@pytest.fixture
def admin(test_database_url, clean_database, test_auth, fake_manufacturer_directory, make_token, stage):
    storage = FakeAssetStorage()
    storage.put(f"assets/{sha_of(IMAGE_CONTENT)}.png", IMAGE_CONTENT, content_type="image/png",
                metadata={"sha256": sha_of(IMAGE_CONTENT)})
    app = create_app(spec022_settings(test_database_url, image_migration_stage=stage), auth=test_auth,
                     manufacturer_directory_factory=lambda r: fake_manufacturer_directory, asset_storage=storage)
    with TestClient(app) as client:
        yield ApiClient(client, make_token("perm:product-catalog:all:all"))


@pytest.fixture
def product_with_assets(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Gaseosa cola")
    image = image_asset(session_factory, product.id, content=IMAGE_CONTENT)
    sheet = image_asset(session_factory, product.id, asset_type="TECHNICAL_SHEET", mime="application/pdf",
                        content=b"ficha", storage_uri="https://cdn.example.com/ficha.pdf", file_name="ficha.pdf")
    return product, image, sheet


def _code(response) -> str:
    return response.json()["code"].removeprefix("PRODUCT_CATALOG.")


def test_create_image_by_product_is_rejected_in_both_stages(admin, product_with_assets) -> None:
    product, *_ = product_with_assets
    response = admin.post(f"{V}/products/{product.id}/assets", json={
        "asset_type": "IMAGE", "file_name": "a.png", "storage_uri": f"s3://{BUCKET}/assets/x.png",
        "mime_type": "image/png", "is_primary": True})
    assert response.status_code == 422 and _code(response) == "IMAGE_REQUIRES_PRESENTATION"


def test_listing_and_detail(admin, product_with_assets, stage) -> None:
    product, image, sheet = product_with_assets
    listed = {item["id"]: item for item in admin.get(f"{V}/products/{product.id}/assets").json()}
    detail = admin.get(f"{V}/products/{product.id}?expand=detail").json()["detail"]["assets"]
    filtered = admin.get(f"{V}/products/{product.id}/assets", params={"asset_type": "IMAGE"})

    assert str(sheet.id) in listed and listed[str(sheet.id)]["global_product_presentation_id"] is None
    if stage == "transition":
        assert listed[str(image.id)]["global_product_presentation_id"] == str(image.global_product_presentation_id)
        assert {item["id"] for item in detail} == {str(image.id), str(sheet.id)}
        assert filtered.status_code == 200 and [item["id"] for item in filtered.json()] == [str(image.id)]
    else:
        assert str(image.id) not in listed
        assert {item["id"] for item in detail} == {str(sheet.id)}
        assert filtered.status_code == 422 and _code(filtered) == "IMAGE_REQUIRES_PRESENTATION"


def test_image_content_by_product_route(admin, product_with_assets, stage) -> None:
    product, image, _ = product_with_assets
    response = admin.get(f"{V}/products/{product.id}/assets/{image.id}/content")
    if stage == "transition":
        assert response.status_code == 200 and response.content == IMAGE_CONTENT
    else:
        assert response.status_code == 422 and _code(response) == "IMAGE_REQUIRES_PRESENTATION"


@pytest.mark.parametrize("action", ["update", "set-primary", "deactivate", "reactivate"])
def test_image_changes_by_product_route_are_frozen_or_rejected(admin, product_with_assets, stage, action) -> None:
    product, image, _ = product_with_assets
    url = f"{V}/products/{product.id}/assets/{image.id}"
    if action == "update":
        response = admin.put(url, json={"file_name": "b.png", "storage_uri": image.storage_uri, "mime_type": "image/png",
                                        "version": image.version})
    else:
        response = admin.post(f"{url}/{action}", json={"version": image.version})
    expected = (409, "IMAGE_MIGRATION_IN_PROGRESS") if stage == "transition" else (422, "IMAGE_REQUIRES_PRESENTATION")
    assert (response.status_code, _code(response)) == expected


def test_other_asset_types_keep_working_in_both_stages(admin, product_with_assets) -> None:
    product, _, sheet = product_with_assets
    url = f"{V}/products/{product.id}/assets"
    renamed = admin.put(f"{url}/{sheet.id}", json={"file_name": "ficha-v2.pdf", "storage_uri": sheet.storage_uri,
                                                   "mime_type": "application/pdf", "version": sheet.version})
    assert renamed.status_code == 200
    second = admin.post(url, json={"asset_type": "TECHNICAL_SHEET", "file_name": "otra.pdf",
                                   "storage_uri": "https://cdn.example.com/otra.pdf", "mime_type": "application/pdf"})
    assert second.status_code == 201
    primary = admin.post(f"{url}/{second.json()['id']}/set-primary", json={"version": second.json()["version"]})
    assert primary.status_code == 200 and primary.json()["is_primary"] is True
    deactivated = admin.post(f"{url}/{second.json()['id']}/deactivate", json={"version": primary.json()["version"]})
    assert deactivated.status_code == 200
    assert admin.post(f"{url}/{second.json()['id']}/reactivate",
                      json={"version": deactivated.json()["version"]}).status_code == 200


def test_presentation_routes_work_in_both_stages(admin, product_with_assets) -> None:
    product, image, _ = product_with_assets
    listed = admin.get(f"{V}/products/{product.id}/presentations/{image.global_product_presentation_id}/assets")
    assert listed.status_code == 200 and [item["id"] for item in listed.json()] == [str(image.id)]
