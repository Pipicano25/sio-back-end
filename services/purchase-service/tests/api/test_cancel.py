"""Anulación (Historia 3; FR-026 a FR-030; RC-03; T053)."""

from __future__ import annotations

from dataclasses import replace

from tests.conftest import base, count_rows, fetch, new_key, user_sub


def test_cancel_draft_is_local(world, fakes, make_draft, cancel, test_engine) -> None:
    fakes.inventory.availability.fail_if_called = True
    draft = make_draft()
    response = cancel(draft, reason="Pedido duplicado")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CANCELLED" and body["number"] is None and body["inventory_operation_id"] is None
    assert body["cancellation_reason"] == "Pedido duplicado"
    assert body["cancelled_by_user_id"] == str(fakes.oc.members[(user_sub("compras.test"), world.company)])
    [operation] = fetch(test_engine, "SELECT * FROM purchase_operations")
    assert (operation["operation_type"], operation["status"], operation["inventory_operation_id"]) == ("CANCEL", "SUCCEEDED", None)


def test_cancel_confirmed_reverses_exactly_its_entry(world, fakes, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    make_sequence()
    other = confirm(make_draft()).json()  # otra compra confirmada en la misma sucursal
    confirmed = confirm(make_draft()).json()
    response = cancel(confirmed, reason="Mercancía rechazada")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CANCELLED" and body["number"] == confirmed["number"]  # conserva el número
    assert body["inventory_operation_id"] == confirmed["inventory_operation_id"]

    reversal = fakes.inventory.by_id[fakes.inventory.by_key[next(k for k, v in fakes.inventory.by_key.items() if v.kind == "ENTRY_REVERSAL")].ref.id]
    assert str(reversal.ref.reverses_operation_id) == confirmed["inventory_operation_id"]  # reverso exacto
    operation = fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'CANCEL'")[0]
    assert reversal.payload["operation_key"] == str(operation["id"])
    assert reversal.payload["reason"] == "Mercancía rechazada"
    assert operation["inventory_operation_id"] == reversal.ref.id  # FR-049: id del reverso
    assert fakes.inventory.balance(world.branch, world.product) == 2  # solo queda la otra compra
    assert other["status"] == "CONFIRMED"


def test_consumed_inventory_is_409_and_stays_confirmed(world, fakes, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    make_sequence()
    confirmed = confirm(make_draft()).json()
    from uuid import UUID

    fakes.inventory.consumed.add(UUID(confirmed["inventory_operation_id"]))
    response = cancel(confirmed)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.INVENTORY_ALREADY_CONSUMED"
    assert fetch(test_engine, "SELECT status FROM purchases")[0]["status"] == "CONFIRMED"
    operation = fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'CANCEL'")[0]
    assert operation["status"] == "FAILED" and operation["error_code"] == "INVENTORY_ALREADY_CONSUMED"


def test_rejections(buyer, world, make_draft, cancel) -> None:
    draft = make_draft()
    response = buyer.post(
        f"{base(world)}/purchases/{draft['id']}/cancellation", json={"version": 1, "reason": "  "}, headers={"Idempotency-Key": new_key()}
    )
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "REASON_REQUIRED"
    cancelled = cancel(draft).json()
    again = cancel(cancelled)
    assert again.status_code == 409 and again.json()["code"] == "PURCHASE.INVALID_STATUS"


def test_inventory_unavailable_then_same_key_completes_once(world, fakes, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    make_sequence()
    confirmed = confirm(make_draft()).json()
    key = new_key()
    fakes.inventory.availability.down = True
    response = cancel(confirmed, key)
    assert response.status_code == 503 and response.json()["dependency"] == "inventory"
    assert fetch(test_engine, "SELECT status FROM purchases")[0]["status"] == "CONFIRMED"
    fakes.inventory.availability.down = False
    retried = cancel(confirmed, key, reason="otro motivo")  # la primera solicitud manda
    assert retried.status_code == 200 and retried.json()["cancellation_reason"] == "Error de registro"
    reversals = [item for item in fakes.inventory.by_key.values() if item.kind == "ENTRY_REVERSAL"]
    assert len(reversals) == 1
    assert cancel(confirmed, key).status_code == 200  # repetición idempotente


def test_cancellation_does_not_revalidate_references(world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    make_sequence()
    confirmed = confirm(make_draft()).json()
    fakes.cr.availability.fail_if_called = True
    fakes.catalog.availability.fail_if_called = True
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], status="INACTIVE")
    assert cancel(confirmed).status_code == 200


def test_cancellation_requires_assignment_and_delete_permission(as_user, world, fakes, make_draft, cancel, make_token, as_token) -> None:
    draft = make_draft()
    fakes.oc.assignments.discard((user_sub("compras.test"), world.branch))
    assert cancel(draft).status_code == 403
    sub = "sub-sin-delete"
    fakes.oc.add_member(sub, world.company, branches=(world.branch,))
    client = as_token(make_token("perm:purchase:purchases:update", "perm:purchase:purchases:read", sub=sub, preferred_username="x"))
    assert cancel(draft, client=client).status_code == 403


def test_cancellation_is_audited(world, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    make_sequence()
    cancel(confirm(make_draft()).json())
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox") if row["payload"]["action"] == "CANCEL_PURCHASE"]
    assert len(events) == 1 and events[0]["result"] == "SUCCESS" and events[0]["reason"] == "Error de registro"
    assert count_rows(test_engine, "purchase_operations", "operation_type = 'CANCEL' AND status = 'SUCCEEDED'") == 1
