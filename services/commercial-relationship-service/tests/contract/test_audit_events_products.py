"""Eventos de productos y presentaciones de empresa (feature 016; acciones CR 1–4 y 15–18; T035)."""

from __future__ import annotations

import pytest

from tests.api.helpers import adopt, adopt_presentation, presentation_update_body, product_update_body

TECHNICAL = {"id", "version", "created_at", "created_by", "updated_at", "updated_by"}


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def check(event: dict, action: str, entity_type: str, entity_id: str, company) -> None:
    assert event["action"] == action and event["entity_type"] == entity_type
    assert event["entity_id"] == entity_id and event["company_id"] == str(company)
    assert event["result"] == "SUCCESS" and event["branch_id"] is None
    assert event["username_snapshot"] == "admin.test"
    assert event["redacted_paths"] == []


def test_adopt_update_deactivate_reactivate_company_product(admin, company, fake_catalog, outbox, clear_outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    created = outbox()[-1]
    check(created, "ADOPT_COMPANY_PRODUCT", "CompanyProduct", product["id"], company)
    assert created["previous_values"] is None
    assert created["new_values"]["internal_code"] == product["internal_code"]
    assert created["new_values"]["global_product_id"] == product["global_product_id"]
    assert not set(created["new_values"]) & TECHNICAL

    clear_outbox()
    url = f"/api/v1/company-products/{product['id']}"
    updated = admin.put(url, json=product_update_body(product, display_name="Nombre comercial nuevo"))
    assert updated.status_code == 200, updated.text
    identical = admin.put(url, json=product_update_body(updated.json()))
    assert identical.status_code == 200
    version = updated.json()["version"]
    assert admin.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert admin.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    update, deactivate, reactivate = outbox()  # el PUT idéntico no registra evento (DS-05)
    check(update, "UPDATE_COMPANY_PRODUCT", "CompanyProduct", product["id"], company)
    assert update["previous_values"] == {"display_name": product["display_name"]}
    assert update["new_values"] == {"display_name": "Nombre comercial nuevo"}
    check(deactivate, "DEACTIVATE_COMPANY_PRODUCT", "CompanyProduct", product["id"], company)
    assert deactivate["previous_values"] == {"status": "ACTIVE"} and deactivate["new_values"] == {"status": "INACTIVE"}
    check(reactivate, "REACTIVATE_COMPANY_PRODUCT", "CompanyProduct", product["id"], company)


def test_company_product_presentation_lifecycle(admin, company, fake_catalog, outbox, clear_outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    clear_outbox()
    presentation = adopt_presentation(admin, company, fake_catalog, product)
    url = f"/api/v1/company-product-presentations/{presentation['id']}"
    updated = admin.put(url, json=presentation_update_body(presentation, internal_code="CAJA-12-NUEVA"))
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert admin.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert admin.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_COMPANY_PRODUCT_PRESENTATION", "UPDATE_COMPANY_PRODUCT_PRESENTATION",
        "DEACTIVATE_COMPANY_PRODUCT_PRESENTATION", "REACTIVATE_COMPANY_PRODUCT_PRESENTATION",
    ]
    for event in events:
        check(event, event["action"], "CompanyProductPresentation", presentation["id"], company)
    assert events[0]["new_values"]["company_product_id"] == product["id"]
    assert events[1]["previous_values"] == {"internal_code": presentation["internal_code"]}
    assert events[1]["new_values"] == {"internal_code": "CAJA-12-NUEVA"}
