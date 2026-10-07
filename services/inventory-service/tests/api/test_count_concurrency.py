"""Conteos bajo concurrencia: un conteo en curso por sucursal y finalización todo o nada (RC-13, RC-14; T042)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from inventory_service.infrastructure import repository as repository_module
from tests.api.test_fifo_concurrency import assert_layers_are_consistent
from tests.conftest import OPERATOR_ROLES, line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def base(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-counts"


def send_all(app, requests, workers=10):
    def send(request):
        method, url, body, token = request
        client = TestClient(app, raise_server_exceptions=False)
        response = client.request(method, url, json=body, headers={"Authorization": f"Bearer {token}"})
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(send, requests))


def new_count(clerk, world) -> dict:
    response = clerk.post(base(world), json={"branch_id": str(world.branch)})
    assert response.status_code == 201
    return response.json()


def test_two_simultaneous_starts_in_the_same_branch(app, as_user, user_token, world) -> None:
    clerk = as_user("inventario.test")
    counts = [new_count(clerk, world) for _ in range(6)]
    token = user_token("inventario.test")
    results = send_all(app, [("POST", f"{base(world)}/{c['id']}/start", {"version": 1}, token) for c in counts])
    statuses = [status for status, _ in results]
    assert statuses.count(200) == 1
    assert [body["code"] for status, body in results if status == 409] == ["INVENTORY.COUNT_ALREADY_IN_PROGRESS"] * 5


def test_complete_and_cancel_at_the_same_time(app, as_user, operator, user_token, world, test_engine) -> None:
    clerk = as_user("inventario.test")
    product = world.products[0]
    assert operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost="5"))).status_code == 201
    for _ in range(5):
        count = new_count(clerk, world)
        started = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": 1}).json()
        clerk.request("PUT", f"{base(world)}/{count['id']}/details/{product}", json={"counted_quantity": "9"})
        token = user_token("inventario.test")
        results = send_all(
            app,
            [
                ("POST", f"{base(world)}/{count['id']}/complete", {"completion_key": str(uuid4()), "version": started["version"]}, token),
                ("POST", f"{base(world)}/{count['id']}/cancel", {"reason": "Carrera", "version": started["version"]}, token),
            ],
        )
        statuses = sorted(status for status, _ in results)
        assert statuses == [200, 409], results
        final = clerk.get(f"{base(world)}/{count['id']}").json()
        assert final["status"] in ("COMPLETED", "CANCELLED")
        if final["status"] == "CANCELLED":
            assert final["adjustments"] == []
    assert_layers_are_consistent(test_engine)


def test_completion_concurrent_with_outputs_is_all_or_nothing(app, as_user, operator, service_token, user_token, world, test_engine) -> None:
    clerk = as_user("inventario.test")
    a, b, c = world.products
    body = operation_body(world, *[line(p, "20", unit_cost=str(i + 1)) for i, p in enumerate((a, b, c))])
    assert operator.post(ENTRIES, json=body).status_code == 201

    count = new_count(clerk, world)
    started = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": 1}).json()
    for product, counted in ((c, "18"), (a, "15"), (b, "25")):
        clerk.request("PUT", f"{base(world)}/{count['id']}/details/{product}", json={"counted_quantity": counted})

    sales_token = service_token(*OPERATOR_ROLES)
    requests = [
        ("POST", OUTPUTS, operation_body(world, *[line(p, "1") for p in order], origin_type="SALE"), sales_token)
        for order in ([a, b, c], [c, b, a], [b, a, c], [c, a, b]) * 3
    ]
    requests.insert(6, ("POST", f"{base(world)}/{count['id']}/complete", {"completion_key": str(uuid4()), "version": started["version"]}, user_token("inventario.test")))
    results = send_all(app, requests, workers=13)
    statuses = [status for status, _ in results]
    assert 500 not in statuses and 503 not in statuses

    final = clerk.get(f"{base(world)}/{count['id']}").json()
    assert final["status"] == "COMPLETED"
    assert len(final["adjustments"]) == 3
    with test_engine.connect() as connection:
        balances = dict(connection.execute(text("SELECT company_product_id, quantity FROM inventory_balances")).all())
    sold = statuses.count(201)
    # Cada diferencia registrada se aplicó una vez sobre el saldo vigente: A −5, B +5, C −2.
    assert balances == {a: D(20 - 5 - sold), b: D(20 + 5 - sold), c: D(20 - 2 - sold)}
    assert_layers_are_consistent(test_engine)


def test_failure_during_completion_leaves_nothing(as_user, operator, world, test_engine, monkeypatch) -> None:
    clerk = as_user("inventario.test")
    a, b, _ = world.products
    assert operator.post(ENTRIES, json=operation_body(world, line(a, "10", unit_cost="2"), line(b, "10", unit_cost="3"))).status_code == 201
    count = new_count(clerk, world)
    started = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": 1}).json()
    clerk.request("PUT", f"{base(world)}/{count['id']}/details/{a}", json={"counted_quantity": "8"})
    clerk.request("PUT", f"{base(world)}/{count['id']}/details/{b}", json={"counted_quantity": "11"})

    def snapshot():
        with test_engine.connect() as connection:
            return {
                table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all()
                for table in ("inventory_movements", "inventory_balances", "inventory_cost_layers", "inventory_cost_consumptions", "inventory_adjustments")
            }

    before = snapshot()
    original = repository_module.insert_adjustments

    def explode(session, rows):
        original(session, rows)  # algunos ajustes ya se escribieron en esta transacción
        raise RuntimeError("falla inyectada durante la finalización")

    monkeypatch.setattr(repository_module, "insert_adjustments", explode)
    response = clerk.post(f"{base(world)}/{count['id']}/complete", json={"completion_key": str(uuid4()), "version": started["version"]})
    assert response.status_code == 500
    assert snapshot() == before
    assert clerk.get(f"{base(world)}/{count['id']}").json()["status"] == "IN_PROGRESS"
