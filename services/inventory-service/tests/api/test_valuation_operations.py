"""Valoración FIFO en entradas y salidas (Historia 3, escenarios 1, 3 y 5; FR-050 a FR-061; T020)."""

from __future__ import annotations

from decimal import Decimal as D

from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
TABLES = (
    "inventory_operations",
    "inventory_movements",
    "inventory_balances",
    "inventory_cost_layers",
    "inventory_cost_consumptions",
)


def entry(operator, world, product, quantity, cost):
    response = operator.post(ENTRIES, json=operation_body(world, line(product, quantity, unit_cost=cost)))
    assert response.status_code == 201, response.text
    return response.json()


def output(operator, world, product, quantity):
    response = operator.post(OUTPUTS, json=operation_body(world, line(product, quantity), origin_type="SALE"))
    assert response.status_code == 201, response.text
    return response.json()


def layers(test_engine, product):
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT layer_kind, original_quantity, remaining_quantity, unit_cost, cost_known, currency_code, status "
                "FROM inventory_cost_layers WHERE company_product_id = :p ORDER BY received_at, id"
            ),
            {"p": product},
        ).all()


def test_entries_create_layers_and_value_the_balance(operator, world, test_engine) -> None:
    product = world.products[0]
    first = entry(operator, world, product, "10", "1000")
    movement = first["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("1000.0000", "10000.00", True)
    assert first["balances"] == [
        {
            "company_product_id": str(product),
            "quantity": "10.0000",
            "inventory_value": "10000.00",
            "average_unit_cost": "1000.0000",
            "has_unknown_cost": False,
        }
    ]

    second = entry(operator, world, product, "5", "1300")
    assert second["balances"][0]["inventory_value"] == "16500.00"
    assert second["balances"][0]["average_unit_cost"] == "1100.0000"
    assert [tuple(row) for row in layers(test_engine, product)] == [
        ("ENTRY", D("10"), D("10"), D("1000"), True, "COP", "OPEN"),
        ("ENTRY", D("5"), D("5"), D("1300"), True, "COP", "OPEN"),
    ]


def test_output_reports_its_fifo_cost(operator, world, test_engine) -> None:
    product = world.products[0]
    entry(operator, world, product, "10", "1000")
    entry(operator, world, product, "5", "1300")

    data = output(operator, world, product, "12")
    movement = data["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("1050.0000", "12600.00", True)
    assert data["balances"][0] == {
        "company_product_id": str(product),
        "quantity": "3.0000",
        "inventory_value": "3900.00",
        "average_unit_cost": "1300.0000",
        "has_unknown_cost": False,
    }
    remaining = [(row.remaining_quantity, row.status) for row in layers(test_engine, product)]
    assert remaining == [(D("0"), "CLOSED"), (D("3"), "OPEN")]


def test_entry_without_unit_cost_is_rejected_without_changes(operator, world, test_engine) -> None:
    """Historia 3 escenario 3: cambio incompatible aprobado (DS-12, FR-061)."""
    body = operation_body(world, line(world.products[0], "4", unit_cost="10"), line(world.products[1], "2"))
    body["lines"][1].pop("unit_cost", None)  # `operation_body` completa un costo por defecto en las entradas
    response = operator.post(ENTRIES, json=body)
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "INVENTORY.VALIDATION_ERROR"
    assert [(error["field"], error["code"]) for error in data["errors"]] == [("lines[1].unit_cost", "UNIT_COST_REQUIRED")]
    assert all(count_rows(test_engine, table) == 0 for table in TABLES)


def test_zero_cost_is_a_real_cost_not_an_unknown_one(operator, world, test_engine) -> None:
    """Un costo real 0 queda con `cost_known = true`: nunca se confunde con "sin costo"."""
    data = entry(operator, world, world.products[0], "3", "0")
    assert data["movements"][0]["cost_known"] is True
    assert data["balances"][0]["has_unknown_cost"] is False
    assert [tuple(row)[3:5] for row in layers(test_engine, world.products[0])] == [(D("0"), True)]


def test_layers_take_the_company_currency(operator, world, fake_oc, test_engine) -> None:
    fake_oc.currencies[world.company] = "USD"
    entry(operator, world, world.products[0], "1", "2.5")
    assert layers(test_engine, world.products[0])[0].currency_code == "USD"
    assert ("company", world.company) in fake_oc.technical_calls


def test_outputs_do_not_query_the_company_currency(operator, world, fake_oc) -> None:
    entry(operator, world, world.products[0], "5", "10")
    fake_oc.technical_calls.clear()
    output(operator, world, world.products[0], "2")
    assert not [call for call in fake_oc.technical_calls if call[0] == "company"]


def test_unknown_company_is_rejected(operator, world, fake_oc, test_engine) -> None:
    del fake_oc.currencies[world.company]
    response = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "1", unit_cost="1")))
    assert response.status_code == 422
    assert any(error["code"] == "COMPANY_NOT_FOUND" for error in response.json()["errors"])
    assert all(count_rows(test_engine, table) == 0 for table in TABLES)


def test_operational_context_unavailable_applies_nothing(operator, world, fake_oc, test_engine) -> None:
    fake_oc.unavailable = True
    response = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "1", unit_cost="1")))
    assert response.status_code == 503
    assert response.json()["dependency"] == "operational-context"
    assert all(count_rows(test_engine, table) == 0 for table in TABLES)


def test_balance_queries_report_the_valuation(operator, world) -> None:
    product = world.products[0]
    entry(operator, world, product, "10", "1000")
    output(operator, world, product, "4")
    response = operator.get(f"/api/v1/companies/{world.company}/branches/{world.branch}/balances/{product}")
    assert response.status_code == 200
    data = response.json()
    assert (data["quantity"], data["inventory_value"], data["average_unit_cost"], data["has_unknown_cost"]) == (
        "6.0000",
        "6000.00",
        "1000.0000",
        False,
    )
    empty = operator.get(f"/api/v1/companies/{world.company}/branches/{world.branch}/balances/{world.products[2]}").json()
    assert (empty["inventory_value"], empty["average_unit_cost"], empty["has_unknown_cost"]) == ("0.00", None, False)


def test_kardex_reports_cost_and_value(operator, world) -> None:
    product = world.products[0]
    entry(operator, world, product, "10", "1000")
    output(operator, world, product, "4")
    page = operator.get(f"/api/v1/companies/{world.company}/branches/{world.branch}/kardex/{product}").json()
    assert [(m["movement_type"], m["unit_cost"], m["movement_value"], m["cost_known"]) for m in page["items"]] == [
        ("PURCHASE_ENTRY", "1000.0000", "10000.00", True),
        ("SALE_OUTPUT", "1000.0000", "4000.00", True),
    ]
