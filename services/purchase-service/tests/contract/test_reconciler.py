"""Conciliador de recepciones `PENDING` (R-08; FR-025; RC-06; T048; spec 020 FR-020-03, RC-MVP-2).

Spec 020: la recepción es la operación que aplica la entrada en Inventory (la confirmación es
local); no existe compensación por numeración (DS-03).
"""

from __future__ import annotations

import pytest

from purchase_service.config import Settings
from purchase_service.domain.status import RECONCILER_ACTOR
from tests.conftest import fetch, new_key
from tests.contract.reconciler_support import age_pending, run_reconciler

RECEIPT_OPERATION = "SELECT * FROM purchase_operations WHERE operation_type = 'RECEIVE'"


def pending_receipt(fakes, make_sequence, make_draft, confirm, receive, *, lose_response: bool):
    make_sequence()
    confirmed = confirm(make_draft()).json()
    key = new_key()
    if lose_response:
        fakes.inventory.lose_response = 1  # Inventory aplica, la respuesta se pierde
    else:
        fakes.inventory.availability.down = True  # Inventory nunca recibe la solicitud
    assert receive(confirmed, key).status_code == 503
    fakes.inventory.availability.down = False
    return confirmed, key


def test_only_takes_pending_older_than_threshold(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    pending_receipt(fakes, make_sequence, make_draft, confirm, receive, lose_response=True)
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 0
    assert fetch(test_engine, RECEIPT_OPERATION)[0]["status"] == "PENDING"


def test_applied_in_inventory_is_completed(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    confirmed, _ = pending_receipt(fakes, make_sequence, make_draft, confirm, receive, lose_response=True)
    age_pending(test_engine)
    calls_before = fakes.inventory.entry_calls
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 1 and len(result.completed) == 1
    assert fakes.inventory.entry_calls == calls_before  # solo consulta por clave, nunca vuelve a aplicar
    purchase = fetch(test_engine, "SELECT * FROM purchases")[0]
    [entry] = fakes.inventory.entries()
    assert purchase["status"] == "CONFIRMED" and purchase["number"] == confirmed["number"]
    assert purchase["inventory_operation_id"] == entry.ref.id and purchase["updated_by"] == RECONCILER_ACTOR
    assert purchase["received_at"] is not None and purchase["received_by_user_id"] is not None
    operation = fetch(test_engine, RECEIPT_OPERATION)[0]
    assert operation["status"] == "SUCCEEDED" and operation["updated_by"] == RECONCILER_ACTOR
    assert purchase["received_at"] == operation["started_at"]  # la fecha en que el usuario confirmó la recepción
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox")]
    assert actions.count("RECEIVE_PURCHASE") == 1


def test_not_applied_is_failed_and_purchase_stays_pending(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    confirmed, key = pending_receipt(fakes, make_sequence, make_draft, confirm, receive, lose_response=False)
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert len(result.failed) == 1
    operation = fetch(test_engine, RECEIPT_OPERATION)[0]
    assert operation["status"] == "FAILED" and operation["error_code"] == "OPERATION_NOT_APPLIED"
    purchase = fetch(test_engine, "SELECT status, inventory_operation_id FROM purchases")[0]
    assert purchase == {"status": "CONFIRMED", "inventory_operation_id": None}
    assert fakes.inventory.entries() == []
    replay = receive(confirmed, key)  # la misma clave repite el cierre
    assert replay.status_code == 409 and replay.json()["code"] == "PURCHASE.OPERATION_NOT_APPLIED"
    audit = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox") if row["payload"]["action"] == "RECEIVE_PURCHASE"]
    assert audit[0]["result"] == "FAILURE"
    assert receive(confirmed, new_key()).status_code == 200  # una clave nueva vuelve a intentar


def test_inventory_unavailable_leaves_it_for_next_cycle(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    pending_receipt(fakes, make_sequence, make_draft, confirm, receive, lose_response=True)
    age_pending(test_engine)
    fakes.inventory.availability.down = True
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 1 and result.unchanged
    assert fetch(test_engine, RECEIPT_OPERATION)[0]["status"] == "PENDING"
    fakes.inventory.availability.down = False
    age_pending(test_engine)
    assert len(run_reconciler(test_engine, fakes.inventory).completed) == 1


def test_client_retry_after_claim_prevents_wrong_failure(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    """Carrera: el conciliador marcó la operación y consultó (no existía); entre tanto el cliente reintenta y aplica.

    El cierre `FAILED` del conciliador exige que nadie haya tocado la operación desde su marca.
    """
    confirmed, key = pending_receipt(fakes, make_sequence, make_draft, confirm, receive, lose_response=False)
    age_pending(test_engine)
    original_find = fakes.inventory.find_by_key

    def find_then_client_retries(company_id, operation_key):
        found = original_find(company_id, operation_key)  # todavía no existe
        response = receive(confirmed, key)  # el cliente reintenta y completa
        assert response.status_code == 200, response.text
        return found

    fakes.inventory.find_by_key = find_then_client_retries
    result = run_reconciler(test_engine, fakes.inventory)
    assert not result.failed
    assert fetch(test_engine, RECEIPT_OPERATION)[0]["status"] == "SUCCEEDED"
    assert len(fakes.inventory.entries()) == 1


def test_threshold_must_exceed_ten_inventory_timeouts(test_settings) -> None:
    from dataclasses import replace

    with pytest.raises(RuntimeError):
        replace(test_settings, inventory_timeout_seconds=10.0, reconciler_threshold_seconds=99.0)
    assert isinstance(replace(test_settings, inventory_timeout_seconds=10.0, reconciler_threshold_seconds=100.0), Settings)
