"""Adaptador de Inventory (contrato 012 + delta 013; research.md R-07; T015)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.application.ports import InventoryRejection
from purchase_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from tests.contract.adapter_support import Recorder, Tokens, expired_then, json_response, timeout

BASE = "http://inventory.test/api/v1"


def gateway(handler) -> tuple[HTTPInventoryGateway, Recorder, Tokens]:
    recorder, tokens = Recorder(handler), Tokens()
    return HTTPInventoryGateway(base_url=BASE, timeout_seconds=1, tokens=tokens, transport=recorder.transport), recorder, tokens


@pytest.mark.parametrize("status", [200, 201])
def test_entry_returns_operation_id(status) -> None:
    operation = uuid4()
    adapter, recorder, _ = gateway(json_response(status, {"id": str(operation), "operation_type": "ENTRY"}))
    payload = {"operation_key": str(uuid4()), "lines": []}
    assert adapter.apply_entry(payload).id == operation
    assert recorder.requests[0].url.path == "/api/v1/inventory-entries"
    assert json.loads(recorder.requests[0].content) == payload
    assert recorder.requests[0].headers["authorization"].startswith("Bearer tecnico-")


def test_reversal_targets_the_exact_operation() -> None:
    entry, reversal = uuid4(), uuid4()
    adapter, recorder, _ = gateway(json_response(201, {"id": str(reversal), "reverses_operation_id": str(entry)}))
    result = adapter.reverse_entry(entry, {"operation_key": "k"})
    assert result.id == reversal and result.reverses_operation_id == entry
    assert recorder.requests[0].url.path == f"/api/v1/inventory-entries/{entry}/reversal"


@pytest.mark.parametrize(
    ("status", "code"),
    [(409, "ENTRY_LAYER_CONSUMED"), (409, "OPERATION_KEY_CONFLICT"), (422, "VALIDATION_ERROR"), (404, "NOT_FOUND")],
)
def test_definitive_rejections(status, code) -> None:
    adapter, _, _ = gateway(json_response(status, {"code": f"INVENTORY.{code}"}))
    with pytest.raises(InventoryRejection) as error:
        adapter.reverse_entry(uuid4(), {})
    assert (error.value.status, error.value.code) == (status, code)


@pytest.mark.parametrize("handler", [json_response(503), json_response(500), json_response(408), json_response(403), timeout, json_response(201, {"x": 1})])
def test_retryable_failures_are_unavailable(handler) -> None:
    adapter, _, _ = gateway(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        adapter.apply_entry({})
    assert error.value.provider == "inventory"


def test_by_key_found_missing_and_renewal() -> None:
    company, key, operation = uuid4(), uuid4(), uuid4()
    adapter, recorder, tokens = gateway(expired_then({"id": str(operation)}))
    assert adapter.find_by_key(company, key).id == operation
    assert recorder.requests[-1].url.path == f"/api/v1/companies/{company}/inventory-operations/by-key/{key}"
    assert tokens.invalidated == 1
    adapter, _, _ = gateway(json_response(404))
    assert adapter.find_by_key(company, key) is None
