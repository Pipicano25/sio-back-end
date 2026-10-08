"""Eventos de clientes y proveedores de empresa (feature 016; acciones CR 5–14; T036)."""

from __future__ import annotations

import pytest

from tests.api.helpers import person_customer, supplier
from tests.contract.test_audit_events_products import check


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def _customer_body(current: dict, **changes) -> dict:
    body = {key: current[key] for key in ("internal_code", "display_name", "preferred_contact_person_id", "version")}
    body.update(changes)
    return body


def test_customer_lifecycle(admin, company, fake_party, outbox, clear_outbox) -> None:
    customer = person_customer(admin, company, fake_party)
    url = f"/api/v1/company-customers/{customer['id']}"
    updated = admin.put(url, json=_customer_body(customer, display_name="Cliente renombrado"))
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert admin.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert admin.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    create, update, deactivate, reactivate = outbox()
    for event, action in zip(
        (create, update, deactivate, reactivate),
        ("CREATE_COMPANY_CUSTOMER", "UPDATE_COMPANY_CUSTOMER", "DEACTIVATE_COMPANY_CUSTOMER", "REACTIVATE_COMPANY_CUSTOMER"),
        strict=True,
    ):
        check(event, action, "CompanyCustomer", customer["id"], company)
    assert create["new_values"]["customer_kind"] == "PERSON"
    assert create["new_values"]["person_identity_id"] == customer["person_identity_id"]
    assert update["new_values"] == {"display_name": "Cliente renombrado"}
    assert deactivate["new_values"] == {"status": "INACTIVE"} and reactivate["new_values"] == {"status": "ACTIVE"}


def test_supplier_lifecycle_with_block_reason(admin, company, fake_party, outbox, clear_outbox) -> None:
    provider = supplier(admin, company, fake_party)
    url = f"/api/v1/company-suppliers/{provider['id']}"
    body = {key: provider[key] for key in ("internal_code", "display_name", "version")}
    updated = admin.put(url, json={**body, "display_name": "Proveedor renombrado"})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    blocked = admin.post(f"{url}/block", json={"version": version, "block_reason": "Incumplimiento de entregas"})
    assert blocked.status_code == 200, blocked.text
    unblocked = admin.post(f"{url}/unblock", json={"version": version + 1})
    assert unblocked.status_code == 200, unblocked.text
    assert admin.post(f"{url}/deactivate", json={"version": version + 2}).status_code == 200
    assert admin.post(f"{url}/reactivate", json={"version": version + 3}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_COMPANY_SUPPLIER", "UPDATE_COMPANY_SUPPLIER", "BLOCK_COMPANY_SUPPLIER",
        "UNBLOCK_COMPANY_SUPPLIER", "DEACTIVATE_COMPANY_SUPPLIER", "REACTIVATE_COMPANY_SUPPLIER",
    ]
    for event in events:
        check(event, event["action"], "CompanySupplier", provider["id"], company)
    block = events[2]
    assert block["previous_values"] == {"status": "ACTIVE", "block_reason": None}
    assert block["new_values"] == {"status": "BLOCKED", "block_reason": "Incumplimiento de entregas"}
    assert block["reason"] == "Incumplimiento de entregas"
    assert events[3]["new_values"] == {"status": "ACTIVE", "block_reason": None}
