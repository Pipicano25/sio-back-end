"""Misma clave en paralelo: una sola aplicación y ningún `500` (FR-023, RC-05; T039)."""

from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from tests.conftest import ALL_INVENTORY, count_rows, line, operation_body

ENTRIES = "/api/v1/inventory-entries"


def post_all(app, token, bodies, workers=25):
    headers = {"Authorization": f"Bearer {token}"}

    def send(body):
        # Sin `with`: no ejecuta el ciclo de vida de la aplicación compartida (que cierra el pool).
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(ENTRIES, json=body, headers=headers)
        return response.status_code, response.json().get("id")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(send, bodies))


def test_hundred_parallel_requests_with_the_same_key(app, service_token, world, test_engine) -> None:
    body = operation_body(world, line(world.products[0], "4"))
    results = post_all(app, service_token(*ALL_INVENTORY), [body] * 100)

    statuses = [status for status, _ in results]
    assert 500 not in statuses
    assert statuses.count(201) == 1
    assert statuses.count(200) == 99
    assert len({operation_id for _, operation_id in results}) == 1
    assert count_rows(test_engine, "inventory_movements") == 1


def test_parallel_requests_with_the_same_key_and_different_payloads(app, service_token, world, test_engine) -> None:
    body = operation_body(world, line(world.products[0], "4"))
    different = copy.deepcopy(body)
    different["lines"][0]["quantity"] = "5"
    bodies = [body if i % 2 == 0 else different for i in range(40)]

    results = post_all(app, service_token(*ALL_INVENTORY), bodies, workers=20)
    statuses = [status for status, _ in results]

    assert 500 not in statuses
    assert statuses.count(201) == 1
    winner = next(index for index, (status, _) in enumerate(results) if status == 201)
    for index, (status, _) in enumerate(results):
        same_as_winner = (index % 2) == (winner % 2)
        if index != winner:
            assert status == (200 if same_as_winner else 409)
    assert count_rows(test_engine, "inventory_operations") == 1
