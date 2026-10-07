"""Confirmación (Historia 2; FR-015 a FR-021; DS-02, DS-04; RC-03; T044)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from tests.conftest import base, count_rows, fetch, line, new_key, user_sub


def test_confirmation_applies_entry_and_assigns_number(buyer, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence(reset_policy="MONTHLY")
    draft = make_draft(
        line(world.product, "2", "120000", company_product_presentation_id=world.presentation, tax_amount="45600"),
        line(world.product_2, "3", "1000", discount_amount="300"),
        supplier_payment_condition_id=world.condition,
    )
    response = confirm(draft)
    assert response.status_code == 200, response.text
    purchase = response.json()
    period = date.fromisoformat(draft["operation_date"]).strftime("%Y%m")
    assert purchase["status"] == "CONFIRMED"
    assert purchase["number"] == f"CP-{period}-000001" and purchase["sequence_value"] == 1
    assert purchase["purchase_sequence_id"] is not None
    assert purchase["due_date"] == (date.fromisoformat(draft["operation_date"]) + timedelta(days=30)).isoformat()
    assert purchase["pending_operation_id"] is None

    [entry] = fakes.inventory.entries()
    assert purchase["inventory_operation_id"] == str(entry.ref.id)
    payload = entry.payload
    assert payload["origin_type"] == "PURCHASE" and payload["origin_id"] == draft["id"]
    assert payload["company_id"] == str(world.company) and payload["branch_id"] == str(world.branch)
    assert payload["application_user_id"] == str(fakes.oc.members[(user_sub("compras.test"), world.company)])
    assert payload["reason"] is None
    first, second = payload["lines"]
    assert first == {
        "origin_detail_id": draft["lines"][0]["id"],
        "company_product_id": str(world.product),
        "quantity": "24.0000",
        "unit_cost": "10000.0000",  # (240000 − 0) / 24, sin el IVA de 45600 (DS-04)
    }
    assert second["quantity"] == "3.0000" and second["unit_cost"] == "900.0000"  # (3000 − 300) / 3
    assert fakes.inventory.balance(world.branch, world.product) == Decimal("24")


def test_operation_key_is_the_operation_id(buyer, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    confirm(draft, key)
    [operation] = fetch(test_engine, "SELECT * FROM purchase_operations")
    [entry] = fakes.inventory.entries()
    assert entry.payload["operation_key"] == str(operation["id"])
    assert entry.payload["correlation_id"] == str(operation["correlation_id"])
    assert operation["status"] == "SUCCEEDED" and operation["idempotency_key"] == key
    assert operation["inventory_operation_id"] == entry.ref.id
    assert operation["created_by"] == user_sub("compras.test") and operation["completed_at"] is not None


def test_correlation_id_is_propagated(buyer, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    correlation = "7d0c2e7a-6b38-4c0b-9e8b-2f1c0b6c9a11"
    buyer.post(
        f"{base(world)}/purchases/{draft['id']}/confirmation",
        json={"version": 1},
        headers={"Idempotency-Key": new_key(), "X-Correlation-Id": correlation},
    )
    assert fakes.inventory.entries()[0].payload["correlation_id"] == correlation


def test_snapshots_are_refreshed_and_frozen(buyer, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], display_name="Nuevo nombre ficticio")
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], display_name="Arroz renombrado")
    confirmed = confirm(draft).json()
    assert confirmed["supplier_name_snapshot"] == "Nuevo nombre ficticio"
    assert confirmed["lines"][0]["product_name_snapshot"] == "Arroz renombrado"
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], display_name="Otro nombre")
    again = buyer.get(f"{base(world)}/purchases/{draft['id']}").json()
    assert again["supplier_name_snapshot"] == "Nuevo nombre ficticio"  # congelado (DS-02)


def test_requires_key_lines_and_version(buyer, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    empty = buyer.post(f"{base(world)}/purchases", json={"branch_id": str(world.branch), "company_supplier_id": str(world.supplier), "operation_date": date.today().isoformat()}).json()
    response = buyer.post(f"{base(world)}/purchases/{empty['id']}/confirmation", json={"version": 1})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    response = confirm(empty)
    assert response.status_code == 422 and response.json()["code"] == "PURCHASE.PURCHASE_WITHOUT_LINES"
    draft = make_draft()
    response = confirm(draft, version=7)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.VERSION_CONFLICT"


def test_reference_no_longer_fit_rejects_without_effects(buyer, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(line(world.product), line(world.product_2))
    fakes.cr.products[world.product_2] = replace(fakes.cr.products[world.product_2], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PURCHASE.REFERENCES_NOT_ELIGIBLE"
    assert body["errors"][0]["code"] == "PRODUCT_INACTIVE" and body["errors"][0]["line_number"] == 2
    assert fakes.inventory.entries() == []
    assert count_rows(test_engine, "purchase_operations") == 0
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["status"] == "DRAFT"


def test_without_sequence_rejects_before_inventory(world, fakes, make_draft, confirm, test_engine) -> None:
    fakes.inventory.availability.fail_if_called = True
    draft = make_draft()
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_NOT_CONFIGURED"
    assert count_rows(test_engine, "purchase_operations") == 0


def test_exhausted_sequence_rejects_before_inventory(world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence(maximum_number=1)
    assert confirm(make_draft()).status_code == 200
    fakes.inventory.availability.fail_if_called = True
    response = confirm(make_draft())
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_EXHAUSTED"


def test_definitive_inventory_rejection_fails_operation(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.reject_entry = (422, "VALIDATION_ERROR")
    response = confirm(draft)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PURCHASE.INVENTORY_REJECTED" and body["details"]["inventory_code"] == "VALIDATION_ERROR"
    [operation] = fetch(test_engine, "SELECT status, error_code FROM purchase_operations")
    assert operation == {"status": "FAILED", "error_code": "INVENTORY_REJECTED"}
    purchase = fetch(test_engine, "SELECT status, number FROM purchases")[0]
    assert purchase == {"status": "DRAFT", "number": None}
    assert count_rows(test_engine, "purchase_sequence_counters") == 0  # no consume número


def test_inactive_operator_is_409(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    user = fakes.oc.members[(user_sub("compras.test"), world.company)]
    fakes.oc.users[user] = replace(fakes.oc.users[user], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    assert response.json()["errors"][0]["code"] == "APPLICATION_USER_INACTIVE"


def test_confirmation_requires_branch_assignment(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.oc.assignments.discard((user_sub("compras.test"), world.branch))
    response = confirm(draft)
    assert response.status_code == 403 and response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"


def test_confirmation_is_audited(world, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    confirm_event = [event for event in events if event["action"] == "CONFIRM_PURCHASE"]
    assert len(confirm_event) == 1
    assert confirm_event[0]["result"] == "SUCCESS"
    assert confirm_event[0]["new_values"]["number"] == confirmed["number"]
    assert confirm_event[0]["new_values"]["inventory_operation_id"] == confirmed["inventory_operation_id"]
