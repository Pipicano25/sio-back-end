"""Reversos concurrentes (FR-032, RC-03; T043)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.conftest import ALL_INVENTORY, line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def post_parallel(app, token, requests):
    headers = {"Authorization": f"Bearer {token}"}

    def send(item):
        url, body = item
        # Sin `with`: no ejecuta el ciclo de vida de la aplicación compartida (que cierra el pool).
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(url, json=body, headers=headers)
        return response.status_code, response.json().get("code")

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        return list(pool.map(send, requests))


def test_two_reversals_of_the_same_operation(app, operator, service_token, world) -> None:
    operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "10")))
    output = operator.post(OUTPUTS, json=operation_body(world, line(world.products[0], "4"), origin_type="SALE")).json()

    url = f"{OUTPUTS}/{output['id']}/reversal"
    results = post_parallel(app, service_token(*ALL_INVENTORY), [(url, reversal_body(world)), (url, reversal_body(world))])

    assert sorted(status for status, _ in results) == [201, 409]
    assert ("INVENTORY.ALREADY_REVERSED" in {code for _, code in results})


def test_entry_reversal_racing_an_output_never_goes_negative(app, operator, service_token, world, test_engine) -> None:
    product = world.products[0]
    entry = operator.post(ENTRIES, json=operation_body(world, line(product, "10"))).json()

    requests = [
        (f"{ENTRIES}/{entry['id']}/reversal", reversal_body(world)),
        (OUTPUTS, operation_body(world, line(product, "6"), origin_type="SALE")),
    ]
    statuses = sorted(status for status, _ in post_parallel(app, service_token(*ALL_INVENTORY), requests))

    assert statuses == [201, 409]
    with test_engine.connect() as connection:
        quantity = connection.execute(text("SELECT quantity FROM inventory_balances")).scalar_one()
    assert quantity >= 0
