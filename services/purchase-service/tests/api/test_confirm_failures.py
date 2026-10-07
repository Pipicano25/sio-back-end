"""Fallas distribuidas de la confirmación (R-05; FR-022; RC-01, RC-03; T046)."""

from __future__ import annotations

from sqlalchemy import text

from tests.conftest import base, fetch, new_key


def operation(test_engine) -> dict:
    return fetch(test_engine, "SELECT * FROM purchase_operations")[0]


def test_inventory_unavailable_leaves_pending_and_retry_completes(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    fakes.inventory.availability.down = True
    response = confirm(draft, key)
    assert response.status_code == 503
    body = response.json()
    assert body["dependency"] == "inventory" and body["operation_id"]
    pending = operation(test_engine)
    assert pending["status"] == "PENDING"
    assert fetch(test_engine, "SELECT status, number FROM purchases")[0] == {"status": "DRAFT", "number": None}

    fakes.inventory.availability.down = False
    retried = confirm(draft, key)
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "CONFIRMED"
    [entry] = fakes.inventory.entries()
    assert entry.payload["operation_key"] == str(pending["id"])  # misma clave de operación
    assert operation(test_engine)["status"] == "SUCCEEDED"


def test_lost_response_retry_gets_idempotent_200(world, fakes, make_sequence, make_draft, confirm) -> None:
    """Inventory aplicó la entrada pero la respuesta se perdió: el reintento no duplica (RC-01)."""
    make_sequence()
    draft = make_draft()
    key = new_key()
    fakes.inventory.lose_response = 1
    assert confirm(draft, key).status_code == 503
    assert len(fakes.inventory.entries()) == 1
    retried = confirm(draft, key)
    assert retried.status_code == 200
    assert len(fakes.inventory.entries()) == 1
    assert fakes.inventory.entry_calls == 2  # la segunda llamada fue idempotente en Inventory


def test_exhaustion_between_check_and_assignment_compensates(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """La secuencia se agota entre T1 y T2: la entrada aplicada se revierte y no se consume número."""
    sequence = make_sequence(maximum_number=1)
    first, second = make_draft(), make_draft()
    key = new_key()
    fakes.inventory.availability.down = True
    assert confirm(second, key).status_code == 503  # T1 pasó con capacidad disponible
    fakes.inventory.availability.down = False
    assert confirm(first).status_code == 200  # consume el único número

    response = confirm(second, key)  # Inventory aplica, pero el número ya no cabe
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_EXHAUSTED"
    entries = [item for item in fakes.inventory.entries() if item.payload["origin_id"] == second["id"]]
    assert len(entries) == 1 and entries[0].reversed_by is not None  # compensado
    assert fakes.inventory.balance(world.branch, world.product) == 2  # solo la primera compra
    failed = fetch(test_engine, "SELECT * FROM purchase_operations WHERE purchase_id = :p", p=second["id"])[0]
    assert failed["status"] == "FAILED" and failed["error_code"] == "SEQUENCE_EXHAUSTED"
    assert failed["inventory_operation_id"] == entries[0].ref.id
    assert failed["error_details"]["compensation_operation_id"] == str(entries[0].reversed_by)
    assert fetch(test_engine, "SELECT status, number FROM purchases WHERE id = :p", p=second["id"])[0] == {"status": "DRAFT", "number": None}
    assert fetch(test_engine, "SELECT current_number FROM purchase_sequence_counters")[0]["current_number"] == 1
    assert sequence["maximum_number"] == 1


def test_failed_compensation_stays_pending_and_observable(buyer, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence(maximum_number=1)
    first, second = make_draft(), make_draft()
    key = new_key()
    fakes.inventory.availability.down = True
    confirm(second, key)
    fakes.inventory.availability.down = False
    confirm(first)

    original_reverse = fakes.inventory.reverse_entry

    def unavailable_reverse(operation_id, payload):
        from purchase_service.application.exceptions import DependencyUnavailableError

        raise DependencyUnavailableError("inventory", operation="reversal", cause="prueba")

    fakes.inventory.reverse_entry = unavailable_reverse
    response = confirm(second, key)
    assert response.status_code == 503
    pending = fetch(test_engine, "SELECT * FROM purchase_operations WHERE purchase_id = :p", p=second["id"])[0]
    assert pending["status"] == "PENDING" and pending["error_code"] == "COMPENSATION_PENDING"
    assert pending["inventory_operation_id"] is not None  # la entrada aplicada queda registrada
    listed = buyer.get(f"{base(world)}/purchase-operations/{pending['id']}").json()
    assert listed["error_code"] == "COMPENSATION_PENDING"  # visible

    fakes.inventory.reverse_entry = original_reverse
    retried = confirm(second, key)
    assert retried.status_code == 409 and retried.json()["code"] == "PURCHASE.SEQUENCE_EXHAUSTED"
    assert fetch(test_engine, "SELECT status FROM purchase_operations WHERE purchase_id = :p", p=second["id"])[0]["status"] == "FAILED"
    assert fakes.inventory.balance(world.branch, world.product) == 2


def test_database_failure_after_inventory_is_completed_by_retry(app, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """Si T2 no puede escribir, la operación queda PENDING y se completa después sin compensar."""
    make_sequence()
    draft = make_draft()
    key = new_key()
    original_apply = fakes.inventory.apply_entry

    def apply_then_break_database(payload):
        result = original_apply(payload)
        # Fallo local tras aplicar en Inventory: otra transacción bloquea la compra más que lock_timeout.
        app.state.database.lock_timeout_ms = 1
        holder.begin()
        holder.execute(text("SELECT 1 FROM purchases WHERE id = :id FOR UPDATE"), {"id": draft["id"]})
        return result

    holder = test_engine.connect()
    fakes.inventory.apply_entry = apply_then_break_database
    try:
        response = confirm(draft, key)
        assert response.status_code == 503 and response.json()["dependency"] == "database"
    finally:
        holder.rollback()
        holder.close()
    app.state.database.lock_timeout_ms = 5000
    fakes.inventory.apply_entry = original_apply
    assert fetch(test_engine, "SELECT status FROM purchase_operations")[0]["status"] == "PENDING"
    retried = confirm(draft, key)
    assert retried.status_code == 200 and retried.json()["status"] == "CONFIRMED"
    assert len(fakes.inventory.entries()) == 1


def test_compensation_uses_the_confirming_user_not_the_creator(as_user, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """D-07: el reverso compensatorio usa al usuario que inició la confirmación (aquí admin.test, no el creador)."""
    from tests.conftest import user_sub

    make_sequence(maximum_number=1)
    first, second = make_draft(), make_draft()  # creadas por compras.test
    admin = as_user("admin.test")
    key = new_key()
    fakes.inventory.availability.down = True
    assert confirm(second, key, client=admin).status_code == 503
    fakes.inventory.availability.down = False
    confirm(first)

    original_reverse = fakes.inventory.reverse_entry
    attempts = []

    def failing_then_real(operation_id, payload):
        attempts.append(payload)
        if len(attempts) == 1:
            from purchase_service.application.exceptions import DependencyUnavailableError

            raise DependencyUnavailableError("inventory", operation="reversal", cause="prueba")
        return original_reverse(operation_id, payload)

    fakes.inventory.reverse_entry = failing_then_real
    assert confirm(second, key, client=admin).status_code == 503  # compensación pendiente
    assert confirm(second, key, client=admin).status_code == 409  # reintento: compensación aplicada

    confirmer = str(fakes.oc.members[(user_sub("admin.test"), world.company)])
    creator = str(fakes.oc.members[(user_sub("compras.test"), world.company)])
    assert confirmer != creator
    assert [payload["application_user_id"] for payload in attempts] == [confirmer, confirmer]
    assert attempts[0] == attempts[1]  # misma solicitud en todo reintento (huella de Inventory)
    operation = fetch(test_engine, "SELECT * FROM purchase_operations WHERE purchase_id = :p", p=second["id"])[0]
    assert str(operation["application_user_id"]) == confirmer
    assert operation["status"] == "FAILED" and set(operation["error_details"]) == {"error", "compensation_operation_id"}


def test_operation_columns_and_error_details(world, fakes, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    """D-02: actor y motivo en columnas propias; `error_details` solo con errores."""
    from tests.conftest import user_sub

    make_sequence()
    confirmed = confirm(make_draft()).json()
    cancel(confirmed, reason="Motivo original")
    rows = fetch(test_engine, "SELECT operation_type, application_user_id, reason, error_details FROM purchase_operations ORDER BY started_at")
    buyer_user = fakes.oc.members[(user_sub("compras.test"), world.company)]
    assert [(row["operation_type"], row["application_user_id"], row["reason"], row["error_details"]) for row in rows] == [
        ("CONFIRM", buyer_user, None, None),
        ("CANCEL", buyer_user, "Motivo original", None),
    ]
