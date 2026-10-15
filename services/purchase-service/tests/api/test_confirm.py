"""Confirmación local (Historia 2; FR-015 a FR-021; DS-02; spec 020 FR-020-01, RC-MVP-1; T044, T008)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from tests.conftest import base, count_rows, fetch, line, new_key, user_sub


def test_confirmation_assigns_number_without_moving_inventory(buyer, world, fakes, make_sequence, make_draft, confirm) -> None:
    """Spec 020: confirmar no crea existencias; la compra queda pendiente de recepción."""
    make_sequence(reset_policy="MONTHLY")
    draft = make_draft(
        line(world.product, "2", "120000", company_product_presentation_id=world.presentation, tax_amount="45600"),
        line(world.product_2, "3", "1000", discount_amount="300"),
        supplier_payment_condition_id=world.condition,
    )
    fakes.inventory.availability.fail_if_called = True
    response = confirm(draft)
    assert response.status_code == 200, response.text
    purchase = response.json()
    period = date.fromisoformat(draft["operation_date"]).strftime("%Y%m")
    assert purchase["status"] == "CONFIRMED"
    assert purchase["number"] == f"CP-{period}-000001" and purchase["sequence_value"] == 1
    assert purchase["purchase_sequence_id"] is not None
    assert purchase["payment_condition_code_snapshot"] == "CASH" and purchase["due_date"] == draft["operation_date"]
    assert purchase["payment_method_code_snapshot"] == "CASH" and purchase["payment_method_name_snapshot"] == "Efectivo"
    assert purchase["receipt_status"] == "PENDING"
    assert purchase["inventory_operation_id"] is None and purchase["received_at"] is None
    assert purchase["pending_operation_id"] is None
    assert fakes.inventory.entries() == []
    assert fakes.inventory.balance(world.branch, world.product) == 0


def test_confirm_operation_is_local_and_succeeded(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    key = new_key()
    confirm(make_draft(), key)
    [operation] = fetch(test_engine, "SELECT * FROM purchase_operations")
    assert operation["operation_type"] == "CONFIRM" and operation["status"] == "SUCCEEDED"
    assert operation["idempotency_key"] == key and operation["inventory_operation_id"] is None
    assert operation["created_by"] == user_sub("compras.test") and operation["completed_at"] is not None
    assert fakes.inventory.entries() == []


def test_snapshots_are_refreshed_and_frozen(buyer, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], display_name="Nuevo nombre ficticio")
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], display_name="Arroz renombrado")
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], name="Efectivo (caja)")
    confirmed = confirm(draft).json()
    assert confirmed["supplier_name_snapshot"] == "Nuevo nombre ficticio"
    assert confirmed["lines"][0]["product_name_snapshot"] == "Arroz renombrado"
    assert confirmed["payment_method_name_snapshot"] == "Efectivo (caja)"
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], display_name="Otro nombre")
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], name="Otro", status="INACTIVE")
    again = buyer.get(f"{base(world)}/purchases/{draft['id']}").json()
    assert again["supplier_name_snapshot"] == "Nuevo nombre ficticio"  # congelado (DS-02)
    assert again["payment_method_name_snapshot"] == "Efectivo (caja)"  # congelado (spec 020, RC-MVP-4)


def test_requires_key_lines_and_version(buyer, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    empty = buyer.post(
        f"{base(world)}/purchases",
        json={
            "branch_id": str(world.branch),
            "company_supplier_id": str(world.supplier),
            "operation_date": date.today().isoformat(),
            "payment_method_id": str(world.payment_method),
        },
    ).json()
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
    assert count_rows(test_engine, "purchase_operations") == 0
    assert count_rows(test_engine, "purchase_sequence_counters") == 0
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["status"] == "DRAFT"


def test_payment_method_inactive_at_confirmation_is_409(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """Spec 020 (FR-020-09): el medio de pago se revalida al confirmar."""
    make_sequence()
    draft = make_draft()
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    assert response.json()["errors"][0]["code"] == "PAYMENT_METHOD_INACTIVE"
    assert count_rows(test_engine, "purchase_operations") == 0


def test_without_sequence_rejects_without_effects(world, fakes, make_draft, confirm, test_engine) -> None:
    draft = make_draft()
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_NOT_CONFIGURED"
    assert count_rows(test_engine, "purchase_operations") == 0


def test_exhausted_sequence_rejects_without_consuming_or_compensating(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """Spec 020 (DS-03): la numeración ocurre antes de cualquier movimiento; no hay nada que compensar."""
    make_sequence(maximum_number=1)
    assert confirm(make_draft()).status_code == 200
    second = make_draft()
    response = confirm(second)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_EXHAUSTED"
    assert fetch(test_engine, "SELECT status, number FROM purchases WHERE id = :p", p=second["id"])[0] == {"status": "DRAFT", "number": None}
    assert fetch(test_engine, "SELECT current_number FROM purchase_sequence_counters")[0]["current_number"] == 1
    assert fakes.inventory.entries() == []


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
    values = confirm_event[0]["new_values"]
    assert values["number"] == confirmed["number"] and values["receipt_status"] == "PENDING"
    assert values["payment_method_id"] == str(world.payment_method)
    assert "inventory_operation_id" not in values
