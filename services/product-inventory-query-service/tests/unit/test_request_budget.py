"""Presupuesto de tiempo de la solicitud (T093; RNF-022-3, FR-022-71, CP-65, CP-66).

3 s por dependencia y 8 s por solicitud. Al vencer, la llamada no sale y la solicitud responde `503` completo:
`partial` nunca aparece por un fallo.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.progressive_search import progressive_search
from product_inventory_query_service.application.request_context import RequestBudget, request_budget
from product_inventory_query_service.domain.pagination import Candidate
from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient
from tests.conftest import build_test_settings


def test_default_timeouts() -> None:
    settings = build_test_settings()
    assert (settings.dependency_timeout_seconds, settings.request_budget_seconds) == (3.0, 8.0)


def test_budget_exhausted_mid_search_is_dependency_unavailable_not_partial() -> None:
    clock = {"now": 0.0}

    def handler(request):
        clock["now"] += 3.0  # cada llamada consume 3 s del presupuesto
        return httpx.Response(200, json={})

    client = AsyncDependencyClient(provider="commercial-relationship", base_url="http://cr.test", timeout_seconds=3,
                                   transport=httpx.MockTransport(handler))

    async def fetch(after, limit):
        await client.send("search", "POST", "/s", authorization=None)
        index = 0 if after is None else int(after["id"]) + 1
        return [Candidate(str(index), {"k": [], "id": str(index)})], True

    async def evaluator(candidates):
        return set()

    async def run():
        with request_budget(RequestBudget(8, 8, clock=lambda: clock["now"])):
            return await progressive_search(fetch, [evaluator], need=21, batch_size=40, max_batches=10,
                                            work_time_seconds=100)

    with pytest.raises(DependencyUnavailableError) as exc:
        asyncio.run(run())
    assert exc.value.cause == "presupuesto_agotado"


def test_dependency_timeout_is_3_seconds_while_the_budget_allows_it() -> None:
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"]["read"])
        return httpx.Response(200, json={})

    clock = {"now": 6.0}
    client = AsyncDependencyClient(provider="inventory", base_url="http://inv.test", timeout_seconds=3,
                                   transport=httpx.MockTransport(handler))

    async def run():
        with request_budget(RequestBudget(8, 8, clock=lambda: clock["now"])):
            await client.send("op", "GET", "/x", authorization=None)

    asyncio.run(run())
    assert seen == [pytest.approx(3.0)]
