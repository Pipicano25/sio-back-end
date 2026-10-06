"""Salidas concurrentes reales contra PostgreSQL (SC-002, RC-03; T035).

Cada hilo usa su propio `TestClient` sobre la misma aplicación (misma base y pool).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.conftest import line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def post_many(app, token, bodies, url=OUTPUTS, workers=25):
    headers = {"Authorization": f"Bearer {token}"}

    def send(body):
        # Sin `with`: no ejecuta el ciclo de vida de la aplicación compartida (que cierra el pool).
        client = TestClient(app, raise_server_exceptions=False)
        return client.post(url, json=body, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(send, bodies))


def kardex(test_engine, product):
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT balance_sequence, previous_balance, new_balance FROM inventory_movements "
                "WHERE company_product_id = :p ORDER BY balance_sequence"
            ),
            {"p": product},
        ).all()


def assert_chained(rows) -> None:
    assert [row.balance_sequence for row in rows] == list(range(1, len(rows) + 1))
    for previous, current in zip(rows, rows[1:]):
        assert current.previous_balance == previous.new_balance
    assert all(row.new_balance >= 0 for row in rows)


@pytest.mark.parametrize(("initial", "expected_applied"), [(10, 10), (0, 0)])
def test_fifty_simultaneous_outputs(app, operator, service_token, world, test_engine, initial, expected_applied) -> None:
    from tests.conftest import ALL_INVENTORY

    product = world.products[0]
    if initial:
        assert operator.post(ENTRIES, json=operation_body(world, line(product, str(initial)))).status_code == 201

    bodies = [operation_body(world, line(product, "1"), origin_type="SALE") for _ in range(50)]
    statuses = post_many(app, service_token(*ALL_INVENTORY), bodies)

    assert statuses.count(201) == expected_applied
    assert statuses.count(409) == 50 - expected_applied
    assert 500 not in statuses

    rows = kardex(test_engine, product)
    assert_chained(rows)
    with test_engine.connect() as connection:
        quantity = connection.execute(text("SELECT coalesce(sum(quantity), 0) FROM inventory_balances")).scalar_one()
    assert quantity == Decimal(0)


def test_operations_over_products_in_different_order_do_not_deadlock(app, operator, service_token, world, test_engine) -> None:
    from tests.conftest import ALL_INVENTORY

    p1, p2, p3 = world.products
    assert operator.post(ENTRIES, json=operation_body(world, line(p1, "100"), line(p2, "100"), line(p3, "100"))).status_code == 201

    orders = [(p1, p2, p3), (p3, p2, p1), (p2, p3, p1), (p1, p3, p2)]
    bodies = [
        operation_body(world, *[line(p, "1") for p in orders[i % len(orders)]], origin_type="SALE") for i in range(40)
    ]
    statuses = post_many(app, service_token(*ALL_INVENTORY), bodies, workers=20)

    assert statuses == [201] * 40
    for product in (p1, p2, p3):
        rows = kardex(test_engine, product)
        assert_chained(rows)
        assert rows[-1].new_balance == Decimal(60)
