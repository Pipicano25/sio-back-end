"""Cliente de token técnico `client_credentials` (R-06; T016)."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

import httpx
import pytest

from purchase_service.infrastructure.keycloak_token_client import KeycloakTokenClient, TokenUnavailableError

SECRET = "secreto-muy-privado"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def client(handler, clock=None) -> KeycloakTokenClient:
    return KeycloakTokenClient(
        token_url="http://keycloak.test/realms/sio/protocol/openid-connect/token",
        client_id="purchase-service",
        client_secret=SECRET,
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
        clock=clock or Clock(),
    )


def test_client_credentials_and_cache_until_60s_before_expiry() -> None:
    requests = []
    clock = Clock()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"access_token": f"t{len(requests)}", "expires_in": 300})

    tokens = client(handler, clock)
    assert tokens.get_token() == "t1"
    clock.now += 239
    assert tokens.get_token() == "t1"
    clock.now += 2  # quedan menos de 60 s
    assert tokens.get_token() == "t2"
    assert requests[0] == {"grant_type": ["client_credentials"], "client_id": ["purchase-service"],
                           "client_secret": [SECRET]}


def test_invalidate_forces_a_new_token() -> None:
    count = []

    def handler(request):
        count.append(1)
        return httpx.Response(200, json={"access_token": f"t{len(count)}", "expires_in": 300})

    tokens = client(handler)
    tokens.get_token()
    tokens.invalidate()
    assert tokens.get_token() == "t2"


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(401, json={"error": "invalid_client"}),
        lambda request: httpx.Response(200, json={}),
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("caido")),
    ],
)
def test_keycloak_unavailable_without_leaking_the_secret(handler, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(TokenUnavailableError):
        client(handler).get_token()
    assert SECRET not in caplog.text
    assert SECRET not in repr(client(handler))
