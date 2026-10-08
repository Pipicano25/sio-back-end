"""Conciliador de operaciones PENDING (R-16, FR-021; RC-06; T057)."""

from __future__ import annotations

import pytest

from sales_service.config import Settings
from sales_service.domain.status import RECONCILER_ACTOR
from tests.conftest import fetch, new_key
from tests.contract.reconciler_support import age_pending, run_reconciler


def pending_confirmation(fakes, make_sequence, make_draft, confirm, *, lose_response: bool):
    make_sequence()
    draft = make_draft()
    key = new_key()
    if lose_response:
        fakes.inventory.lose_response = 1  # Inventory aplica, la respuesta se pierde
    else:
        fakes.inventory.availability.down = True  # Inventory nunca recibe la solicitud
    assert confirm(draft, key).status_code == 503
    fakes.inventory.availability.down = False
    return draft, key


def test_only_takes_pending_older_than_threshold(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    pending_confirmation(fakes, make_sequence, make_draft, confirm, lose_response=True)
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 0
    assert fetch(test_engine, "SELECT status FROM sale_operations")[0]["status"] == "PENDING"


def test_applied_in_inventory_is_completed(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    draft, _ = pending_confirmation(fakes, make_sequence, make_draft, confirm, lose_response=True)
    age_pending(test_engine)
    calls_before = fakes.inventory.output_calls
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 1 and len(result.completed) == 1
    assert fakes.inventory.output_calls == calls_before  # solo consulta por clave, nunca vuelve a aplicar
    sale = fetch(test_engine, "SELECT * FROM sales")[0]
    [entry] = fakes.inventory.outputs()
    assert sale["status"] == "CONFIRMED" and sale["number"] == "FV-000001"
    assert sale["inventory_operation_id"] == entry.ref.id and sale["updated_by"] == RECONCILER_ACTOR
    # Completa con el costo FIFO de la salida consultada por clave (P-05).
    detail = fetch(test_engine, "SELECT unit_cost_snapshot, cost_total, cost_known, gross_margin_amount FROM sale_details")[0]
    assert (str(detail["unit_cost_snapshot"]), str(detail["cost_total"]), detail["cost_known"]) == ("1000.0000", "2000.00", True)
    assert str(detail["gross_margin_amount"]) == "1000.00"  # 2 × 1500 − 2000
    operation = fetch(test_engine, "SELECT * FROM sale_operations")[0]
    assert operation["status"] == "SUCCEEDED" and operation["updated_by"] == RECONCILER_ACTOR
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox")]
    assert actions.count("CONFIRM_SALE") == 1


def test_not_applied_is_failed_and_sale_stays_draft(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    draft, key = pending_confirmation(fakes, make_sequence, make_draft, confirm, lose_response=False)
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert len(result.failed) == 1
    operation = fetch(test_engine, "SELECT * FROM sale_operations")[0]
    assert operation["status"] == "FAILED" and operation["error_code"] == "OPERATION_NOT_APPLIED"
    assert fetch(test_engine, "SELECT status FROM sales")[0]["status"] == "DRAFT"
    assert fakes.inventory.outputs() == []
    replay = confirm(draft, key)  # la misma clave repite el cierre
    assert replay.status_code == 409 and replay.json()["code"] == "SALES.OPERATION_NOT_APPLIED"
    audit = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox") if row["payload"]["action"] == "CONFIRM_SALE"]
    assert audit[0]["result"] == "FAILURE"


def test_inventory_unavailable_leaves_it_for_next_cycle(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    pending_confirmation(fakes, make_sequence, make_draft, confirm, lose_response=True)
    age_pending(test_engine)
    fakes.inventory.availability.down = True
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.claimed == 1 and result.unchanged
    assert fetch(test_engine, "SELECT status FROM sale_operations")[0]["status"] == "PENDING"
    fakes.inventory.availability.down = False
    age_pending(test_engine)
    assert len(run_reconciler(test_engine, fakes.inventory).completed) == 1


def test_client_retry_after_claim_prevents_wrong_failure(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """Carrera: el conciliador marcó la operación y consultó (no existía); entre tanto el cliente reintenta y aplica.

    El cierre `FAILED` del conciliador exige que nadie haya tocado la operación desde su marca.
    """
    draft, key = pending_confirmation(fakes, make_sequence, make_draft, confirm, lose_response=False)
    age_pending(test_engine)
    original_find = fakes.inventory.find_by_key

    def find_then_client_retries(company_id, operation_key):
        found = original_find(company_id, operation_key)  # todavía no existe
        response = confirm(draft, key)  # el cliente reintenta y completa
        assert response.status_code == 200, response.text
        return found

    fakes.inventory.find_by_key = find_then_client_retries
    result = run_reconciler(test_engine, fakes.inventory)
    assert not result.failed
    operation = fetch(test_engine, "SELECT status FROM sale_operations")[0]
    assert operation["status"] == "SUCCEEDED"
    assert fetch(test_engine, "SELECT status FROM sales")[0]["status"] == "CONFIRMED"
    assert len(fakes.inventory.outputs()) == 1


def test_retries_pending_compensation(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence(maximum_number=1)
    first, second = make_draft(), make_draft()
    key = new_key()
    fakes.inventory.availability.down = True
    confirm(second, key)
    fakes.inventory.availability.down = False
    confirm(first)
    original_reverse = fakes.inventory.reverse_output

    def down(*_):
        from sales_service.application.exceptions import DependencyUnavailableError

        raise DependencyUnavailableError("inventory", operation="reversal", cause="prueba")

    fakes.inventory.reverse_output = down
    assert confirm(second, key).status_code == 503
    fakes.inventory.reverse_output = original_reverse
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert result.compensated
    operation = fetch(test_engine, "SELECT * FROM sale_operations WHERE sale_id = :p", p=second["id"])[0]
    assert operation["status"] == "FAILED" and operation["error_code"] == "SEQUENCE_EXHAUSTED"
    assert fakes.inventory.balance(world.branch, world.product) == 1000 - 2  # la salida compensada se restituyó


def test_threshold_must_exceed_ten_inventory_timeouts(test_settings) -> None:
    from dataclasses import replace

    with pytest.raises(RuntimeError):
        replace(test_settings, inventory_timeout_seconds=10.0, reconciler_threshold_seconds=99.0)
    assert isinstance(replace(test_settings, inventory_timeout_seconds=10.0, reconciler_threshold_seconds=100.0), Settings)
