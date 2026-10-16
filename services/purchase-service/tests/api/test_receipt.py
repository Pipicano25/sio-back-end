"""Recepción física completa (spec 020; FR-020-02 a FR-020-05; RC-MVP-1, RC-MVP-2; T009)."""

from __future__ import annotations

import threading
from dataclasses import replace
from decimal import Decimal

from tests.conftest import base, count_rows, fetch, line, new_key, user_sub


def confirmed_purchase(make_sequence, make_draft, confirm, *lines, **header) -> dict:
    make_sequence()
    response = confirm(make_draft(*lines, **header))
    assert response.status_code == 200, response.text
    return response.json()


def test_receipt_applies_the_entry_with_base_units_and_base_cost(world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    purchase = confirmed_purchase(
        make_sequence,
        make_draft,
        confirm,
        line(world.product, "2", "120000", company_product_presentation_id=world.presentation),
        line(world.product_2, "3", "1000", discount_amount="300"),
    )
    response = receive(purchase)
    assert response.status_code == 200, response.text
    received = response.json()
    assert received["status"] == "CONFIRMED" and received["receipt_status"] == "RECEIVED"
    receiver = fakes.oc.members[(user_sub("compras.test"), world.company)]
    assert received["received_by_user_id"] == str(receiver) and received["received_at"] is not None
    assert received["number"] == purchase["number"]  # la recepción no numera

    [entry] = fakes.inventory.entries()
    assert received["inventory_operation_id"] == str(entry.ref.id)
    payload = entry.payload
    assert payload["origin_type"] == "PURCHASE" and payload["origin_id"] == purchase["id"]
    assert payload["company_id"] == str(world.company) and payload["branch_id"] == str(world.branch)
    assert payload["application_user_id"] == str(receiver) and payload["reason"] is None
    first, second = payload["lines"]
    assert first == {
        "origin_detail_id": purchase["lines"][0]["id"],
        "company_product_id": str(world.product),
        "quantity": "24.0000",  # 2 cajas x 12 (factor de la presentación)
        "unit_cost": "10000.0000",  # (240000 − 0) / 24, sin el IVA de 45600 (DS-04)
    }
    assert second["quantity"] == "3.0000" and second["unit_cost"] == "900.0000"  # (3000 − 300) / 3
    assert fakes.inventory.balance(world.branch, world.product) == Decimal("24")


def test_receipt_operation_key_is_the_operation_id(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    key = new_key()
    receive(purchase, key)
    [operation] = fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'RECEIVE'")
    [entry] = fakes.inventory.entries()
    assert entry.payload["operation_key"] == str(operation["id"])
    assert entry.payload["correlation_id"] == str(operation["correlation_id"])
    assert operation["status"] == "SUCCEEDED" and operation["idempotency_key"] == key
    assert operation["inventory_operation_id"] == entry.ref.id and operation["completed_at"] is not None


def test_correlation_id_is_propagated(buyer, world, fakes, make_sequence, make_draft, confirm) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    correlation = "7d0c2e7a-6b38-4c0b-9e8b-2f1c0b6c9a11"
    buyer.post(
        f"{base(world)}/purchases/{purchase['id']}/receipt",
        json={"version": purchase["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": new_key(), "X-Correlation-Id": correlation},
    )
    assert fakes.inventory.entries()[0].payload["correlation_id"] == correlation


def test_full_receipt_must_be_confirmed_explicitly(buyer, world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    response = receive(purchase, full=False)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "FULL_RECEIPT_NOT_CONFIRMED"
    omitted = buyer.post(
        f"{base(world)}/purchases/{purchase['id']}/receipt",
        json={"version": purchase["version"]},
        headers={"Idempotency-Key": new_key()},
    )
    assert omitted.status_code == 422
    assert fakes.inventory.entries() == []
    assert count_rows(test_engine, "purchase_operations", "operation_type = 'RECEIVE'") == 0


def test_same_key_is_idempotent_and_another_key_is_already_received(world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    key = new_key()
    first = receive(purchase, key)
    for _ in range(3):
        again = receive(purchase, key)
        assert again.status_code == 200
        assert again.json()["inventory_operation_id"] == first.json()["inventory_operation_id"]
    assert len(fakes.inventory.entries()) == 1 and fakes.inventory.entry_calls == 1

    duplicate = receive(first.json(), new_key())
    assert duplicate.status_code == 409 and duplicate.json()["code"] == "PURCHASE.PURCHASE_ALREADY_RECEIVED"
    assert len(fakes.inventory.entries()) == 1


def test_receipt_requires_a_confirmed_purchase(world, fakes, make_sequence, make_draft, confirm, receive, cancel) -> None:
    make_sequence()
    draft = make_draft()
    response = receive(draft)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.INVALID_STATUS"
    cancelled = cancel(confirm(make_draft()).json()).json()
    response = receive(cancelled)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.INVALID_STATUS"
    assert fakes.inventory.entries() == []


def test_receipt_version_conflict_and_branch_access(world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    response = receive(purchase, version=purchase["version"] + 5)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.VERSION_CONFLICT"
    fakes.oc.assignments.discard((user_sub("compras.test"), world.branch))
    response = receive(purchase)
    assert response.status_code == 403 and response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"
    assert fakes.inventory.entries() == []


def test_definitive_inventory_rejection_keeps_the_purchase_pending(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    fakes.inventory.reject_entry = (422, "VALIDATION_ERROR")
    response = receive(purchase)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PURCHASE.INVENTORY_REJECTED" and body["details"]["inventory_code"] == "VALIDATION_ERROR"
    [operation] = fetch(test_engine, "SELECT status, error_code FROM purchase_operations WHERE operation_type = 'RECEIVE'")
    assert operation == {"status": "FAILED", "error_code": "INVENTORY_REJECTED"}
    assert fetch(test_engine, "SELECT status, inventory_operation_id, received_at FROM purchases")[0] == {
        "status": "CONFIRMED",
        "inventory_operation_id": None,
        "received_at": None,
    }
    fakes.inventory.reject_entry = None
    assert receive(purchase).status_code == 200  # con otra clave, una vez corregida la causa


def test_receipt_rechecks_the_operator(world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    user = fakes.oc.members[(user_sub("compras.test"), world.company)]
    fakes.oc.users[user] = replace(fakes.oc.users[user], status="INACTIVE")
    response = receive(purchase)
    assert response.status_code == 409 and response.json()["errors"][0]["code"] == "APPLICATION_USER_INACTIVE"
    assert fakes.inventory.entries() == []


def test_receipt_records_the_receiving_user(as_user, world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    """Quien confirma la recepción queda como `received_by_user_id` y como usuario de la entrada."""
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)  # creada y confirmada por compras.test
    received = receive(purchase, client=as_user("admin.test")).json()
    receiver = str(fakes.oc.members[(user_sub("admin.test"), world.company)])
    assert received["received_by_user_id"] == receiver
    assert fakes.inventory.entries()[0].payload["application_user_id"] == receiver


def test_two_keys_concurrently_apply_one_entry(test_client, user_token, world, fakes, make_sequence, make_draft, confirm) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    fakes.inventory.availability.latency = 0.3
    barrier = threading.Barrier(2)
    responses = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait(5)
        response = test_client.post(
            f"{base(world)}/purchases/{purchase['id']}/receipt",
            json={"version": purchase["version"], "full_receipt_confirmed": True},
            headers={"Authorization": f"Bearer {user_token('compras.test')}", "Idempotency-Key": new_key()},
        )
        with lock:
            responses.append(response)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert sorted(response.status_code for response in responses) == [200, 409], [r.text for r in responses]
    loser = next(response for response in responses if response.status_code == 409)
    assert loser.json()["code"] in {
        "PURCHASE.OPERATION_IN_PROGRESS",
        "PURCHASE.VERSION_CONFLICT",
        "PURCHASE.PURCHASE_ALREADY_RECEIVED",
    }
    assert len(fakes.inventory.entries()) == 1


def test_receipt_is_audited(world, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    purchase = confirmed_purchase(make_sequence, make_draft, confirm)
    received = receive(purchase).json()
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    [event] = [event for event in events if event["action"] == "RECEIVE_PURCHASE"]
    assert event["result"] == "SUCCESS"
    assert event["new_values"]["receipt_status"] == "RECEIVED"
    assert event["new_values"]["inventory_operation_id"] == received["inventory_operation_id"]
    assert event["new_values"]["received_by_user_id"] == received["received_by_user_id"]
