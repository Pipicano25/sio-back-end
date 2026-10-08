"""Adaptador de Inventory (contrato 012 + delta 013; research.md R-08, R-09; T017)."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import pytest

from sales_service.application.exceptions import DependencyUnavailableError
from sales_service.application.ports import InventoryRejection
from sales_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from tests.contract.adapter_support import Recorder, Tokens, expired_then, json_response, timeout

BASE = "http://inventory.test/api/v1"


def gateway(handler) -> tuple[HTTPInventoryGateway, Recorder, Tokens]:
    recorder, tokens = Recorder(handler), Tokens()
    return HTTPInventoryGateway(base_url=BASE, timeout_seconds=1, tokens=tokens, transport=recorder.transport), recorder, tokens


def output_body(operation, detail, *, cost_known=True) -> dict:
    return {
        "id": str(operation),
        "operation_type": "OUTPUT",
        "movements": [
            {"id": str(uuid4()), "line_index": 0, "origin_detail_id": str(detail), "company_product_id": str(uuid4()),
             "movement_type": "SALE_OUTPUT", "quantity": "24.0000", "unit_cost": "1250.1250",
             "movement_value": "30003.0000", "cost_known": cost_known},
        ],
        "balances": [],
    }


@pytest.mark.parametrize("status", [200, 201])
def test_output_returns_the_fifo_cost_of_each_movement(status) -> None:
    operation, detail = uuid4(), uuid4()
    adapter, recorder, _ = gateway(json_response(status, output_body(operation, detail)))
    payload = {"operation_key": str(uuid4()), "lines": [{"origin_detail_id": str(detail), "quantity": "24"}]}
    result = adapter.apply_output(payload)
    assert result.id == operation
    movement = result.movements[0]
    assert (movement.origin_detail_id, movement.unit_cost, movement.movement_value, movement.cost_known) == (
        detail, Decimal("1250.1250"), Decimal("30003.0000"), True,
    )
    assert recorder.requests[0].url.path == "/api/v1/inventory-outputs"
    sent = json.loads(recorder.requests[0].content)
    assert sent == payload and "unit_cost" not in sent["lines"][0]
    assert recorder.requests[0].headers["authorization"].startswith("Bearer tecnico-")


def test_unknown_cost_flag_is_read_as_is() -> None:
    adapter, _, _ = gateway(json_response(201, output_body(uuid4(), uuid4(), cost_known=False)))
    assert adapter.apply_output({}).movements[0].cost_known is False
    adapter, _, _ = gateway(json_response(201, output_body(uuid4(), uuid4(), cost_known=None)))
    assert adapter.apply_output({}).movements[0].cost_known is None


def test_output_without_costs_is_an_unexpected_body() -> None:
    body = output_body(uuid4(), uuid4())
    del body["movements"][0]["unit_cost"]
    adapter, _, _ = gateway(json_response(201, body))
    with pytest.raises(DependencyUnavailableError):
        adapter.apply_output({})


def test_reversal_targets_the_exact_output() -> None:
    output, reversal = uuid4(), uuid4()
    adapter, recorder, _ = gateway(
        json_response(201, {"id": str(reversal), "operation_type": "OUTPUT_REVERSAL", "reverses_operation_id": str(output)})
    )
    result = adapter.reverse_output(output, {"operation_key": "k"})
    assert result.id == reversal and result.reverses_operation_id == output and result.movements == ()
    assert recorder.requests[0].url.path == f"/api/v1/inventory-outputs/{output}/reversal"


def test_insufficient_stock_keeps_the_shortages() -> None:
    shortages = [{"index": 1, "company_product_id": str(uuid4()), "available": "3.0000", "requested": "5.0000"}]
    adapter, _, _ = gateway(json_response(409, {"code": "INVENTORY.INSUFFICIENT_STOCK", "shortages": shortages}))
    with pytest.raises(InventoryRejection) as error:
        adapter.apply_output({})
    assert (error.value.status, error.value.code) == (409, "INSUFFICIENT_STOCK")
    assert error.value.body["shortages"] == shortages


@pytest.mark.parametrize(
    ("status", "code"),
    [(409, "ALREADY_REVERSED"), (409, "OPERATION_KEY_CONFLICT"), (422, "VALIDATION_ERROR"), (404, "NOT_FOUND")],
)
def test_definitive_rejections(status, code) -> None:
    adapter, _, _ = gateway(json_response(status, {"code": f"INVENTORY.{code}"}))
    with pytest.raises(InventoryRejection) as error:
        adapter.reverse_output(uuid4(), {})
    assert (error.value.status, error.value.code) == (status, code)


@pytest.mark.parametrize(
    "handler",
    [json_response(503), json_response(500), json_response(408), json_response(403), timeout, json_response(201, {"x": 1})],
)
def test_retryable_failures_are_unavailable(handler) -> None:
    adapter, _, _ = gateway(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        adapter.apply_output({})
    assert error.value.provider == "inventory"


def test_by_key_found_missing_and_renewal() -> None:
    company, key, operation, detail = uuid4(), uuid4(), uuid4(), uuid4()
    adapter, recorder, tokens = gateway(expired_then(output_body(operation, detail)))
    found = adapter.find_by_key(company, key)
    assert found.id == operation and found.movements[0].origin_detail_id == detail
    assert recorder.requests[-1].url.path == f"/api/v1/companies/{company}/inventory-operations/by-key/{key}"
    assert tokens.invalidated == 1
    adapter, _, _ = gateway(json_response(404))
    assert adapter.find_by_key(company, key) is None


def test_balances_lookup_fills_missing_products_with_zero() -> None:
    company, branch, with_stock, without = uuid4(), uuid4(), uuid4(), uuid4()
    adapter, recorder, _ = gateway(json_response(200, {"items": [
        {"company_id": str(company), "branch_id": str(branch), "company_product_id": str(with_stock), "quantity": "12.5000"},
    ]}))
    balances = adapter.lookup_balances(company, branch, [with_stock, without, with_stock])
    assert balances[with_stock].quantity == Decimal("12.5000") and balances[without].quantity == 0
    assert recorder.requests[0].url.path == f"/api/v1/companies/{company}/branches/{branch}/balances/lookup"
    assert json.loads(recorder.requests[0].content) == {"company_product_ids": [str(with_stock), str(without)]}
    unavailable, _, _ = gateway(json_response(503))
    with pytest.raises(DependencyUnavailableError):
        unavailable.lookup_balances(company, branch, [with_stock])
