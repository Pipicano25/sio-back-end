"""Cliente de token técnico `client_credentials` (R-06; T018)."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

import httpx
import pytest

from sales_service.infrastructure.keycloak_token_client import KeycloakTokenClient, TokenUnavailableError

SECRET = "secreto-muy-privado"


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def client(handler, clock=None, background=None) -> KeycloakTokenClient:
    return KeycloakTokenClient(
        background=background or (lambda task: None),
        token_url="http://keycloak.test/realms/sio/protocol/openid-connect/token",
        client_id="sales-service",
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
    assert requests[0] == {"grant_type": ["client_credentials"], "client_id": ["sales-service"],
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


def test_renews_in_background_before_the_hard_margin() -> None:
    """La renovación anticipada no hace esperar a la solicitud (Keycloak puede tardar segundos)."""
    requests = []
    clock = Clock()
    pending = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(1)
        return httpx.Response(200, json={"access_token": f"t{len(requests)}", "expires_in": 300})

    tokens = client(handler, clock, background=pending.append)
    assert tokens.get_token() == "t1"
    clock.now += 179
    assert tokens.get_token() == "t1" and pending == []  # quedan 121 s: sin renovar
    clock.now += 2  # quedan 119 s: renovación en segundo plano, la solicitud usa el vigente
    assert tokens.get_token() == "t1" and len(pending) == 1
    assert tokens.get_token() == "t1" and len(pending) == 1  # una sola renovación en curso
    pending.pop()()  # el hilo de fondo termina
    assert tokens.get_token() == "t2" and len(requests) == 2


def test_failed_background_renewal_falls_back_to_the_synchronous_one(caplog) -> None:
    clock = Clock()
    pending = []
    answers = iter([httpx.Response(200, json={"access_token": "t1", "expires_in": 300}),
                    httpx.Response(503),
                    httpx.Response(200, json={"access_token": "t3", "expires_in": 300})])
    tokens = client(lambda request: next(answers), clock, background=pending.append)
    assert tokens.get_token() == "t1"
    clock.now += 200
    assert tokens.get_token() == "t1"
    pending.pop()()  # falla: se registra y se conserva el vigente
    assert tokens.get_token() == "t1"
    clock.now += 50  # quedan 50 s: renovación síncrona
    assert tokens.get_token() == "t3"
    assert SECRET not in caplog.text
