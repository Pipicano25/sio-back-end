"""Contratos internos tras la spec 024: PC-3 con imágenes, PC-1 sin ellas y PC-2 `has_image` (casos 31f y 35)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient
from tests.spec022_support import PUBLIC_BASE, image_asset, spec022_settings

V = "/api/v1"


def _client(test_database_url, test_auth, fake_manufacturer_directory, make_token, **overrides):
    app = create_app(spec022_settings(test_database_url, **overrides), auth=test_auth,
                     manufacturer_directory_factory=lambda r: fake_manufacturer_directory)
    return TestClient(app), make_token("perm:product-catalog:products:read")


@pytest.fixture
def reader(test_database_url, clean_database, test_auth, fake_manufacturer_directory, make_token):
    client, token = _client(test_database_url, test_auth, fake_manufacturer_directory, make_token)
    with client:
        yield ApiClient(client, token)


@pytest.fixture
def catalog(session_factory):
    """Un producto con tres presentaciones: dos imágenes en la botella, una en la lata y ninguna en la caja."""
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Gaseosa cola")
    bottle = factories.presentation(session_factory, product.id, "BOTELLA")
    can = factories.presentation(session_factory, product.id, "LATA")
    box = factories.presentation(session_factory, product.id, "CAJA")
    old = image_asset(session_factory, product.id, content=b"\x89PNG\r\n\x1a\nvieja", presentation_id=bottle.id,
                      is_primary=False)
    front = image_asset(session_factory, product.id, content=b"\x89PNG\r\n\x1a\nfrente", presentation_id=bottle.id)
    can_image = image_asset(session_factory, product.id, content=b"\x89PNG\r\n\x1a\nlata", presentation_id=can.id)
    image_asset(session_factory, product.id, content=b"\x89PNG\r\n\x1a\nretirada", presentation_id=can.id,
                is_primary=False, status="INACTIVE")
    return dict(product=product, bottle=bottle, can=can, box=box, old=old, front=front, can_image=can_image)


def _lookup(reader, ids, **params):
    response = reader.post(f"{V}/presentations/batch-lookup", json={"ids": [str(i) for i in ids]}, params=params)
    assert response.status_code == 200, response.text
    return {item["id"]: item for item in response.json()["items"]}


def test_pc3_brings_each_presentation_primary_image(reader, catalog) -> None:
    items = _lookup(reader, [catalog["bottle"].id, catalog["can"].id, catalog["box"].id])
    bottle, can, box = (items[str(catalog[k].id)] for k in ("bottle", "can", "box"))

    assert bottle["has_image"] is True and bottle["image_asset_id"] == str(catalog["front"].id)
    assert can["has_image"] is True and can["image_asset_id"] == str(catalog["can_image"].id)
    assert bottle["image_url"] != can["image_url"]
    assert bottle["image_url"].startswith(f"{PUBLIC_BASE}/api/v1/public/product-images?ref=")
    assert box == {**box, "has_image": False, "image_asset_id": None, "image_url": None}
    assert all("images" not in item for item in items.values())


def test_pc3_include_images_lists_active_images_primary_first(reader, catalog) -> None:
    items = _lookup(reader, [catalog["bottle"].id, catalog["can"].id, catalog["box"].id], include_images="true")
    bottle = items[str(catalog["bottle"].id)]["images"]
    assert [(image["asset_id"], image["is_primary"]) for image in bottle] == [
        (str(catalog["front"].id), True), (str(catalog["old"].id), False)]
    assert all(image["image_url"] for image in bottle)
    assert [image["asset_id"] for image in items[str(catalog["can"].id)]["images"]] == [str(catalog["can_image"].id)]
    assert items[str(catalog["box"].id)]["images"] == []


def test_pc3_constant_number_of_queries(reader, session_factory) -> None:
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Varias")
    presentations = [factories.presentation(session_factory, product.id, f"P{i}") for i in range(20)]
    for index, presentation in enumerate(presentations):
        image_asset(session_factory, product.id, content=f"img{index}".encode(), presentation_id=presentation.id)

    def count(ids) -> int:
        statements: list[str] = []
        listener = lambda *args: statements.append(args[2])  # noqa: E731
        event.listen(Engine, "before_cursor_execute", listener)
        try:
            _lookup(reader, ids, include_images="true")
        finally:
            event.remove(Engine, "before_cursor_execute", listener)
        return len(statements)

    assert count([presentations[0].id]) == count([p.id for p in presentations])


def test_pc3_without_public_route_has_image_but_no_urls(test_database_url, clean_database, test_auth,
                                                        fake_manufacturer_directory, make_token, catalog) -> None:
    client, token = _client(test_database_url, test_auth, fake_manufacturer_directory, make_token,
                            image_ref_secret=None, public_base_url=None)
    with client:
        items = _lookup(ApiClient(client, token), [catalog["bottle"].id], include_images="true")
    bottle = items[str(catalog["bottle"].id)]
    assert bottle["has_image"] is True and bottle["image_url"] is None
    assert all(image["image_url"] is None for image in bottle["images"])


@pytest.mark.parametrize(("stage", "has_fields"), [("transition", True), ("completed", False)])
def test_pc1_image_fields_depend_on_stage(test_database_url, clean_database, test_auth, fake_manufacturer_directory,
                                          make_token, catalog, stage, has_fields) -> None:
    client, token = _client(test_database_url, test_auth, fake_manufacturer_directory, make_token,
                            image_migration_stage=stage)
    with client:
        response = ApiClient(client, token).post(f"{V}/products/summaries/batch-lookup",
                                                 json={"ids": [str(catalog["product"].id)]})
    item = response.json()["items"][0]
    assert item["found"] is True
    assert ({"has_image", "image_asset_id", "image_url"} <= set(item)) is has_fields


def test_pc2_has_image_means_some_presentation_with_primary_image(reader, session_factory, catalog) -> None:
    unit = factories.unit(session_factory, "KG")
    without = factories.product(session_factory, unit.id, "Sin imagen")
    factories.presentation(session_factory, without.id, "UNIDAD")
    one = factories.product(session_factory, unit.id, "Una presentación con imagen")
    only = factories.presentation(session_factory, one.id, "UNIDAD")
    factories.presentation(session_factory, one.id, "CAJA")
    image_asset(session_factory, one.id, content=b"\x89PNG\r\n\x1a\nuna", presentation_id=only.id)
    secondary_only = factories.product(session_factory, unit.id, "Solo secundaria")
    lonely = factories.presentation(session_factory, secondary_only.id, "UNIDAD")
    image_asset(session_factory, secondary_only.id, content=b"\x89PNG\r\n\x1a\nsec", presentation_id=lonely.id,
                is_primary=False)
    candidates = [str(p.id) for p in (without, one, catalog["product"], secondary_only)]

    def match(flag: bool) -> list[str]:
        response = reader.post(f"{V}/products/match", json={"candidate_ids": candidates, "has_image": flag})
        assert response.status_code == 200, response.text
        return response.json()["ids"]

    assert match(True) == [str(one.id), str(catalog["product"].id)]
    assert match(False) == [str(without.id), str(secondary_only.id)]
