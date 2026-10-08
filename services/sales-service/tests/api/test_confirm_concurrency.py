"""Confirmaciones concurrentes de la misma venta (Historia 2 escenarios 3 y 5; RC-01, RC-04; T056)."""

from __future__ import annotations

import threading

from tests.conftest import base, line, new_key


def test_two_keys_same_sale_only_one_applies(test_client, user_token, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.availability.latency = 0.3  # la primera queda dentro de Inventory mientras llega la segunda
    barrier = threading.Barrier(2)
    responses = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait(5)
        response = test_client.post(
            f"{base(world)}/sales/{draft['id']}/confirmation",
            json={"version": draft["version"]},
            headers={"Authorization": f"Bearer {user_token('ventas.test')}", "Idempotency-Key": new_key()},
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
    assert loser.json()["code"] in {"SALES.OPERATION_IN_PROGRESS", "SALES.VERSION_CONFLICT", "SALES.INVALID_STATUS"}
    assert len(fakes.inventory.outputs()) == 1


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
                f"{base(world)}/sales/{draft['id']}/confirmation",
                json={"version": draft["version"]},
                headers={"Authorization": f"Bearer {user_token('ventas.test')}", "Idempotency-Key": key},
            )
        )

    threads = [threading.Thread(target=attempt) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert len(fakes.inventory.outputs()) == 1
    assert {response.status_code for response in responses} <= {200, 409}
    numbers = {response.json().get("number") for response in responses if response.status_code == 200}
    assert len(numbers) == 1


def test_twenty_sales_of_the_last_unit_confirm_exactly_one(test_client, user_token, world, fakes, make_sequence, make_draft) -> None:
    """RC-04 / SC-003: Inventory serializa la última unidad; las demás ventas se rechazan por existencias."""
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "1", "1000")
    drafts = [make_draft(line(world.product, "1")) for _ in range(20)]
    barrier = threading.Barrier(len(drafts))
    responses = []
    lock = threading.Lock()

    def attempt(draft) -> None:
        barrier.wait(10)
        response = test_client.post(
            f"{base(world)}/sales/{draft['id']}/confirmation",
            json={"version": draft["version"]},
            headers={"Authorization": f"Bearer {user_token('ventas.test')}", "Idempotency-Key": new_key()},
        )
        with lock:
            responses.append(response)

    threads = [threading.Thread(target=attempt, args=(draft,)) for draft in drafts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200] + [409] * 19, [response.text for response in responses if response.status_code != 409]
    assert {response.json()["code"] for response in responses if response.status_code == 409} == {"SALES.INSUFFICIENT_STOCK"}
    assert len(fakes.inventory.outputs()) == 1
    assert fakes.inventory.balance(world.branch, world.product) == 0
