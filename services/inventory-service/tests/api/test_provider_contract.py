"""Garantías del contrato Provider para Purchase y Sales (`contracts/inventory-provider.md`; RC-09; T069)."""

from __future__ import annotations

import re

from tests.conftest import BALANCES_READ, MOVEMENTS_READ, PLATFORM_LOOKUP, line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
DECIMAL = re.compile(r"^-?\d+\.\d{4}$")
MONEY = re.compile(r"^-?\d+\.\d{2}$")

OPERATION_FIELDS = {
    "id", "operation_key", "operation_type", "company_id", "branch_id", "origin_type", "origin_id",
    "application_user_id", "correlation_id", "reason", "reverses_operation_id", "reversed_by_operation_id",
    "created_at", "created_by", "movements", "balances",
}
MOVEMENT_FIELDS = {
    "id", "line_index", "origin_detail_id", "company_product_id", "movement_type", "quantity",
    "previous_balance", "new_balance", "balance_sequence", "unit_cost", "reversed_movement_id",
    # 013 (`inventory-provider-delta.md`): ampliación compatible.
    "movement_value", "cost_known",
}
BALANCE_FIELDS = {"company_product_id", "quantity", "inventory_value", "average_unit_cost", "has_unknown_cost"}


def test_guaranteed_fields_and_decimal_format(purchase, world) -> None:
    data = purchase.post(ENTRIES, json=operation_body(world, line(world.products[0], 3, unit_cost="7.5"))).json()
    assert OPERATION_FIELDS <= set(data)
    movement = data["movements"][0]
    assert MOVEMENT_FIELDS <= set(movement)
    for field in ("quantity", "previous_balance", "new_balance", "unit_cost"):
        assert DECIMAL.match(movement[field]), (field, movement[field])
    assert MONEY.match(movement["movement_value"]) and movement["cost_known"] is True
    balance = data["balances"][0]
    assert BALANCE_FIELDS == set(balance)
    assert DECIMAL.match(balance["quantity"]) and DECIMAL.match(balance["average_unit_cost"])
    assert MONEY.match(balance["inventory_value"])


def test_retry_with_same_key_is_200_and_conflict_is_409(purchase, world) -> None:
    body = operation_body(world, line(world.products[0], "2"))
    assert purchase.post(ENTRIES, json=body).status_code == 201
    assert purchase.post(ENTRIES, json=body).status_code == 200
    assert purchase.post(ENTRIES, json={**body, "reason": "otra"}).status_code == 409


def test_sales_flow_check_stock_then_output_then_reverse(purchase, sales, as_token, service_token, world) -> None:
    product = world.products[0]
    purchase.post(ENTRIES, json=operation_body(world, line(product, "5")))
    reader = as_token(service_token(BALANCES_READ, MOVEMENTS_READ, PLATFORM_LOOKUP, client_id="sales-service"))

    stock = reader.post(
        f"/api/v1/companies/{world.company}/branches/{world.branch}/balances/lookup",
        json={"company_product_ids": [str(product)]},
    )
    assert stock.status_code == 200 and stock.json()["items"][0]["quantity"] == "5.0000"

    rejected = sales.post(OUTPUTS, json=operation_body(world, line(product, "6"), origin_type="SALE"))
    assert rejected.status_code == 409 and rejected.json()["shortages"]

    output = sales.post(OUTPUTS, json=operation_body(world, line(product, "5"), origin_type="SALE")).json()
    by_key = reader.get(f"/api/v1/companies/{world.company}/inventory-operations/by-key/{output['operation_key']}")
    assert by_key.status_code == 200 and by_key.json()["id"] == output["id"]

    reversed_ = sales.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world))
    assert reversed_.status_code == 201


def test_human_with_wildcard_never_applies(as_user, world) -> None:
    assert as_user("admin.test").post(ENTRIES, json=operation_body(world, line(world.products[0], "1"))).status_code == 403


def test_technical_reader_without_lookup_gets_isolation(as_token, service_token, world) -> None:
    reader = as_token(service_token(BALANCES_READ, client_id="sales-service"))
    response = reader.get(f"/api/v1/companies/{world.company}/branches/{world.branch}/balances")
    assert response.status_code == 404


def test_entries_require_unit_cost(purchase, world) -> None:
    """Cambio incompatible declarado y aprobado (DS-12)."""
    body = operation_body(world, line(world.products[0], "2"))
    body["lines"][0].pop("unit_cost", None)
    response = purchase.post(ENTRIES, json=body)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNIT_COST_REQUIRED"


def test_output_reports_cost_and_consumed_entry_cannot_be_reversed(purchase, sales, world) -> None:
    product = world.products[0]
    entry = purchase.post(ENTRIES, json=operation_body(world, line(product, "4", unit_cost="12.5"))).json()
    output = sales.post(OUTPUTS, json=operation_body(world, line(product, "1"), origin_type="SALE")).json()
    movement = output["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("12.5000", "12.50", True)

    response = purchase.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.ENTRY_LAYER_CONSUMED"
