"""Conciliador de anulaciones `PENDING` (R-08, R-09; RC-03, RC-06; T054)."""

from __future__ import annotations

from tests.conftest import fetch, new_key
from tests.contract.reconciler_support import age_pending, run_reconciler


def pending_cancellation(fakes, make_sequence, make_draft, confirm, receive, cancel, *, lose_response: bool):
    make_sequence()
    confirmed = receive(confirm(make_draft()).json()).json()  # spec 020: solo una compra recibida revierte
    if lose_response:
        fakes.inventory.lose_response = 1
    else:
        fakes.inventory.availability.down = True
    assert cancel(confirmed, new_key()).status_code == 503
    fakes.inventory.availability.down = False
    return confirmed


def test_applied_reversal_completes_cancellation(world, fakes, make_sequence, make_draft, confirm, receive, cancel, test_engine) -> None:
    confirmed = pending_cancellation(fakes, make_sequence, make_draft, confirm, receive, cancel, lose_response=True)
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert len(result.completed) == 1
    purchase = fetch(test_engine, "SELECT * FROM purchases")[0]
    assert purchase["status"] == "CANCELLED" and purchase["number"] == confirmed["number"]
    assert purchase["cancellation_reason"] == "Error de registro"
    operation = fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'CANCEL'")[0]
    reversal = next(item for item in fakes.inventory.by_key.values() if item.kind == "ENTRY_REVERSAL")
    assert operation["status"] == "SUCCEEDED" and operation["inventory_operation_id"] == reversal.ref.id


def test_unapplied_reversal_fails_and_purchase_stays_confirmed(world, fakes, make_sequence, make_draft, confirm, receive, cancel, test_engine) -> None:
    pending_cancellation(fakes, make_sequence, make_draft, confirm, receive, cancel, lose_response=False)
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert len(result.failed) == 1
    assert fetch(test_engine, "SELECT status FROM purchases")[0]["status"] == "CONFIRMED"
    operation = fetch(test_engine, "SELECT * FROM purchase_operations WHERE operation_type = 'CANCEL'")[0]
    assert operation["status"] == "FAILED"
    assert fakes.inventory.balance(world.branch, world.product) == 2
