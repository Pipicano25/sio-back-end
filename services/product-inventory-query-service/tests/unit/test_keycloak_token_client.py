"""Token técnico por `client_credentials` (T061; FR-022-72, FR-022-101, CP-68)."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import parse_qs

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from product_inventory_query_service.observability import SERVICE_LOGGER

SECRET = "secreto-del-cliente-tecnico"


def _client(handler, clock) -> KeycloakTokenClient:
    return KeycloakTokenClient(token_url="http://kc.test/token", client_id="product-inventory-query-service",
                               client_secret=SECRET, timeout_seconds=3, transport=httpx.MockTransport(handler),
                               clock=lambda: clock["now"])


def test_caches_and_renews_60_seconds_before_expiry() -> None:
    issued = []

    def handler(request):
        form = parse_qs(request.content.decode())
        assert form["grant_type"] == ["client_credentials"]
        assert form["client_id"] == ["product-inventory-query-service"]
        issued.append(1)
        return httpx.Response(200, json={"access_token": f"token-{len(issued)}", "expires_in": 300})

    clock = {"now": 0.0}
    client = _client(handler, clock)

    async def run():
        assert await client.token() == "token-1"
        clock["now"] = 239.0
        assert await client.token() == "token-1"
        clock["now"] = 240.5
        assert await client.token() == "token-2"
        client.invalidate()
        assert await client.token() == "token-3"
        assert len(await asyncio.gather(*(client.token() for _ in range(10)))) == 10

    asyncio.run(run())
    assert len(issued) == 3


def test_failures_are_dependency_unavailable_and_never_log_the_secret(caplog) -> None:
    clock = {"now": 0.0}
    logger = logging.getLogger(SERVICE_LOGGER)
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger=SERVICE_LOGGER):
            for handler in (
                lambda r: httpx.Response(401, json={"error": "unauthorized_client"}),
                lambda r: httpx.Response(200, json={"sin_token": True}),
            ):
                with pytest.raises(DependencyUnavailableError):
                    asyncio.run(_client(handler, clock).token())
    finally:
        logger.propagate = False
    assert SECRET not in " ".join(record.getMessage() for record in caplog.records)
    assert SECRET not in repr(_client(lambda r: httpx.Response(200), clock))
