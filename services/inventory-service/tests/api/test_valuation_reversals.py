"""Reversos valorizados (Historia 3, escenarios 2 y 6; FR-053; DS-16; RN-04; punto 4; T021)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest
from sqlalchemy import text

from tests.conftest import line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
STATE_TABLES = (
    "inventory_operations",
    "inventory_movements",
    "inventory_balances",
    "inventory_cost_layers",
    "inventory_cost_consumptions",
    "audit_outbox",
)


def post_ok(client, url, body):
    response = client.post(url, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def snapshot(test_engine) -> dict:
    with test_engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all() for table in STATE_TABLES}


def query(test_engine, sql, **params):
    with test_engine.connect() as connection:
        return connection.execute(text(sql), params).all()


@pytest.fixture
def stock(operator, world):
    """Entradas de 10 a 1 000 y 5 a 1 300 del producto 0."""
    product = world.products[0]
    first = post_ok(operator, ENTRIES, operation_body(world, line(product, "10", unit_cost="1000")))
    second = post_ok(operator, ENTRIES, operation_body(world, line(product, "5", unit_cost="1300")))
    return product, first, second


def test_output_reversal_restores_the_same_layers_with_the_same_cost(operator, world, stock, test_engine) -> None:
    product, _, _ = stock
    sale = post_ok(operator, OUTPUTS, operation_body(world, line(product, "12"), origin_type="SALE"))
    reversal = post_ok(operator, f"{OUTPUTS}/{sale['id']}/reversal", reversal_body(world))

    movement = reversal["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("1050.0000", "12600.00", True)
    assert reversal["balances"][0]["inventory_value"] == "16500.00"

    restores = query(
        test_engine,
        "SELECT r.cost_layer_id, r.quantity, r.unit_cost, r.cost_amount, c.cost_layer_id AS original_layer, c.quantity AS original_quantity "
        "FROM inventory_cost_consumptions r JOIN inventory_cost_consumptions c ON c.id = r.restores_consumption_id "
        "WHERE r.consumption_type = 'RESTORE' ORDER BY r.unit_cost",
    )
    assert [(row.quantity, row.unit_cost, row.cost_amount) for row in restores] == [
        (D("10"), D("1000"), D("10000.00")),
        (D("2"), D("1300"), D("2600.00")),
    ]
    assert all(row.cost_layer_id == row.original_layer and row.quantity == row.original_quantity for row in restores)
    consumes = query(test_engine, "SELECT quantity FROM inventory_cost_consumptions WHERE consumption_type = 'CONSUME' ORDER BY quantity")
    assert [row.quantity for row in consumes] == [D("2"), D("10")]  # los consumos originales no cambian
    layers = query(test_engine, "SELECT remaining_quantity, status FROM inventory_cost_layers ORDER BY received_at, id")
    assert [tuple(row) for row in layers] == [(D("10"), "OPEN"), (D("5"), "OPEN")]


def test_entry_reversal_with_intact_layer_retires_it(operator, world, test_engine) -> None:
    product = world.products[1]
    purchase = post_ok(operator, ENTRIES, operation_body(world, line(product, "10", unit_cost="1000")))
    reversal = post_ok(operator, f"{ENTRIES}/{purchase['id']}/reversal", reversal_body(world))
    movement = reversal["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("1000.0000", "10000.00", True)
    assert reversal["balances"][0]["inventory_value"] == "0.00"
    assert reversal["balances"][0]["average_unit_cost"] is None
    rows = query(
        test_engine,
        "SELECT c.consumption_type, c.quantity, l.remaining_quantity, l.status FROM inventory_cost_consumptions c "
        "JOIN inventory_cost_layers l ON l.id = c.cost_layer_id",
    )
    assert [tuple(row) for row in rows] == [("ENTRY_REVERSAL", D("10"), D("0"), "CLOSED")]


@pytest.mark.parametrize("sold", ["2", "10"], ids=["consumida-parcialmente", "consumida-totalmente"])
def test_entry_reversal_of_a_consumed_layer_is_rejected_without_changes(operator, world, stock, test_engine, sold) -> None:
    product, first, _ = stock
    post_ok(operator, OUTPUTS, operation_body(world, line(product, sold), origin_type="SALE"))
    before = snapshot(test_engine)

    response = operator.post(f"{ENTRIES}/{first['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.ENTRY_LAYER_CONSUMED"
    assert snapshot(test_engine) == before


def test_entry_reversal_is_allowed_again_once_the_sale_is_reversed(operator, world, stock) -> None:
    product, first, _ = stock
    sale = post_ok(operator, OUTPUTS, operation_body(world, line(product, "4"), origin_type="SALE"))
    assert operator.post(f"{ENTRIES}/{first['id']}/reversal", json=reversal_body(world)).status_code == 409
    post_ok(operator, f"{OUTPUTS}/{sale['id']}/reversal", reversal_body(world))
    reversal = post_ok(operator, f"{ENTRIES}/{first['id']}/reversal", reversal_body(world))
    assert reversal["balances"][0] == {
        "company_product_id": str(product),
        "quantity": "5.0000",
        "inventory_value": "6500.00",
        "average_unit_cost": "1300.0000",
        "has_unknown_cost": False,
    }


def test_reversals_never_change_the_cost_of_previous_outputs(operator, world, stock, test_engine) -> None:
    """RN-04: el costo histórico de una salida no cambia por reversos, entradas ni salidas posteriores."""
    product, _, second = stock
    sale = post_ok(operator, OUTPUTS, operation_body(world, line(product, "3"), origin_type="SALE"))
    movement_id = sale["movements"][0]["id"]

    def history():
        movement = query(test_engine, "SELECT unit_cost, movement_value, cost_known FROM inventory_movements WHERE id = :m", m=movement_id)
        consumptions = query(
            test_engine,
            "SELECT cost_layer_id, quantity, unit_cost, cost_amount, cost_known FROM inventory_cost_consumptions "
            "WHERE movement_id = :m ORDER BY cost_layer_id",
            m=movement_id,
        )
        return [tuple(row) for row in movement], [tuple(row) for row in consumptions]

    before = history()
    later = post_ok(operator, OUTPUTS, operation_body(world, line(product, "9"), origin_type="SALE"))
    post_ok(operator, f"{OUTPUTS}/{later['id']}/reversal", reversal_body(world))
    post_ok(operator, ENTRIES, operation_body(world, line(product, "4", unit_cost="1500")))
    assert operator.post(f"{ENTRIES}/{second['id']}/reversal", json=reversal_body(world)).status_code in (201, 409)
    assert history() == before


def test_a_reversal_cannot_be_reversed(operator, world, stock) -> None:
    product, _, _ = stock
    sale = post_ok(operator, OUTPUTS, operation_body(world, line(product, "1"), origin_type="SALE"))
    reversal = post_ok(operator, f"{OUTPUTS}/{sale['id']}/reversal", reversal_body(world))
    response = operator.post(f"{OUTPUTS}/{reversal['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.REVERSAL_NOT_ALLOWED"
