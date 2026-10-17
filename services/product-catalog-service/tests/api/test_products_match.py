"""PC-2: productos globales por filtros (spec 022, FR-022-83; T029).

Modo evaluador (subconjunto de `candidate_ids`) y modo conductor (orden estable por nombre canónico
normalizado e `id`, continuación *keyset*, `has_more` sin conteo).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient
from tests.spec022_support import image_asset, spec022_settings

URL = "/api/v1/products/match"


@pytest.fixture
def client(test_database_url, clean_database, test_auth, fake_manufacturer_directory):
    app = create_app(spec022_settings(test_database_url), auth=test_auth,
                     manufacturer_directory_factory=lambda request: fake_manufacturer_directory)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def reader(client, make_token) -> ApiClient:
    return ApiClient(client, make_token("perm:product-catalog:products:read"))


def _match(reader, **body):
    response = reader.post(URL, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _walk(reader, limit: int, **filters) -> list[str]:
    seen: list[str] = []
    after = None
    for _ in range(100):
        page = _match(reader, limit=limit, **({"after": after} if after else {}), **filters)
        assert set(page) == {"items", "has_more"}
        seen.extend(item["id"] for item in page["items"])
        if not page["has_more"]:
            return seen
        after = page["items"][-1]["position"]
    raise AssertionError("no terminó")


@pytest.fixture
def catalog(session_factory):
    unit = factories.unit(session_factory)
    colgate = factories.brand(session_factory, "COLGATE")
    other_brand = factories.brand(session_factory, "OTRA")
    parent = factories.category(session_factory, "HIGIENE")
    child = factories.category(session_factory, "ORAL", parent=parent.id)
    names = ["Crema B", "Crema A", "Crema B", "Cepillo", "Enjuague"]
    products = [factories.product(session_factory, unit.id, name, brand_id=colgate.id) for name in names]
    other = factories.product(session_factory, unit.id, "Jabón", brand_id=other_brand.id)
    inactive = factories.product(session_factory, unit.id, "Crema vieja", brand_id=colgate.id, status="INACTIVE")
    factories.product_category(session_factory, products[0].id, child.id)
    factories.product_category(session_factory, products[1].id, parent.id)
    factories.identifier(session_factory, products[3].id, "7702010000017")
    image_asset(session_factory, products[0].id, content=b"imagen 0")
    image_asset(session_factory, products[2].id, content=b"imagen 2", mime="image/svg+xml")
    return dict(products=products, other=other, inactive=inactive, colgate=colgate, parent=parent, child=child)


def _by_key(products) -> list[str]:
    from product_catalog_service.application.normalization import canonical_name_key

    return [str(p.id) for p in sorted(products, key=lambda p: (canonical_name_key(p.canonical_name), str(p.id)))]


def test_conductor_walk_by_brand_with_ties(reader, catalog) -> None:
    expected = _by_key(catalog["products"])
    for limit in (1, 2, 5):
        assert _walk(reader, limit, brand_ids=[str(catalog["colgate"].id)]) == expected


def test_conductor_status_default_active(reader, catalog) -> None:
    ids = _walk(reader, 10, brand_ids=[str(catalog["colgate"].id)])
    assert str(catalog["inactive"].id) not in ids
    all_ids = _walk(reader, 10, brand_ids=[str(catalog["colgate"].id)], status="ALL")
    assert str(catalog["inactive"].id) in all_ids


def test_category_with_and_without_descendants(reader, catalog) -> None:
    parent = str(catalog["parent"].id)
    assert _walk(reader, 10, category_ids=[parent]) == [str(catalog["products"][1].id)]
    with_children = _walk(reader, 10, category_ids=[parent], include_descendants=True)
    assert sorted(with_children) == sorted([str(catalog["products"][0].id), str(catalog["products"][1].id)])


def test_identifier_is_exact(reader, catalog) -> None:
    assert _walk(reader, 10, identifier="7702010000017") == [str(catalog["products"][3].id)]
    assert _walk(reader, 10, identifier="770201") == []


def test_has_image_true_and_false(reader, catalog) -> None:
    with_image = _walk(reader, 10, has_image=True)
    assert with_image == [str(catalog["products"][0].id)]  # el SVG no cuenta
    without = _walk(reader, 10, has_image=False, brand_ids=[str(catalog["colgate"].id)])
    assert str(catalog["products"][0].id) not in without
    assert str(catalog["products"][2].id) in without


def test_evaluator_mode_returns_subset_in_request_order(reader, catalog) -> None:
    products = catalog["products"]
    candidates = [str(catalog["other"].id), str(products[3].id), str(uuid4()), str(products[0].id)]
    page = _match(reader, candidate_ids=candidates, brand_ids=[str(catalog["colgate"].id)])
    assert page == {"ids": [str(products[3].id), str(products[0].id)]}
    assert _match(reader, candidate_ids=candidates, has_image=True) == {"ids": [str(products[0].id)]}


def test_validation(reader) -> None:
    some = [str(uuid4())]
    cases = [
        {"limit": 0},
        {"limit": 101},
        {},
        {"candidate_ids": some, "after": {"k": ["x"], "id": some[0]}},
        {"candidate_ids": some, "limit": 10},
        {"candidate_ids": [str(uuid4()) for _ in range(101)]},
        {"limit": 10, "unknown": 1},
        {"limit": 10, "status": "BLOQUEADO"},
        {"limit": 10, "after": {"k": ["x"]}},
    ]
    for body in cases:
        assert reader.post(URL, json=body).status_code == 422, body


def test_permission(client, make_token) -> None:
    body = {"limit": 5}
    assert ApiClient(client, make_token("perm:product-catalog:brands:read")).post(URL, json=body).status_code == 403
    assert ApiClient(client, None).post(URL, json=body).status_code == 401
