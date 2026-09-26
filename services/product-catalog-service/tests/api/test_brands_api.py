"""Marcas (FR-009, FR-018, FR-019)."""

from uuid import UUID

from tests import factories

URL = "/api/v1/brands"


def test_brand_crud(api) -> None:
    created = api.post(URL, json={"code": "acme", "name": "ACME S.A."})
    assert created.status_code == 201
    brand = created.json()
    assert brand["code"] == "ACME"

    updated = api.put(f"{URL}/{brand['id']}", json={"name": "Acme", "description": "Marca", "version": 1})
    assert updated.status_code == 200
    assert updated.json()["description"] == "Marca"


def test_duplicate_code_case_insensitive(api) -> None:
    api.post(URL, json={"code": "ACME", "name": "Acme"})
    response = api.post(URL, json={"code": "Acme", "name": "Otra"})
    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_CODE"


def test_deactivating_brand_keeps_products(api, session_factory) -> None:
    brand = api.post(URL, json={"code": "ACME", "name": "Acme"}).json()
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, brand_id=UUID(brand["id"]))

    assert api.post(f"{URL}/{brand['id']}/deactivate", json={"version": 1}).status_code == 200

    stored = api.get(f"/api/v1/products/{product.id}").json()
    assert stored["global_brand_id"] == brand["id"]
    assert stored["status"] == "ACTIVE"


def test_list_filters(api) -> None:
    api.post(URL, json={"code": "ACME", "name": "Acme"})
    other = api.post(URL, json={"code": "TECNO", "name": "Tecnoquímicas"}).json()
    api.post(f"{URL}/{other['id']}/deactivate", json={"version": 1})

    def codes(query: str) -> list[str]:
        return [item["code"] for item in api.get(f"{URL}?{query}").json()["items"]]

    assert codes("") == ["ACME", "TECNO"]
    assert codes("status=ACTIVE") == ["ACME"]
    assert codes("code=tecno") == ["TECNO"]
    assert codes("search=quimicas") == ["TECNO"]
