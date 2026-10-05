"""Historia 3 de la 010: condiciones de pago del proveedor (T042; FR-030 a FR-038; I1; RC-15)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import code_of, condition_update_body, create_condition, supplier

URL = "/api/v1/companies/{company}/supplier-payment-conditions"


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def provider(admin, company, fake_party):
    return supplier(admin, company, fake_party)


def _body(provider, fake_payment, code="CREDIT", **overrides):
    return {
        "company_supplier_id": provider["id"],
        "payment_condition_type_id": str(fake_payment.id_of(code)),
        "currency_code": "COP",
        "payment_terms_days": 0 if code == "CASH" else 30,
        **overrides,
    }


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def test_scenario_1_credit_condition(admin, company, provider, fake_payment):
    response = _post(admin, company, _body(provider, fake_payment, credit_limit="5000000.00"))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE" and body["valid_from"] is not None and body["valid_to"] is None
    assert body["credit_limit"] == "5000000.00"
    # La respuesta no copia el código ni el nombre del tipo (Principio III, RC-15).
    assert "code" not in body and "name" not in body and "payment_condition_type_code" not in body


@pytest.mark.parametrize(("code", "days"), [("CASH", 15), ("CREDIT", 0), ("FINANCING", 0)])
def test_scenarios_2_and_3_terms_vs_type(admin, company, provider, fake_payment, code, days):
    response = _post(admin, company, _body(provider, fake_payment, code=code, payment_terms_days=days))
    assert response.status_code == 422 and code_of(response) == "PAYMENT_TERMS_INCONSISTENT"


def test_scenario_4_type_not_found_or_inactive(admin, company, provider, fake_payment):
    response = _post(admin, company, _body(provider, fake_payment, payment_condition_type_id=str(uuid4())))
    assert response.status_code == 422 and code_of(response) == "PAYMENT_CONDITION_TYPE_NOT_FOUND"

    inactive = fake_payment.add("CREDIT", status="INACTIVE")
    response = _post(admin, company, _body(provider, fake_payment, payment_condition_type_id=str(inactive)))
    assert response.status_code == 422 and code_of(response) == "PAYMENT_CONDITION_TYPE_INACTIVE"


def test_scenario_5_payment_reference_unavailable(admin, company, provider, fake_payment):
    fake_payment.unavailable = True
    response = _post(admin, company, _body(provider, fake_payment))
    assert response.status_code == 503 and response.json()["dependency"] == "payment-reference"
    assert admin.get(URL.format(company=company), params={"status": "ALL"}).json()["total_records"] == 0


def test_scenarios_6_and_7_default_per_currency(admin, company, provider, fake_payment):
    first = create_condition(admin, company, provider, fake_payment, is_default=True)
    create_condition(admin, company, provider, fake_payment, is_default=False)
    usd = create_condition(admin, company, provider, fake_payment, currency_code="USD", is_default=True)
    second = create_condition(admin, company, provider, fake_payment, is_default=True)

    assert admin.get(f"/api/v1/supplier-payment-conditions/{first['id']}").json()["is_default"] is False
    assert admin.get(f"/api/v1/supplier-payment-conditions/{usd['id']}").json()["is_default"] is True
    assert second["is_default"] is True


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"valid_from": "2026-10-05T00:00:00Z", "valid_to": "2026-10-05T00:00:00Z"}, "VALIDITY_INVALID"),
        ({"credit_limit": "-1"}, "VALIDATION_ERROR"),
        ({"interest_rate_percentage": "100.5"}, "VALIDATION_ERROR"),
        ({"cash_discount_percentage": "-0.1"}, "VALIDATION_ERROR"),
        ({"credit_limit": "1500.5", "currency_code": "CLP"}, "PRICE_SCALE_NOT_ALLOWED"),
        ({"valid_from": "2026-10-05T00:00:00"}, "VALIDATION_ERROR"),  # sin zona horaria
        ({"currency_code": "ZAR"}, "CURRENCY_NOT_SUPPORTED"),
    ],
)
def test_scenario_8_invalid_values(admin, company, provider, fake_payment, overrides, code):
    response = _post(admin, company, _body(provider, fake_payment, **overrides))
    assert response.status_code == 422 and code_of(response) == code


@pytest.mark.parametrize(("action", "code"), [("block", "COMPANY_SUPPLIER_BLOCKED"), ("deactivate", "COMPANY_SUPPLIER_INACTIVE")])
def test_scenario_9_fr_031_unchanged(admin, company, provider, fake_payment, action, code):
    body = {"version": 1, "block_reason": "Incumplimiento"} if action == "block" else {"version": 1}
    admin.post(f"/api/v1/company-suppliers/{provider['id']}/{action}", json=body)
    response = _post(admin, company, _body(provider, fake_payment))
    assert response.status_code == 422 and code_of(response) == code


def test_put_and_applicable_at(admin, company, provider, fake_payment):
    future = create_condition(admin, company, provider, fake_payment, valid_from="2030-01-01T00:00:00Z")
    current = create_condition(admin, company, provider, fake_payment, valid_from="2026-01-01T00:00:00Z", valid_to="2029-01-01T00:00:00Z")
    url = URL.format(company=company)

    applicable = admin.get(url, params={"applicable_at": "2027-06-01T00:00:00Z"}).json()
    assert [row["id"] for row in applicable["items"]] == [current["id"]]
    assert admin.get(url, params={"applicable_at": "2027-06-01T00:00:00"}).status_code == 422

    response = admin.put(f"/api/v1/supplier-payment-conditions/{future['id']}",
                         json={**condition_update_body(future), "company_supplier_id": str(uuid4())})
    assert response.status_code == 422 and code_of(response) == "IMMUTABLE_FIELD"

    updated = admin.put(f"/api/v1/supplier-payment-conditions/{future['id']}",
                        json=condition_update_body(future, payment_terms_days=60))
    assert updated.status_code == 200 and updated.json()["payment_terms_days"] == 60


def test_readers_and_permissions(as_user, admin, company, provider, fake_payment):
    created = create_condition(admin, company, provider, fake_payment)
    url = f"/api/v1/supplier-payment-conditions/{created['id']}"

    assert as_user("reportes.test").get(url).status_code == 200
    assert as_user("ventas.test").put(url, json=condition_update_body(created)).status_code == 403
    assert as_user("supervisor.test").post(url + "/deactivate", json={"version": 1}).status_code == 403
    assert as_user("inventario.test").get(URL.format(company=company)).status_code == 403
