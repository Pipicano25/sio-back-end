"""Reglas transversales de la Fase B sobre todas sus rutas de escritura (T073; RC-12, RC-14; FR-090 a FR-092).

La empresa `INACTIVE` (lectura e inactivación permitidas; el resto `422
COMPANY_INACTIVE`) se verifica para todas las rutas en `test_isolation.py`, y la
ausencia de `DELETE` en `test_openapi_contract.py`.
"""

from __future__ import annotations

import pytest

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    code_of,
    condition_update_body,
    create_condition,
    create_price,
    create_price_list,
    create_supplier_product,
    presentation_update_body,
    price_list_update_body,
    price_update_body,
    supplier,
    supplier_product_update_body,
)
from tests.api.routes import PHASE_B_ROUTES, route_id
from tests.conftest import user_sub

PARAM = {
    "presentation": "presentation_id",
    "supplier_product": "supplier_product_id",
    "condition": "condition_id",
    "price_list": "price_list_id",
    "price_item": "price_list_item_id",
}
UPDATE_BODY = {
    "presentation": presentation_update_body,
    "supplier_product": supplier_product_update_body,
    "condition": condition_update_body,
    "price_list": price_list_update_body,
    "price_item": price_update_body,
}


@pytest.fixture
def rows(as_user, company, fake_catalog, fake_party, fake_payment):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    provider = supplier(client, company, fake_party)
    price_list = create_price_list(client, company)
    return {
        "presentation": adopt_presentation(client, company, fake_catalog, product),
        "supplier_product": create_supplier_product(client, company, provider, product, fake_catalog),
        "condition": create_condition(client, company, provider, fake_payment),
        "price_list": price_list,
        "price_item": create_price(client, company, price_list, product),
    }


def _body(route, row, version):
    if route.method == "PUT":
        return UPDATE_BODY[route.target](row, version=version)
    if route.path.endswith("/change-price"):
        return {"unit_price": "1", "version": version}
    return {"version": version}


VERSIONED = [route for route in PHASE_B_ROUTES if route.write and route.target in PARAM]


@pytest.mark.parametrize("route", VERSIONED, ids=route_id)
def test_stale_version_is_409_without_changes(as_user, rows, route):
    admin = as_user("admin.test")
    row = rows[route.target]
    url = route.path.format(**{PARAM[route.target]: row["id"]})
    if route.path.endswith("/reactivate"):
        row = admin.post(url.replace("/reactivate", "/deactivate"), json={"version": 1}).json()

    response = admin.request(route.method, url, json=_body(route, row, version=99))

    assert response.status_code == 409, response.text
    assert code_of(response) == "VERSION_CONFLICT"
    item_url = route.path.split("/{")[0] + "/" + row["id"]
    assert admin.get(item_url).json()["version"] == row["version"]


@pytest.mark.parametrize("field", ["created_by", "updated_by", "status", "company_id"])
@pytest.mark.parametrize(
    "path",
    ["company-product-presentations", "supplier-products", "supplier-payment-conditions", "price-lists", "price-list-items"],
)
def test_server_controlled_fields_rejected_on_create(as_user, company, path, field):
    response = as_user("admin.test").post(f"/api/v1/companies/{company}/{path}", json={field: "x"})
    assert response.status_code == 422
    assert any(error["field"] == field for error in response.json()["errors"]), response.json()


@pytest.mark.parametrize("target", sorted(PARAM))
def test_audit_created_by_immutable_and_updated_by_real(as_user, rows, target):
    row = rows[target]
    base = next(route.path for route in PHASE_B_ROUTES if route.target == target and route.method == "PUT")
    url = base.format(**{PARAM[target]: row["id"]})

    response = as_user("supervisor.test").post(url + "/reactivate", json={"version": row["version"]})
    assert response.status_code == 409  # ya activo: transición inválida, sin cambios

    deactivated = as_user("admin.test").post(url + "/deactivate", json={"version": row["version"]}).json()
    reactivated = as_user("supervisor.test").post(url + "/reactivate", json={"version": deactivated["version"]})
    assert reactivated.status_code == 200, reactivated.text
    body = reactivated.json()
    assert body["created_by"] == user_sub("admin.test")
    assert body["updated_by"] == user_sub("supervisor.test")
