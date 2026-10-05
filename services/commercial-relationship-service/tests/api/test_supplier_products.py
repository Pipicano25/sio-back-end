"""Historia 2 de la 010: productos de proveedor (T033; FR-020 a FR-028; aclaración 3; I1)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    code_of,
    create_supplier_product,
    supplier,
    supplier_product_body,
    supplier_product_update_body,
)

URL = "/api/v1/companies/{company}/supplier-products"


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def world(admin, company, fake_catalog, fake_party):
    product = adopt(admin, company, fake_catalog)
    provider = supplier(admin, company, fake_party)
    return {"product": product, "supplier": provider}


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def test_scenario_1_creates_with_defaults(admin, company, fake_catalog, world):
    response = _post(admin, company, supplier_product_body(
        world["supplier"], world["product"], fake_catalog, negotiated_unit_cost="12500.5000"
    ))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["pack_quantity"] == "1.0000" and body["minimum_order_quantity"] == "0.0000"
    assert body["negotiated_unit_cost"] == "12500.5000" and body["currency_code"] == "COP"
    assert response.headers["Location"] == f"/api/v1/supplier-products/{body['id']}"


def test_scenario_2_purchase_unit_must_be_base_unit(admin, company, fake_catalog, world):
    response = _post(admin, company, supplier_product_body(
        world["supplier"], world["product"], fake_catalog, purchase_unit_id=str(uuid4())
    ))
    assert response.status_code == 422 and code_of(response) == "PURCHASE_UNIT_NOT_BASE_UNIT"


@pytest.mark.parametrize(("action", "code"), [("deactivate", "COMPANY_SUPPLIER_INACTIVE"), ("block", "COMPANY_SUPPLIER_BLOCKED")])
def test_scenario_3_fr_021_supplier_not_active_separate_causes(admin, company, fake_catalog, world, action, code):
    body = {"version": 1} if action == "deactivate" else {"version": 1, "block_reason": "Revisión"}
    admin.post(f"/api/v1/company-suppliers/{world['supplier']['id']}/{action}", json=body)

    response = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog))
    assert response.status_code == 422 and code_of(response) == code
    assert response.json()["errors"][0]["field"] == "company_supplier_id"


def test_scenario_3_inactive_company_product(admin, company, fake_catalog, world):
    admin.post(f"/api/v1/company-products/{world['product']['id']}/deactivate", json={"version": 1})
    response = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog))
    assert response.status_code == 422 and code_of(response) == "COMPANY_PRODUCT_INACTIVE"


def test_scenario_4_presentation_checks(admin, company, fake_catalog, world):
    other_product = adopt(admin, company, fake_catalog, internal_code="000046")
    of_other = adopt_presentation(admin, company, fake_catalog, other_product)
    not_purchasable = adopt_presentation(admin, company, fake_catalog, world["product"], is_purchasable=False)
    inactive = adopt_presentation(admin, company, fake_catalog, world["product"])
    admin.post(f"/api/v1/company-product-presentations/{inactive['id']}/deactivate", json={"version": 1})

    for presentation, code in (
        (of_other, "PRESENTATION_OF_OTHER_PRODUCT"),
        (not_purchasable, "PRESENTATION_NOT_PURCHASABLE"),
        (inactive, "PRESENTATION_INACTIVE"),
        ({"id": str(uuid4())}, "PRESENTATION_NOT_FOUND"),
    ):
        response = _post(admin, company, supplier_product_body(
            world["supplier"], world["product"], fake_catalog, company_product_presentation_id=presentation["id"]
        ))
        assert response.status_code == 422 and code_of(response) == code, presentation


def test_scenarios_5_and_6_uniqueness_by_presentation_among_active(admin, company, fake_catalog, world):
    presentation = adopt_presentation(admin, company, fake_catalog, world["product"])
    general = create_supplier_product(admin, company, world["supplier"], world["product"], fake_catalog)
    create_supplier_product(
        admin, company, world["supplier"], world["product"], fake_catalog,
        company_product_presentation_id=presentation["id"],
    )

    duplicate = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog))
    assert duplicate.status_code == 409 and code_of(duplicate) == "DUPLICATE_SUPPLIER_PRODUCT"

    # Inactiva no cuenta; reactivar revalida la unicidad entre ACTIVE.
    admin.post(f"/api/v1/supplier-products/{general['id']}/deactivate", json={"version": 1})
    replacement = create_supplier_product(admin, company, world["supplier"], world["product"], fake_catalog)
    reactivate = admin.post(f"/api/v1/supplier-products/{general['id']}/reactivate", json={"version": 2})
    assert reactivate.status_code == 409 and code_of(reactivate) == "DUPLICATE_SUPPLIER_PRODUCT"
    assert replacement["status"] == "ACTIVE"


def test_scenario_7_preferred_swaps_atomically(admin, company, fake_catalog, fake_party, world):
    other_supplier = supplier(admin, company, fake_party, internal_code="PRV-002")
    first = create_supplier_product(admin, company, world["supplier"], world["product"], fake_catalog, is_preferred=True)
    second = create_supplier_product(admin, company, other_supplier, world["product"], fake_catalog, is_preferred=True)

    assert second["is_preferred"] is True
    previous = admin.get(f"/api/v1/supplier-products/{first['id']}").json()
    assert previous["is_preferred"] is False and previous["version"] == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"pack_quantity": "0"},
        {"minimum_order_quantity": "-1"},
        {"negotiated_unit_cost": "-5"},
        {"expected_supplier_lead_time_hours": "-1"},
        {"negotiated_unit_cost": "1.12345"},
        {"expected_supplier_lead_time_hours": "1.123"},
        {"priority": 40000},
    ],
)
def test_scenario_8_invalid_values(admin, company, fake_catalog, world, overrides):
    response = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog, **overrides))
    assert response.status_code == 422 and code_of(response) == "VALIDATION_ERROR"


def test_currency_must_be_supported(admin, company, fake_catalog, world):
    response = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog, currency_code="ZAR"))
    assert response.status_code == 422 and code_of(response) == "CURRENCY_NOT_SUPPORTED"


def test_scenario_9_product_catalog_unavailable(admin, company, fake_catalog, world):
    fake_catalog.base_unit_unavailable = True
    response = _post(admin, company, supplier_product_body(world["supplier"], world["product"], fake_catalog))
    assert response.status_code == 503 and response.json()["dependency"] == "product-catalog"
    assert admin.get(URL.format(company=company), params={"status": "ALL"}).json()["total_records"] == 0


def test_put_rules_and_modification_in_any_state(admin, company, fake_catalog, world):
    created = create_supplier_product(admin, company, world["supplier"], world["product"], fake_catalog)
    url = f"/api/v1/supplier-products/{created['id']}"

    for field in ("company_supplier_id", "company_product_id"):
        response = admin.put(url, json={**supplier_product_update_body(created), field: str(uuid4())})
        assert response.status_code == 422 and code_of(response) == "IMMUTABLE_FIELD"

    same = admin.put(url, json=supplier_product_update_body(created))
    assert same.status_code == 200 and same.json()["version"] == 1

    deactivated = admin.post(url + "/deactivate", json={"version": 1}).json()
    edited = admin.put(url, json=supplier_product_update_body(deactivated, supplier_product_code="PRV-COD-9"))
    assert edited.status_code == 200 and edited.json()["status"] == "INACTIVE"

    marked = admin.put(url, json=supplier_product_update_body(edited.json(), is_preferred=True))
    assert marked.status_code == 422 and code_of(marked) == "DEFAULT_REQUIRES_ACTIVE"

    stale = admin.put(url, json=supplier_product_update_body(edited.json(), priority=3, version=1))
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"


def test_list_filters(admin, company, fake_catalog, fake_party, world):
    other_supplier = supplier(admin, company, fake_party, internal_code="PRV-002")
    first = create_supplier_product(
        admin, company, world["supplier"], world["product"], fake_catalog, supplier_product_code="ABC-77", is_preferred=True,
    )
    create_supplier_product(admin, company, other_supplier, world["product"], fake_catalog)
    url = URL.format(company=company)

    assert admin.get(url).json()["total_records"] == 2
    assert admin.get(url, params={"search": "abc"}).json()["items"][0]["id"] == first["id"]
    assert admin.get(url, params={"company_supplier_id": other_supplier["id"]}).json()["total_records"] == 1
    assert admin.get(url, params={"is_preferred": "true"}).json()["total_records"] == 1
    assert admin.get(url, params={"company_product_id": world["product"]["id"]}).json()["total_records"] == 2


def test_readers_and_permissions(as_user, admin, company, fake_catalog, world):
    created = create_supplier_product(admin, company, world["supplier"], world["product"], fake_catalog)

    assert as_user("consulta.test").get(f"/api/v1/supplier-products/{created['id']}").status_code == 200
    assert _post(as_user("compras.test"), company, {}).status_code == 403
    assert as_user("supervisor.test").post(
        f"/api/v1/supplier-products/{created['id']}/deactivate", json={"version": 1}
    ).status_code == 403
    assert as_user("inventario.test").get(URL.format(company=company)).status_code == 403
