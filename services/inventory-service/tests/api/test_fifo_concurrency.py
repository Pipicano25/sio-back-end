"""Concurrencia FIFO con hilos reales contra PostgreSQL (RC-14, RC-15, SC-003, SC-004; punto 3; T023)."""

from __future__ import annotations

import itertools
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D

from fastapi.testclient import TestClient
from sqlalchemy import text

from inventory_service.infrastructure import valuation_repository
from tests.conftest import OPERATOR_ROLES, line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def send_many(app, token, requests, workers=25):
    headers = {"Authorization": f"Bearer {token}"}

    def send(request):
        url, body = request
        # Sin `with`: no ejecuta el ciclo de vida de la aplicación compartida (que cierra el pool).
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(url, json=body, headers=headers)
        return response.status_code, (response.json() if response.status_code in (200, 201) else None)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(send, requests))


def query(test_engine, sql, **params):
    with test_engine.connect() as connection:
        return connection.execute(text(sql), params).all()


def assert_layers_are_consistent(test_engine) -> None:
    """Ninguna capa consumida dos veces y Σ capas abiertas = saldo, para cada saldo (RC-14, RC-15)."""
    layers = query(
        test_engine,
        "SELECT l.id, l.original_quantity, l.remaining_quantity, "
        "COALESCE(SUM(c.quantity) FILTER (WHERE c.consumption_type = 'CONSUME'), 0) AS consumed, "
        "COALESCE(SUM(c.quantity) FILTER (WHERE c.consumption_type = 'RESTORE'), 0) AS restored, "
        "COALESCE(SUM(c.quantity) FILTER (WHERE c.consumption_type = 'ENTRY_REVERSAL'), 0) AS retired "
        "FROM inventory_cost_layers l LEFT JOIN inventory_cost_consumptions c ON c.cost_layer_id = l.id "
        "GROUP BY l.id, l.original_quantity, l.remaining_quantity",
    )
    for layer in layers:
        assert layer.original_quantity - layer.consumed + layer.restored - layer.retired == layer.remaining_quantity
        assert D(0) <= layer.remaining_quantity <= layer.original_quantity
        assert layer.consumed - layer.restored <= layer.original_quantity  # nunca más de lo que tenía

    mismatches = query(
        test_engine,
        "SELECT b.company_product_id FROM inventory_balances b LEFT JOIN ("
        "  SELECT company_id, branch_id, company_product_id, SUM(remaining_quantity) AS q, "
        "         SUM(round(remaining_quantity * unit_cost, 2)) AS v "
        "  FROM inventory_cost_layers WHERE status = 'OPEN' GROUP BY 1, 2, 3"
        ") l USING (company_id, branch_id, company_product_id) "
        "WHERE b.quantity <> COALESCE(l.q, 0) OR b.inventory_value <> COALESCE(l.v, 0)",
    )
    assert mismatches == []

    values = query(
        test_engine,
        "SELECT m.id, m.movement_value, COALESCE(SUM(c.cost_amount), 0) AS consumed "
        "FROM inventory_movements m JOIN inventory_cost_consumptions c ON c.movement_id = m.id "
        "WHERE m.movement_type IN ('SALE_OUTPUT', 'NEGATIVE_ADJUSTMENT', 'OUTPUT_REVERSAL', 'ENTRY_REVERSAL') "
        "GROUP BY m.id, m.movement_value",
    )
    assert all(row.movement_value == row.consumed for row in values)


