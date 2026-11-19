"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

- El `PUT` recibe solo los campos que cambian; un campo ausente no cambia.
- `null` borra un campo opcional; en un campo obligatorio responde `422`.
- Un cuerpo vacío o solo con `version` responde `422`.
- `version` es opcional: si llega y no coincide, `409`; si no llega, se aplica sobre lo vigente.
- Inactivar y reactivar no exigen versión ni cuerpo.
"""

from __future__ import annotations

import pytest

from tests.api.helpers import adopt, create_price_list, person_customer


def test_company_product_put_with_one_field_keeps_the_rest(as_user, company, fake_catalog):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog, short_name="CORTO")

    response = client.put(f"/api/v1/company-products/{product['id']}", json={"display_name": "Nombre nuevo"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "Nombre nuevo"
    for field in ("internal_code", "short_name", "currency_code", "is_sellable", "is_purchasable"):
        assert body[field] == product[field]
    assert body["version"] == product["version"] + 1


def test_company_product_null_clears_optional_and_rejects_required(as_user, company, fake_catalog):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog, short_name="CORTO")

    cleared = client.put(f"/api/v1/company-products/{product['id']}", json={"short_name": None})
    rejected = client.put(f"/api/v1/company-products/{product['id']}", json={"display_name": None})

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["short_name"] is None
    assert rejected.status_code == 422


def test_company_product_stale_version_is_409(as_user, company, fake_catalog):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog)
    client.put(f"/api/v1/company-products/{product['id']}", json={"display_name": "Primero"})

    response = client.put(
        f"/api/v1/company-products/{product['id']}", json={"display_name": "Segundo", "version": product["version"]}
    )

    assert response.status_code == 409
    assert client.get(f"/api/v1/company-products/{product['id']}").json()["display_name"] == "Primero"


@pytest.mark.parametrize("body", [{}, {"version": 1}, {"desconocido": 1}])
def test_company_product_body_without_valid_changes_is_422(as_user, company, fake_catalog, body):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog)

    assert client.put(f"/api/v1/company-products/{product['id']}", json=body).status_code == 422


def test_company_product_immutable_field_is_still_rejected(as_user, company, fake_catalog):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog)

    response = client.put(f"/api/v1/company-products/{product['id']}", json={"global_product_id": product["id"]})

    assert response.status_code == 422


def test_company_product_status_actions_without_body(as_user, company, fake_catalog):
    client = as_user("admin.sio")
    product = adopt(client, company, fake_catalog)

    deactivated = client.post(f"/api/v1/company-products/{product['id']}/deactivate")
    reactivated = client.post(f"/api/v1/company-products/{product['id']}/reactivate", json={})

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "ACTIVE"


def test_customer_put_changes_only_display_name(as_user, company, fake_party):
    client = as_user("admin.sio")
    customer = person_customer(client, company, fake_party)

    response = client.put(f"/api/v1/company-customers/{customer['id']}", json={"display_name": "Cliente renombrado"})

    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Cliente renombrado"
    assert response.json()["internal_code"] == customer["internal_code"]


def test_price_list_put_changes_only_name(as_user, company):
    client = as_user("admin.sio")
    price_list = create_price_list(client, company, description="Lista de prueba")

    response = client.put(f"/api/v1/price-lists/{price_list['id']}", json={"name": "Mayorista"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Mayorista"
    assert (body["code"], body["description"], body["is_default"]) == (
        price_list["code"],
        "Lista de prueba",
        price_list["is_default"],
    )
