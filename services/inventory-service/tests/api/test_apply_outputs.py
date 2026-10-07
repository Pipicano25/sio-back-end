"""Salidas de venta sin vender lo que no hay (Historia 2; FR-014; RC-03, RC-04; T034)."""

from __future__ import annotations

from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def stock(test_engine, world, product) -> str:
    with test_engine.connect() as connection:
        value = connection.execute(
            text("SELECT quantity FROM inventory_balances WHERE company_id = :c AND branch_id = :b AND company_product_id = :p"),
            {"c": world.company, "b": world.branch, "p": product},
        ).scalar_one_or_none()
    return f"{value if value is not None else 0:.4f}"


def sale(world, *lines, **overrides):
    return operation_body(world, *lines, origin_type="SALE", **overrides)


def test_output_reduces_the_balance(operator, world, test_engine) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "15.5")))
    response = operator.post(OUTPUTS, json=sale(world, line(product, "5")))
    assert response.status_code == 201, response.text
    movement = response.json()["movements"][0]
    assert (movement["movement_type"], movement["previous_balance"], movement["new_balance"], movement["unit_cost"]) == (
        # 013 (FR-060): la salida informa su costo FIFO (el ficticio por defecto de la entrada).
        "SALE_OUTPUT", "15.5000", "10.5000", "1000.0000"
    )
    assert response.json()["operation_type"] == "OUTPUT"
    assert stock(test_engine, world, product) == "10.5000"


def test_insufficient_line_rejects_the_whole_output(operator, world, test_engine) -> None:
    p1, p2 = world.products[:2]
    operator.post(ENTRIES, json=operation_body(world, line(p1, "10"), line(p2, "2")))
    before = count_rows(test_engine, "inventory_movements")

    response = operator.post(OUTPUTS, json=sale(world, line(p1, "3"), line(p2, "5")))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "INVENTORY.INSUFFICIENT_STOCK"
    assert body["shortages"] == [{"index": 1, "company_product_id": str(p2), "available": "2.0000", "requested": "5.0000"}]
    assert stock(test_engine, world, p1) == "10.0000"
    assert count_rows(test_engine, "inventory_movements") == before
    assert count_rows(test_engine, "inventory_operations") == 1


def test_product_without_balance_has_zero_available(operator, world, test_engine) -> None:
    product = world.products[2]
    response = operator.post(OUTPUTS, json=sale(world, line(product, "1")))
    assert response.status_code == 409
    assert response.json()["shortages"][0]["available"] == "0.0000"
    assert count_rows(test_engine, "inventory_balances") == 0


def test_two_lines_of_the_same_product_use_the_sum(operator, world, test_engine) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "10")))

    rejected = operator.post(OUTPUTS, json=sale(world, line(product, "6"), line(product, "6")))
    assert rejected.status_code == 409
    assert rejected.json()["shortages"] == [
        {"index": 1, "company_product_id": str(product), "available": "4.0000", "requested": "6.0000"}
    ]

    applied = operator.post(OUTPUTS, json=sale(world, line(product, "6"), line(product, "4")))
    assert applied.status_code == 201
    first, second = applied.json()["movements"]
    assert (first["new_balance"], second["previous_balance"], second["new_balance"]) == ("4.0000", "4.0000", "0.0000")
    assert (first["balance_sequence"], second["balance_sequence"]) == (2, 3)
    assert stock(test_engine, world, product) == "0.0000"


def test_unit_cost_not_allowed_in_outputs(operator, world) -> None:
    response = operator.post(OUTPUTS, json=sale(world, line(world.products[0], "1", unit_cost="5")))
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "lines[0].unit_cost", "message": "Las salidas no aceptan costo unitario.", "code": "UNIT_COST_NOT_ALLOWED"}
    ]


def test_origin_type_must_be_sale(operator, world) -> None:
    response = operator.post(OUTPUTS, json=operation_body(world, line(world.products[0], "1")))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "ORIGIN_TYPE_MISMATCH"


def test_entries_client_cannot_apply_outputs(purchase, sales, operator, world) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "5")))
    assert purchase.post(OUTPUTS, json=sale(world, line(product, "1"))).status_code == 403
    assert sales.post(OUTPUTS, json=sale(world, line(product, "1"))).status_code == 201
