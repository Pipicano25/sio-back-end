"""Cliente de token técnico `client_credentials` (R-05, Principio IX)."""

from __future__ import annotations

import logging

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    KEYCLOAK_TOKEN_REJECTED,
    DependencyUnavailableError,
)
from commercial_relationship_service.infrastructure.keycloak_token_client import (
    KeycloakTokenClient,
)

SECRET = "super-secret-value"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _client(handler, clock=None) -> KeycloakTokenClient:
    return KeycloakTokenClient(
        base_url="http://kc.test",
        realm="sio",
        client_id="commercial-relationship-service",
        client_secret=SECRET,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
        clock=clock or Clock(),
    )


def test_requests_client_credentials_and_reuses_token():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.path == "/realms/sio/protocol/openid-connect/token"
        body = request.content.decode()
        assert "grant_type=client_credentials" in body
        assert "client_id=commercial-relationship-service" in body
        return httpx.Response(200, json={"access_token": f"token-{len(calls)}", "expires_in": 300})

    clock = Clock()
    client = _client(handler, clock)

    assert client.get_token() == "token-1"
    clock.now += 200  # quedan 100 s > margen de 30 s
    assert client.get_token() == "token-1"
    clock.now += 80  # quedan 20 s < 30 s: se renueva
    assert client.get_token() == "token-2"
    assert len(calls) == 2


def test_invalidate_forces_new_token():
    counter = {"n": 0}

    def handler(request):
        counter["n"] += 1
        return httpx.Response(200, json={"access_token": f"t{counter['n']}", "expires_in": 300})

    client = _client(handler)
    assert client.get_token() == "t1"
    client.invalidate()
    assert client.get_token() == "t2"


@pytest.mark.parametrize(
    "response",
    [httpx.Response(401), httpx.Response(500), httpx.Response(200, json={}), httpx.Response(200, text="x")],
)
def test_rejected_token_is_product_catalog_unavailable(response, caplog):
    caplog.set_level(logging.ERROR)

    with pytest.raises(DependencyUnavailableError) as error:
        _client(lambda request: response).get_token()

    assert error.value.provider == "product-catalog"
    assert error.value.cause == KEYCLOAK_TOKEN_REJECTED
    assert SECRET not in caplog.text


def test_network_error_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(DependencyUnavailableError):
        _client(handler).get_token()


def test_repr_never_shows_secret_or_token():
    client = _client(lambda request: httpx.Response(200, json={"access_token": "the-token"}))
    client.get_token()
    assert SECRET not in repr(client)
    assert "the-token" not in repr(client)
