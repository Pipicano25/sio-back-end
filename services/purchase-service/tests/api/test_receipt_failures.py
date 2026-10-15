"""Fallas distribuidas de la recepción (R-05; FR-022; RC-01, RC-03; spec 020 FR-020-03, RC-MVP-2).

Antes de la spec 020 estas pruebas aplicaban a la confirmación. Las de compensación por
numeración desaparecen: la confirmación numera antes de cualquier movimiento (DS-03).
"""

from __future__ import annotations

from sqlalchemy import text

from tests.conftest import base, fetch, new_key


def receipt_operation(test_engine) -> dict:
    return fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'RECEIVE'")[0]


def confirmed(make_sequence, make_draft, confirm) -> dict:
    make_sequence()
    return confirm(make_draft()).json()


def test_inventory_unavailable_leaves_pending_and_retry_completes(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    purchase = confirmed(make_sequence, make_draft, confirm)
    key = new_key()
    fakes.inventory.availability.down = True
    response = receive(purchase, key)
    assert response.status_code == 503
    body = response.json()
    assert body["dependency"] == "inventory" and body["operation_id"]
    pending = receipt_operation(test_engine)
    assert pending["status"] == "PENDING"
    assert fetch(test_engine, "SELECT status, inventory_operation_id FROM purchases")[0] == {
        "status": "CONFIRMED",
        "inventory_operation_id": None,
    }

    fakes.inventory.availability.down = False
    retried = receive(purchase, key)
    assert retried.status_code == 200, retried.text
    assert retried.json()["receipt_status"] == "RECEIVED"
    [entry] = fakes.inventory.entries()
    assert entry.payload["operation_key"] == str(pending["id"])  # misma clave de operación
    assert receipt_operation(test_engine)["status"] == "SUCCEEDED"


def test_pending_receipt_blocks_other_keys_and_cancellation(buyer, world, fakes, make_sequence, make_draft, confirm, receive, cancel) -> None:
    purchase = confirmed(make_sequence, make_draft, confirm)
    fakes.inventory.availability.down = True
    pending = receive(purchase)
    operation_id = pending.json()["operation_id"]
    other = receive(purchase)
    assert other.status_code == 409 and other.json()["code"] == "PURCHASE.OPERATION_IN_PROGRESS"
    assert other.json()["operation_id"] == operation_id
    blocked = cancel(purchase)
    assert blocked.status_code == 409 and blocked.json()["code"] == "PURCHASE.OPERATION_IN_PROGRESS"
    current = buyer.get(f"{base(world)}/purchases/{purchase['id']}").json()
    assert current["pending_operation_id"] == operation_id and current["receipt_status"] == "PENDING"


def test_lost_response_retry_gets_idempotent_200(world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    """Inventory aplicó la entrada pero la respuesta se perdió: el reintento no duplica (RC-01)."""
    purchase = confirmed(make_sequence, make_draft, confirm)
    key = new_key()
    fakes.inventory.lose_response = 1
    assert receive(purchase, key).status_code == 503
    assert len(fakes.inventory.entries()) == 1
    retried = receive(purchase, key)
    assert retried.status_code == 200
    assert len(fakes.inventory.entries()) == 1
    assert fakes.inventory.entry_calls == 2  # la segunda llamada fue idempotente en Inventory


def test_database_failure_after_inventory_is_completed_by_retry(app, world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    """Si T2 no puede escribir, la operación queda PENDING y se completa después sin duplicar."""
    purchase = confirmed(make_sequence, make_draft, confirm)
    key = new_key()
    original_apply = fakes.inventory.apply_entry

    def apply_then_break_database(payload):
        result = original_apply(payload)
        # Fallo local tras aplicar en Inventory: otra transacción bloquea la compra más que lock_timeout.
        app.state.database.lock_timeout_ms = 1
        holder.begin()
        holder.execute(text("SELECT 1 FROM purchases WHERE id = :id FOR UPDATE"), {"id": purchase["id"]})
        return result

    holder = test_engine.connect()
    fakes.inventory.apply_entry = apply_then_break_database
    try:
        response = receive(purchase, key)
        assert response.status_code == 503 and response.json()["dependency"] == "database"
    finally:
        holder.rollback()
        holder.close()
    app.state.database.lock_timeout_ms = 5000
    fakes.inventory.apply_entry = original_apply
    assert receipt_operation(test_engine)["status"] == "PENDING"
    retried = receive(purchase, key)
    assert retried.status_code == 200 and retried.json()["receipt_status"] == "RECEIVED"
    assert len(fakes.inventory.entries()) == 1


def test_operation_columns_and_error_details(world, fakes, make_sequence, make_draft, confirm, receive, cancel, test_engine) -> None:
    """D-02: actor y motivo en columnas propias; `error_details` solo con errores."""
    from tests.conftest import user_sub

    purchase = confirmed(make_sequence, make_draft, confirm)
    received = receive(purchase).json()
    cancel(received, reason="Motivo original")
    rows = fetch(
        test_engine,
        "SELECT operation_type, application_user_id, reason, error_details FROM purchase_operations ORDER BY started_at",
    )
    buyer_user = fakes.oc.members[(user_sub("compras.test"), world.company)]
    assert [(row["operation_type"], row["application_user_id"], row["reason"], row["error_details"]) for row in rows] == [
        ("CONFIRM", buyer_user, None, None),
        ("RECEIVE", buyer_user, None, None),
        ("CANCEL", buyer_user, "Motivo original", None),
    ]
