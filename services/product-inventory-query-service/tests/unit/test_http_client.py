"""Cliente HTTP asíncrono (T060; FR-022-75, FR-022-76, RNF-022-3, CP-66)."""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.request_context import RequestBudget, request_budget
from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient, TechnicalCaller
from product_inventory_query_service.observability import SERVICE_LOGGER, reset_trace_id, set_trace_id

TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZWNuaWNvIn0.firma-del-token"


def _client(handler, timeout: float = 3.0) -> AsyncDependencyClient:
    return AsyncDependencyClient(provider="inventory", base_url="http://inv.test/api/v1", timeout_seconds=timeout,
                                 transport=httpx.MockTransport(handler))


class Tokens:
    def __init__(self, values=("t1", "t2")) -> None:
        self.values = list(values)
        self.invalidated = 0

    async def token(self) -> str:
        return self.values[min(self.invalidated, len(self.values) - 1)]

    def invalidate(self) -> None:
        self.invalidated += 1


def test_timeout_and_network_errors_are_dependency_unavailable() -> None:
    def timeout(request):
        raise httpx.ReadTimeout("lento", request=request)

    def network(request):
        raise httpx.ConnectError("caído", request=request)

    for handler, cause in ((timeout, "tiempo_agotado"), (network, "error_de_red")):
        with pytest.raises(DependencyUnavailableError) as exc:
            asyncio.run(_client(handler).send("op", "GET", "/x", authorization=None))
        assert exc.value.cause == cause and exc.value.provider == "inventory"


def test_traceparent_keeps_trace_id_and_log_has_no_token_or_body(caplog) -> None:
    seen = {}

    def handler(request):
        seen.update(request.headers)
        return httpx.Response(200, json={"secreto": "no-va-al-log"})

    token = set_trace_id(TRACE)
    try:
        with caplog.at_level(logging.INFO, logger=SERVICE_LOGGER):
            logging.getLogger(SERVICE_LOGGER).propagate = True
            asyncio.run(_client(handler).send("balances_lookup", "POST", "/x", authorization=f"Bearer {TOKEN}", json={"a": 1}))
    finally:
        logging.getLogger(SERVICE_LOGGER).propagate = False
        reset_trace_id(token)
    assert seen["traceparent"].split("-")[1] == TRACE
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "proveedor=inventory operacion=balances_lookup estado=200 duracion_ms=" in text
    assert TOKEN not in text and "no-va-al-log" not in text and "Bearer" not in text


def test_concurrency_is_limited_by_the_request_semaphore() -> None:
    active = {"now": 0, "max": 0}

    async def handler(request):
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        await asyncio.sleep(0.01)
        active["now"] -= 1
        return httpx.Response(200, json={})

    async def run() -> None:
        client = _client(handler)
        with request_budget(RequestBudget(total_seconds=8, max_parallel_calls=3)):
            await asyncio.gather(*(client.send("op", "GET", f"/x/{i}", authorization=None) for i in range(12)))

    asyncio.run(run())
    assert active["max"] == 3


def test_exhausted_budget_prevents_the_call_and_caps_the_timeout() -> None:
    calls = []

    def handler(request):
        calls.append(request.extensions.get("timeout"))
        return httpx.Response(200, json={})

    clock = {"now": 0.0}

    async def run() -> None:
        client = _client(handler, timeout=3.0)
        budget = RequestBudget(total_seconds=8, max_parallel_calls=4, clock=lambda: clock["now"])
        with request_budget(budget):
            clock["now"] = 6.5
            await client.send("op", "GET", "/x", authorization=None)
            clock["now"] = 8.0
            with pytest.raises(DependencyUnavailableError) as exc:
                await client.send("op", "GET", "/x", authorization=None)
            assert exc.value.cause == "presupuesto_agotado"

    asyncio.run(run())
    assert len(calls) == 1
    assert calls[0]["read"] == pytest.approx(1.5)


def test_technical_caller_renews_once_on_401_then_fails_on_second_401_or_403(caplog) -> None:
    statuses = iter([401, 200])
    seen_tokens = []

    def handler(request):
        seen_tokens.append(request.headers["authorization"])
        return httpx.Response(next(statuses), json={"ok": True})

    tokens = Tokens()
    assert asyncio.run(TechnicalCaller(_client(handler), tokens).json("op", "GET", "/x")) == {"ok": True}
    assert seen_tokens == ["Bearer t1", "Bearer t2"] and tokens.invalidated == 1

    for sequence in ([401, 401], [403]):
        responses = iter(sequence)

        def failing(request, responses=responses):
            return httpx.Response(next(responses), json={})

        with pytest.raises(DependencyUnavailableError) as exc:
            asyncio.run(TechnicalCaller(_client(failing), Tokens()).json("op", "GET", "/x"))
        assert exc.value.cause == "identidad_tecnica_rechazada"


def test_non_200_or_invalid_json_is_dependency_unavailable() -> None:
    for response in (httpx.Response(500, json={}), httpx.Response(200, content=b"no es json")):
        with pytest.raises(DependencyUnavailableError):
            asyncio.run(TechnicalCaller(_client(lambda r, response=response: response), Tokens()).json("op", "GET", "/x"))
