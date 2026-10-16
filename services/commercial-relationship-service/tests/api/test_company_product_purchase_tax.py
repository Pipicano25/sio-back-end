"""Historia 4 de la spec 021 (CR): tasa de impuesto de compra del producto de la empresa (T025, T026; FR-021-07, 08).

CP-32 (0 % explícito), CP-62 (rango y decimales), CP-T14 (lote todo o nada, versión, `null`). Datos ficticios: el
19 % no representa una tarifa real.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import adopt, code_of

ONE = "/api/v1/company-products/{id}/purchase-tax"
BATCH = "/api/v1/companies/{company}/company-products/purchase-taxes/batch"
TAX_PERMISSION = "perm:commercial-relationship:company_product_purchase_taxes:update"


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


def test_new_product_has_tax_not_configured(supervisor, company, fake_catalog) -> None:
    product = adopt(supervisor, company, fake_catalog)
    assert product["purchase_tax_percentage"] is None  # sin configurar ≠ 0 %
    fetched = supervisor.get(f"/api/v1/company-products/{product['id']}").json()
    assert fetched["purchase_tax_percentage"] is None


@pytest.mark.parametrize(("value", "expected"), [("0", "0.0000"), ("19", "19.0000"), ("100", "100.0000"), ("12.3456", "12.3456")])
def test_cp32_configure_one_product(supervisor, company, fake_catalog, value, expected) -> None:
    product = adopt(supervisor, company, fake_catalog)
    response = supervisor.put(ONE.format(id=product["id"]), json={"version": product["version"], "purchase_tax_percentage": value})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["purchase_tax_percentage"] == expected and body["version"] == product["version"] + 1


@pytest.mark.parametrize("value", ["-0.0001", "100.0001", "19.00001", "abc", True])
def test_cp62_out_of_range_or_scale(supervisor, company, fake_catalog, value) -> None:
    product = adopt(supervisor, company, fake_catalog)
    response = supervisor.put(ONE.format(id=product["id"]), json={"version": product["version"], "purchase_tax_percentage": value})
    assert response.status_code == 422 and code_of(response) == "TAX_PERCENTAGE_OUT_OF_RANGE", response.text


def test_null_is_rejected_and_same_value_does_not_bump_version(supervisor, company, fake_catalog) -> None:
    product = adopt(supervisor, company, fake_catalog)
    url = ONE.format(id=product["id"])
    assert code_of(supervisor.put(url, json={"version": 1, "purchase_tax_percentage": None})) == "PURCHASE_TAX_REQUIRED"
    configured = supervisor.put(url, json={"version": 1, "purchase_tax_percentage": "19"}).json()
    same = supervisor.put(url, json={"version": configured["version"], "purchase_tax_percentage": "19.00"})
    assert same.status_code == 200 and same.json()["version"] == configured["version"]
    stale = supervisor.put(url, json={"version": 1, "purchase_tax_percentage": "5"})
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"


def test_product_put_does_not_change_the_tax(supervisor, company, fake_catalog) -> None:
    """El `PUT` general del producto no admite la tasa: tiene su propio permiso (M-5)."""
    product = adopt(supervisor, company, fake_catalog)
    body = {key: product[key] for key in (
        "internal_code", "reference_code", "display_name", "short_name", "currency_code", "inventory_control_enabled",
        "lot_tracking_enabled", "expiration_tracking_enabled", "is_purchasable", "is_sellable", "version",
    )}
    response = supervisor.put(f"/api/v1/company-products/{product['id']}", json={**body, "purchase_tax_percentage": "19"})
    assert response.status_code == 422


def test_cpt14_batch_is_all_or_nothing(supervisor, company, fake_catalog) -> None:
    products = [adopt(supervisor, company, fake_catalog, internal_code=f"TAX-{index}") for index in range(3)]
    items = [{"company_product_id": p["id"], "version": p["version"], "purchase_tax_percentage": tax}
             for p, tax in zip(products, ("0", "19", "5"))]

    stale = [*items[:2], {**items[2], "version": 99}]
    response = supervisor.post(BATCH.format(company=company), json={"items": stale})
    assert response.status_code == 409 and code_of(response) == "VERSION_CONFLICT"
    assert all(supervisor.get(f"/api/v1/company-products/{p['id']}").json()["purchase_tax_percentage"] is None for p in products)

    invalid = [*items[:2], {**items[2], "purchase_tax_percentage": "101"}]
    response = supervisor.post(BATCH.format(company=company), json={"items": invalid})
    assert response.status_code == 422 and code_of(response) == "TAX_PERCENTAGE_OUT_OF_RANGE"
    assert response.json()["errors"][0]["field"] == "items[2].purchase_tax_percentage"

    response = supervisor.post(BATCH.format(company=company), json={"items": items})
    assert response.status_code == 200, response.text
    assert [item["purchase_tax_percentage"] for item in response.json()["items"]] == ["0.0000", "19.0000", "5.0000"]


def test_batch_limits_and_ownership(supervisor, as_user, company, other_company, fake_catalog, fake_oc) -> None:
    from tests.conftest import user_sub

    product = adopt(supervisor, company, fake_catalog)
    item = {"company_product_id": product["id"], "version": 1, "purchase_tax_percentage": "19"}
    assert supervisor.post(BATCH.format(company=company), json={"items": []}).status_code == 422
    too_many = [{**item, "company_product_id": str(uuid4())} for _ in range(101)]
    assert supervisor.post(BATCH.format(company=company), json={"items": too_many}).status_code == 422
    repeated = supervisor.post(BATCH.format(company=company), json={"items": [item, item]})
    assert repeated.status_code == 422

    admin = as_user("admin.test")
    fake_oc.add_member(user_sub("admin.test"), other_company)
    response = admin.post(BATCH.format(company=other_company), json={"items": [item]})  # producto de otra empresa
    assert response.status_code == 422 and code_of(response) == "COMPANY_PRODUCT_NOT_FOUND"


@pytest.mark.parametrize("username", ["compras.test", "ventas.test", "consulta.test", "reportes.test", "inventario.test"])
def test_only_admins_and_supervisors_configure_the_tax(as_user, supervisor, company, fake_catalog, username) -> None:
    product = adopt(supervisor, company, fake_catalog)
    client = as_user(username)
    assert client.put(ONE.format(id=product["id"]), json={"version": 1, "purchase_tax_percentage": "19"}).status_code == 403
    batch = {"items": [{"company_product_id": product["id"], "version": 1, "purchase_tax_percentage": "19"}]}
    assert client.post(BATCH.format(company=company), json=batch).status_code == 403


def test_audit_event(supervisor, company, fake_catalog, outbox, clear_outbox) -> None:
    product = adopt(supervisor, company, fake_catalog)
    clear_outbox()
    supervisor.put(ONE.format(id=product["id"]), json={"version": 1, "purchase_tax_percentage": "19"})
    (event,) = outbox()
    assert event["action"] == "UPDATE_COMPANY_PRODUCT_PURCHASE_TAX" and event["entity_type"] == "CompanyProduct"
    assert event["previous_values"] == {"purchase_tax_percentage": None}
    assert event["new_values"] == {"purchase_tax_percentage": "19.0000"}


def test_cr_batch_lookup_exposes_the_tax(supervisor, as_token, service_token, company, fake_catalog) -> None:
    """T026: el `batch-lookup` técnico que usa Purchase incluye la tasa (cambio aditivo)."""
    product = adopt(supervisor, company, fake_catalog)
    supervisor.put(ONE.format(id=product["id"]), json={"version": 1, "purchase_tax_percentage": "19"})
    technical = as_token(service_token(
        "perm:commercial-relationship:company_products:read", "perm:commercial-relationship:platform:lookup",
        client_id="purchase-service",
    ))
    response = technical.post("/api/v1/company-products/batch-lookup", json={"ids": [product["id"], str(uuid4())]})
    assert response.status_code == 200, response.text
    found, missing = response.json()["items"]
    assert found["purchase_tax_percentage"] == "19.0000" and found["found"] is True
    assert missing["found"] is False and missing.get("purchase_tax_percentage") is None