def test_fifty_simultaneous_outputs_never_consume_a_layer_twice(app, operator, service_token, world, test_engine) -> None:
    product = world.products[0]
    for quantity, cost in (("10", "100"), ("10", "200"), ("10", "300"), ("5", "400")):
        assert operator.post(ENTRIES, json=operation_body(world, line(product, quantity, unit_cost=cost))).status_code == 201

    requests = [(OUTPUTS, operation_body(world, line(product, "1"), origin_type="SALE")) for _ in range(50)]
    results = send_many(app, service_token(*OPERATOR_ROLES), requests)
    statuses = [status for status, _ in results]

    assert statuses.count(201) == 35
    assert statuses.count(409) == 15
    assert 500 not in statuses
    # El costo de cada salida coincide con sus consumos y, en conjunto, con las capas en orden FIFO.
    values = sorted(D(data["movements"][0]["movement_value"]) for status, data in results if status == 201)
    assert values == sorted([D("100.00")] * 10 + [D("200.00")] * 10 + [D("300.00")] * 10 + [D("400.00")] * 5)
    assert_layers_are_consistent(test_engine)
    balance = query(test_engine, "SELECT quantity, inventory_value FROM inventory_balances")[0]
    assert tuple(balance) == (D("0"), D("0.00"))


def test_mixed_operations_over_many_products_and_layers_do_not_deadlock(app, operator, service_token, world, test_engine) -> None:
    """Salidas, entradas y reversos simultáneos con líneas en órdenes opuestos (orden de bloqueos global)."""
    products = world.products
    for cost in ("10", "20", "30"):
        body = operation_body(world, *[line(p, "40", unit_cost=cost) for p in products])
        assert operator.post(ENTRIES, json=body).status_code == 201

    rng = random.Random(13)
    sales = []
    for _ in range(6):
        order = products[:] if rng.random() < 0.5 else products[::-1]
        response = operator.post(OUTPUTS, json=operation_body(world, *[line(p, "2") for p in order], origin_type="SALE"))
        assert response.status_code == 201
        sales.append(response.json())

    requests = []
    for i in range(36):
        order = [products[(i + k) % 3] for k in range(3)] if i % 2 else [products[(i - k) % 3] for k in range(3)]
        if i % 3 == 0:
            requests.append((OUTPUTS, operation_body(world, *[line(p, "1.5") for p in order], origin_type="SALE")))
        elif i % 3 == 1:
            requests.append((ENTRIES, operation_body(world, *[line(p, "1", unit_cost=str(40 + i)) for p in order])))
        else:
            sale = sales[(i // 3) % len(sales)]
            requests.append((f"{OUTPUTS}/{sale['id']}/reversal", reversal_body(world)))
    results = send_many(app, service_token(*OPERATOR_ROLES), requests, workers=18)
    statuses = [status for status, _ in results]

    assert 500 not in statuses
    assert 503 not in statuses  # ningún interbloqueo ni bloqueo agotado
    assert set(statuses) <= {201, 409}
    assert_layers_are_consistent(test_engine)


def test_a_failure_in_the_middle_of_concurrent_outputs_leaves_no_partial_consumption(
    app, operator, service_token, world, test_engine, monkeypatch
) -> None:
    product = world.products[0]
    for cost in ("10", "20"):
        assert operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost=cost))).status_code == 201

    original = valuation_repository.consume
    counter = itertools.count(1)
    lock = threading.Lock()

    def flaky(layers, quantity):
        with lock:
            call = next(counter)
        takes = original(layers, quantity)
        if call % 4 == 0:
            raise RuntimeError("falla inyectada a mitad del consumo")
        return takes

    monkeypatch.setattr(valuation_repository, "consume", flaky)
    requests = [(OUTPUTS, operation_body(world, line(product, "1"), origin_type="SALE")) for _ in range(16)]
    statuses = [status for status, _ in send_many(app, service_token(*OPERATOR_ROLES), requests, workers=8)]

    assert statuses.count(500) == 4
    applied = statuses.count(201)
    assert applied == 12
    consumed = query(test_engine, "SELECT COALESCE(SUM(quantity), 0) AS q FROM inventory_cost_consumptions")[0].q
    assert consumed == D(applied)
    assert query(test_engine, "SELECT quantity FROM inventory_balances")[0].quantity == D(20 - applied)
    assert_layers_are_consistent(test_engine)
