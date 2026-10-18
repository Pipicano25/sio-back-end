"""Registro de llamadas por solicitud (T075; FR-022-138, CP-101)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from product_inventory_query_service.application.call_registry import CallRegistry


def test_same_operation_and_arguments_run_once_even_concurrently() -> None:
    a, b = uuid4(), uuid4()
    runs = []

    async def work(label):
        runs.append(label)
        await asyncio.sleep(0)
        return label

    async def run():
        registry = CallRegistry()
        results = await asyncio.gather(
            registry.once("balances", [a, b], lambda: work("1")),
            registry.once("balances", [b, a, a], lambda: work("2")),
            registry.once("balances", [a], lambda: work("3")),
            registry.once("policies", [a, b], lambda: work("4")),
        )
        return registry, results

    registry, results = asyncio.run(run())
    assert results == ["1", "1", "3", "4"]
    assert runs == ["1", "3", "4"]
    assert registry.executed["balances"] == 2


def test_registry_is_per_request() -> None:
    async def run():
        first, second = CallRegistry(), CallRegistry()
        calls = []

        async def work():
            calls.append(1)
            return 1

        await first.once("op", 1, work)
        first.close()
        await second.once("op", 1, work)
        return calls

    assert asyncio.run(run()) == [1, 1]
