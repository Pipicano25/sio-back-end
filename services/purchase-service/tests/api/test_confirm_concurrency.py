"""Confirmaciones concurrentes de la misma compra (Historia 2 escenario 6; RC-01; T047)."""

from __future__ import annotations

import threading

from tests.conftest import base, new_key


def test_two_keys_same_purchase_only_one_applies(test_client, user_token, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.availability.latency = 0.3  # la primera queda dentro de Inventory mientras llega la segunda
    barrier = threading.Barrier(2)
    responses = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait(5)
        response = test_client.post(
            f"{base(world)}/purchases/{draft['id']}/confirmation",
            json={"version": draft["version"]},
            headers={"Authorization": f"Bearer {user_token('compras.test')}", "Idempotency-Key": new_key()},
        )
        with lock:
            responses.append(response)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 409], [response.text for response in responses]
    loser = next(response for response in responses if response.status_code == 409)
    assert loser.json()["code"] in {"PURCHASE.OPERATION_IN_PROGRESS", "PURCHASE.VERSION_CONFLICT", "PURCHASE.INVALID_STATUS"}
    assert len(fakes.inventory.entries()) == 1


def test_same_key_concurrently_applies_once(test_client, user_token, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    fakes.inventory.availability.latency = 0.2
    barrier = threading.Barrier(3)
    responses = []

    def attempt() -> None:
        barrier.wait(5)
        responses.append(
            test_client.post(
                f"{base(world)}/purchases/{draft['id']}/confirmation",
                json={"version": draft["version"]},
                headers={"Authorization": f"Bearer {user_token('compras.test')}", "Idempotency-Key": key},
            )
        )

    threads = [threading.Thread(target=attempt) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert len(fakes.inventory.entries()) == 1
    assert {response.status_code for response in responses} <= {200, 409}
    numbers = {response.json().get("number") for response in responses if response.status_code == 200}
    assert len(numbers) == 1
