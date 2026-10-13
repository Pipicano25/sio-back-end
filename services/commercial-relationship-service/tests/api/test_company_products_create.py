"""Historia 1: adoptar un producto global (FR-010 a FR-014; RC-01, RC-05, RC-07, RC-12)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import adopt, code_of, product_body
from tests.conftest import user_sub

URL = "/api/v1/companies/{company}/company-products"


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def test_adoption_with_defaults_and_first_use(as_user, company, fake_catalog):
    product = fake_catalog.add(uuid4())
    response = _post(as_user("supervisor.test"), company, product_body(product))

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["location"] == f"/api/v1/company-products/{body['id']}"
    assert body["status"] == "ACTIVE" and body["version"] == 1
    assert body["company_id"] == str(company)
    # Spec 019: sin precio ni costo (ni siquiera 0).
    assert "sale_price" not in body and "reference_cost" not in body
    assert body["inventory_control_enabled"] is True and body["lot_tracking_enabled"] is False
    assert body["expiration_tracking_enabled"] is False
    assert body["is_purchasable"] is True and body["is_sellable"] is True
    assert body["created_by"] == body["updated_by"] == user_sub("supervisor.test")
    assert fake_catalog.first_use_calls == [product]
    # Sin datos del producto global (Principio III).
    assert not {"canonical_name", "brand", "base_unit_id"} & set(body)

    detail = as_user("compras.test").get(f"/api/v1/company-products/{body['id']}")
    assert detail.status_code == 200 and detail.json() == body


@pytest.mark.parametrize(
    "field,value", [("sale_price", "12500.50"), ("reference_cost", "3400.1250"), ("sale_price", "0"), ("reference_cost", 0)]
)
def test_price_and_cost_are_rejected_spec_019(as_user, company, fake_catalog, field, value):
    """FR-019-02: enviar `sale_price` o `reference_cost` (aunque sea 0) responde `422` y no guarda nada."""
    product = fake_catalog.add(uuid4())
    response = _post(as_user("admin.test"), company, product_body(product, **{field: value}))
    assert response.status_code == 422, response.text
    assert code_of(response) == "VALIDATION_ERROR" and field in response.text
    assert fake_catalog.first_use_calls == []


def test_incomplete_product_is_not_eligible(as_user, company, fake_catalog):
    product = fake_catalog.add(uuid4(), eligible=False)
    response = _post(as_user("admin.test"), company, product_body(product))
    assert response.status_code == 422
    assert code_of(response) == "GLOBAL_PRODUCT_NOT_ELIGIBLE"
    assert response.json()["errors"][0]["field"] == "global_product_id"
    assert fake_catalog.first_use_calls == []


def test_inactive_and_missing_product_have_distinct_codes(as_user, company, fake_catalog):
    inactive = fake_catalog.add(uuid4(), status="INACTIVE")
    response = _post(as_user("admin.test"), company, product_body(inactive))
    assert code_of(response) == "GLOBAL_PRODUCT_INACTIVE"

    response = _post(as_user("admin.test"), company, product_body(uuid4(), internal_code="X-2"))
    assert response.status_code == 422
    assert code_of(response) == "GLOBAL_PRODUCT_NOT_FOUND"


def test_duplicate_adoption_in_any_state_without_first_use(as_user, company, fake_catalog):
    client = as_user("admin.test")
    first = adopt(client, company, fake_catalog)
    deactivated = client.post(
        f"/api/v1/company-products/{first['id']}/deactivate", json={"version": first["version"]}
    )
    assert deactivated.status_code == 200

    calls_before = list(fake_catalog.first_use_calls)
    response = _post(client, company, product_body(first["global_product_id"], internal_code="OTRO"))
    assert response.status_code == 409
    assert code_of(response) == "DUPLICATE_ADOPTION"
    assert fake_catalog.first_use_calls == calls_before


def test_internal_code_is_case_insensitive(as_user, company, fake_catalog):
    client = as_user("admin.test")
    adopt(client, company, fake_catalog, internal_code="ABC-1")
    product = fake_catalog.add(uuid4())
    response = _post(client, company, product_body(product, internal_code="  abc-1 "))
    assert response.status_code == 409
    assert code_of(response) == "DUPLICATE_INTERNAL_CODE"


def test_first_use_failures(as_user, company, fake_catalog):
    client = as_user("admin.test")
    fake_catalog.first_use_error = "unavailable"
    product = fake_catalog.add(uuid4())
    response = _post(client, company, product_body(product))
    assert response.status_code == 503
    assert response.json()["dependency"] == "product-catalog"

    fake_catalog.first_use_error = "not_eligible"
    response = _post(client, company, product_body(product))
    assert code_of(response) == "GLOBAL_PRODUCT_NOT_ELIGIBLE"

    listing = client.get(URL.format(company=company), params={"status": "ALL"})
    assert listing.json()["total_records"] == 0  # nada se guardó


def test_eligibility_unavailable_is_503(as_user, company, fake_catalog):
    fake_catalog.lookup_unavailable = True
    response = _post(as_user("admin.test"), company, product_body(uuid4()))
    assert response.status_code == 503
    assert response.json()["dependency"] == "product-catalog"


def test_same_global_product_in_another_company(as_user, company, fake_catalog, fake_oc):
    other = uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)
    first = adopt(as_user("admin.test"), company, fake_catalog)
    response = _post(as_user("admin.test"), other, product_body(first["global_product_id"]))
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"inventory_control_enabled": False, "lot_tracking_enabled": True}, "lot_tracking_enabled"),
        ({"lot_tracking_enabled": False, "expiration_tracking_enabled": True}, "expiration_tracking_enabled"),
    ],
)
def test_inventory_flags(as_user, company, fake_catalog, overrides, field):
    product = fake_catalog.add(uuid4())
    response = _post(as_user("admin.test"), company, product_body(product, **overrides))
    assert response.status_code == 422
    assert code_of(response) == "INVENTORY_FLAGS_INVALID"
    assert response.json()["errors"][0]["field"] == field


def test_lots_and_expiration_together(as_user, company, fake_catalog):
    body = adopt(
        as_user("admin.test"), company, fake_catalog, lot_tracking_enabled=True, expiration_tracking_enabled=True
    )
    assert body["lot_tracking_enabled"] and body["expiration_tracking_enabled"]


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"currency_code": "XYZ"}, "CURRENCY_NOT_SUPPORTED"),
        ({"currency_code": "ZAR"}, "CURRENCY_NOT_SUPPORTED"),
        ({"display_name": "   "}, "VALIDATION_ERROR"),
        ({"internal_code": "x" * 61}, "VALIDATION_ERROR"),
        ({"status": "INACTIVE"}, "VALIDATION_ERROR"),
        ({"company_id": str(uuid4())}, "VALIDATION_ERROR"),
        ({"updated_by": "x"}, "VALIDATION_ERROR"),
    ],
)
def test_value_rules(as_user, company, fake_catalog, overrides, code):
    product = fake_catalog.add(uuid4())
    response = _post(as_user("admin.test"), company, product_body(product, **overrides))
    assert response.status_code == 422, response.text
    assert code_of(response) == code
    assert fake_catalog.first_use_calls == []


def test_missing_display_name_has_no_default(as_user, company, fake_catalog):
    body = product_body(fake_catalog.add(uuid4()))
    del body["display_name"]
    response = _post(as_user("admin.test"), company, body)
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "display_name"


def test_lowercase_currency_is_normalized(as_user, company, fake_catalog):
    assert adopt(as_user("admin.test"), company, fake_catalog, currency_code="cop")["currency_code"] == "COP"


def test_non_member_gets_404_even_with_invalid_body(as_user, other_company, fake_catalog):
    response = _post(as_user("admin.test"), other_company, {"basura": True})
    assert response.status_code == 404
    assert code_of(response) == "NOT_FOUND"
    assert fake_catalog.lookup_calls == []


def test_inactive_company(as_user, company, fake_catalog, fake_oc):
    fake_oc.inactive_companies.add(company)
    response = _post(as_user("admin.test"), company, product_body(fake_catalog.add(uuid4())))
    assert response.status_code == 422
    assert code_of(response) == "COMPANY_INACTIVE"


@pytest.mark.parametrize("username", ["compras.test", "ventas.test", "reportes.test", "inventario.test"])
def test_without_create_permission_is_403(as_user, company, fake_catalog, fake_oc, username):
    response = _post(as_user(username), company, product_body(fake_catalog.add(uuid4())))
    assert response.status_code == 403
    assert fake_oc.access_calls == []  # el permiso se evalúa antes del alcance


def test_operational_context_forbidden_and_unavailable(as_user, company, fake_catalog, fake_oc):
    fake_oc.access_forbidden = True
    response = _post(as_user("admin.test"), company, product_body(fake_catalog.add(uuid4())))
    assert response.status_code == 403
    assert code_of(response) == "OPERATIONAL_ACCESS_DENIED"

    fake_oc.access_forbidden = False
    fake_oc.access_unavailable = True
    response = _post(as_user("admin.test"), company, product_body(fake_catalog.add(uuid4())))
    assert response.status_code == 503
    assert response.json()["dependency"] == "operational-context"
