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
