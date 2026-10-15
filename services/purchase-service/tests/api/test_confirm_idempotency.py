"""Idempotencia de confirmación (R-04; FR-022 a FR-024; RC-01; T045; spec 020: confirmación local, sin Inventory)."""

from __future__ import annotations

from tests.conftest import base, count_rows, fetch, line, new_key
from tests.fakes import build_methods


def test_same_key_returns_same_result_without_second_entry(world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    first = confirm(draft, key)
    for _ in range(5):
        again = confirm(draft, key)
        assert again.status_code == 200
        assert again.json()["number"] == first.json()["number"]
        assert again.json()["receipt_status"] == "PENDING"
    assert fakes.inventory.entries() == [] and fakes.inventory.entry_calls == 0


def test_rejected_confirmation_leaves_no_operation_and_the_key_can_be_reused(buyer, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """Spec 020: un rechazo de validación no registra operación ni consume la clave ni el número."""
    from dataclasses import replace

    make_sequence()
    draft = make_draft()
    key = new_key()
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], status="INACTIVE")
    first = confirm(draft, key)
    assert first.status_code == 409 and first.json()["errors"][0]["code"] == "PRODUCT_INACTIVE"
    assert count_rows(test_engine, "purchase_operations") == 0
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], status="ACTIVE")
    assert confirm(draft, key).status_code == 200


def test_key_conflicts(buyer, as_user, world, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    first, second = make_draft(), make_draft()
    key = new_key()
    assert confirm(first, key).status_code == 200
    other_purchase = confirm(second, key)
    assert other_purchase.status_code == 409 and other_purchase.json()["code"] == "PURCHASE.IDEMPOTENCY_KEY_CONFLICT"
    assert "number" not in other_purchase.text
    other_type = cancel(first, key, version=2)
    assert other_type.status_code == 409 and other_type.json()["code"] == "PURCHASE.IDEMPOTENCY_KEY_CONFLICT"
    other_identity = confirm(first, key, client=as_user("admin.test"))
    assert other_identity.status_code == 409 and other_identity.json()["code"] == "PURCHASE.IDEMPOTENCY_KEY_CONFLICT"


def test_confirmed_purchase_rejects_another_confirmation_and_edits(buyer, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    other = confirm(confirmed)  # otra clave
    assert other.status_code == 409 and other.json()["code"] == "PURCHASE.INVALID_STATUS"
    edit = buyer.post(f"{base(world)}/purchases/{draft['id']}/details", json={**line(world.product_2), "version": confirmed["version"]})
    assert edit.status_code == 409 and edit.json()["code"] == "PURCHASE.INVALID_STATUS"
    assert count_rows(test_engine, "purchase_operations", "status = 'PENDING'") == 0


def test_operations_listing_hides_the_key(buyer, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    confirm(draft, key)
    operations = buyer.get(f"{base(world)}/purchases/{draft['id']}/operations").json()
    assert len(operations) == 1 and operations[0]["status"] == "SUCCEEDED"
    assert key not in str(operations) and "idempotency_key" not in operations[0]
    single = buyer.get(f"{base(world)}/purchase-operations/{operations[0]['id']}")
    assert single.status_code == 200 and single.json()["operation_type"] == "CONFIRM"


def test_invalid_key_format(buyer, world, make_draft) -> None:
    draft = make_draft()
    for key in ("con espacio", "x" * 151):
        response = buyer.post(
            f"{base(world)}/purchases/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": key}
        )
        assert response.status_code == 422, key


def test_number_not_consumed_by_failures(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    first, second, third = make_draft(), make_draft(), make_draft()
    fakes.oc.availability.down = True
    assert confirm(first).status_code == 503
    fakes.oc.availability.down = False
    fakes.pr.methods.clear()
    assert confirm(second).status_code == 422
    fakes.pr.methods = build_methods(world)
    assert confirm(third).json()["number"] == "CP-000001"
    assert fetch(test_engine, "SELECT current_number FROM purchase_sequence_counters")[0]["current_number"] == 1
