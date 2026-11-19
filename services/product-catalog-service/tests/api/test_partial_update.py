"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

- El `PUT` recibe solo los campos que cambian; un campo ausente no cambia.
- `null` borra un campo opcional; en un campo obligatorio responde `422`.
- Un cuerpo vacío o solo con `version` responde `422`.
- `version` es opcional: si llega y no coincide, `409`; si no llega, se aplica sobre lo vigente.
- Inactivar y reactivar no exigen versión ni cuerpo.
"""

from decimal import Decimal
from uuid import UUID

import pytest

from tests import factories

BRANDS = "/api/v1/brands"
PRODUCTS = "/api/v1/products"


def test_brand_put_with_one_field_keeps_the_rest(api) -> None:
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME S.A.", "description": "Marca"}).json()

    response = api.put(f"{BRANDS}/{brand['id']}", json={"name": "Acme"})

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Acme"
    assert response.json()["description"] == "Marca"
    assert response.json()["version"] == brand["version"] + 1


def test_brand_null_clears_description_and_rejects_null_name(api) -> None:
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME S.A.", "description": "Marca"}).json()

    cleared = api.put(f"{BRANDS}/{brand['id']}", json={"description": None})
    rejected = api.put(f"{BRANDS}/{brand['id']}", json={"name": None})

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["description"] is None
    assert cleared.json()["name"] == "ACME S.A."
    assert rejected.status_code == 422


def test_brand_stale_version_is_409_and_missing_version_applies(api) -> None:
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME S.A."}).json()
    api.put(f"{BRANDS}/{brand['id']}", json={"name": "Primero"})

    stale = api.put(f"{BRANDS}/{brand['id']}", json={"name": "Segundo", "version": 1})
    latest = api.put(f"{BRANDS}/{brand['id']}", json={"name": "Tercero"})

    assert stale.status_code == 409
    assert latest.status_code == 200, latest.text
    assert latest.json()["name"] == "Tercero"


@pytest.mark.parametrize("body", [{}, {"version": 1}, {"desconocido": 1}, {"code": "OTRA"}])
def test_brand_body_without_valid_changes_is_422(api, body) -> None:
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME S.A."}).json()

    assert api.put(f"{BRANDS}/{brand['id']}", json=body).status_code == 422


def test_brand_status_actions_without_body(api) -> None:
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME S.A."}).json()

    deactivated = api.post(f"{BRANDS}/{brand['id']}/deactivate")
    reactivated = api.post(f"{BRANDS}/{brand['id']}/reactivate", json={})

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "ACTIVE"


def test_product_put_changes_only_description(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    brand = api.post(BRANDS, json={"code": "acme", "name": "ACME"}).json()
    product = factories.product(session_factory, unit.id, brand_id=UUID(brand["id"]))
    before = api.get(f"{PRODUCTS}/{product.id}").json()

    response = api.put(f"{PRODUCTS}/{product.id}", json={"description": "Descripción nueva"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["description"] == "Descripción nueva"
    assert body["canonical_name"] == before["canonical_name"]
    assert body["global_brand_id"] == brand["id"]
    assert body["base_unit_id"] == before["base_unit_id"]


def test_presentation_put_changes_only_name(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    presentation = factories.presentation(session_factory, product.id, "CAJA", base_quantity=12)

    response = api.put(f"/api/v1/presentations/{presentation.id}", json={"name": "Caja x12"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Caja x12"
    assert body["code"] == "CAJA"
    assert Decimal(body["base_quantity"]) == 12
