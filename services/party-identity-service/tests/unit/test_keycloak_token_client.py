"""Pruebas del cliente de token `client_credentials` (FR-018, U3, Principio IX)."""

from urllib.parse import parse_qs

import httpx
import pytest

from party_identity_service.infrastructure.keycloak_token_client import (
    TokenRequestError,
    fetch_client_credentials_token,
)

TOKEN_URL = "http://keycloak.test/realms/sio/protocol/openid-connect/token"
SECRET = "super-secreto-de-prueba"


def _fetch(handler, timeout=4.0):
    return fetch_client_credentials_token(
        TOKEN_URL,
        "party-identity-service",
        SECRET,
        timeout=timeout,
        transport=httpx.MockTransport(handler),
    )


def test_sends_client_credentials_and_returns_token() -> None:
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["form"] = parse_qs(request.content.decode())
        seen["timeout"] = request.extensions["timeout"]
        return httpx.Response(200, json={"access_token": "token-tecnico"})

    assert _fetch(handler, timeout=4.0) == "token-tecnico"
    assert seen["url"] == TOKEN_URL
    assert seen["form"] == {
        "grant_type": ["client_credentials"],
        "client_id": ["party-identity-service"],
        "client_secret": [SECRET],
    }
    assert seen["timeout"]["read"] == 4.0


@pytest.mark.parametrize("status", [400, 401, 500])
def test_error_status_does_not_expose_secret(status) -> None:
    with pytest.raises(TokenRequestError) as error:
        _fetch(lambda request: httpx.Response(status, json={"error": "x"}))

    assert SECRET not in str(error.value)


@pytest.mark.parametrize("exception", [httpx.ConnectError("sin red"), httpx.ReadTimeout("tiempo")])
def test_network_errors_and_timeouts(exception) -> None:
    def handler(request):
        raise exception

    with pytest.raises(TokenRequestError) as error:
        _fetch(handler)

    assert SECRET not in str(error.value)


def test_response_without_token_is_error() -> None:
    with pytest.raises(TokenRequestError):
        _fetch(lambda request: httpx.Response(200, json={}))


# --------------------------------------------------------------------------
# Token en caché para la API (T032; R-06, política de Operational Context)
# --------------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _cached(handler, clock):
    from party_identity_service.infrastructure.keycloak_token_client import (
        CachedClientCredentialsToken,
    )

    return CachedClientCredentialsToken(
        token_url=TOKEN_URL,
        client_id="party-identity-service",
        client_secret=SECRET,
        timeout_seconds=2.0,
        transport=httpx.MockTransport(handler),
        clock=clock,
    )


def test_cached_token_is_reused_and_renewed_before_expiry() -> None:
    issued = []

    def handler(request):
        issued.append(1)
        return httpx.Response(200, json={"access_token": f"token-{len(issued)}", "expires_in": 300})

    clock = _Clock()
    cache = _cached(handler, clock)

    assert cache.get() == "token-1"
    clock.now += 200
    assert cache.get() == "token-1"
    clock.now += 80  # quedan 20 s (< margen de 30 s): se renueva
    assert cache.get() == "token-2"
    assert len(issued) == 2


def test_invalidate_forces_new_token() -> None:
    issued = []

    def handler(request):
        issued.append(1)
        return httpx.Response(200, json={"access_token": f"token-{len(issued)}", "expires_in": 300})

    cache = _cached(handler, _Clock())
    assert cache.get() == "token-1"
    cache.invalidate()
    assert cache.get() == "token-2"


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(401, json={"error": "unauthorized_client"}),
        lambda request: httpx.Response(200, json={"token_type": "bearer"}),
    ],
)
def test_cached_token_errors_never_expose_secret(handler, caplog) -> None:
    cache = _cached(handler, _Clock())

    with pytest.raises(TokenRequestError) as error:
        cache.get()

    assert SECRET not in str(error.value)
    assert SECRET not in caplog.text
    assert SECRET not in repr(cache)
