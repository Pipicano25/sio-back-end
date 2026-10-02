"""Adaptador de membresía contra Operational Context (T034; FR-025–FR-028, RC-06, RC-19).

Vía técnica de `operational-access`: token `client_credentials` propio, `sub`
del usuario como `keycloak_user_id`, sin `permission`. Ante el primer `401` se
renueva el token y se repite exactamente una vez (renovación técnica).
"""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import httpx
import pytest

from party_identity_service.application.exceptions import (
    KEYCLOAK_TOKEN_UNAVAILABLE,
    OPERATIONAL_CONTEXT_UNAVAILABLE,
    OPERATIONAL_CONTEXT_VALIDATION_DENIED,
    CompanyInactiveError,
    CompanyNotFoundError,
    ConfirmationMembershipInvalidError,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.keycloak_token_client import TokenRequestError
from party_identity_service.infrastructure.operational_context_membership_resolver import (
    HTTPOperationalContextMembershipResolver,
)
from party_identity_service.observability import reset_trace_id, set_trace_id

COMPANY = uuid4()
APPLICATION_USER = uuid4()
SUB = "8f2c-user-sub"


class FakeTokens:
    """Doble del token en caché: entrega tokens numerados y cuenta invalidaciones."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.issued = 0
        self.invalidations = 0
        self._current: str | None = None

    def get(self) -> str:
        if self.fail:
            raise TokenRequestError("Keycloak rechazó la solicitud de token.")
        if self._current is None:
            self.issued += 1
            self._current = f"technical-{self.issued}"
        return self._current

    def invalidate(self) -> None:
        self.invalidations += 1
        self._current = None


def _body(**overrides) -> dict:
    body = {
        "allowed": True,
        "reason": None,
        "keycloak_user_id": SUB,
        "company_id": str(COMPANY),
        "branch_id": None,
        "application_user_id": str(APPLICATION_USER),
        "permission": None,
    }
    body.update(overrides)
    return body


def _json(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body), headers={"content-type": "application/json"})


def _resolver(handler, tokens: FakeTokens | None = None) -> HTTPOperationalContextMembershipResolver:
    return HTTPOperationalContextMembershipResolver(
        base_url="http://oc.test/api/v1/",
        tokens=tokens or FakeTokens(),
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def test_request_uses_technical_token_and_exact_parameters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _json(200, _body())

    token = set_trace_id("4bf92f3577b34da6a3ce929d0e0e4736")
    try:
        result = _resolver(handler).resolve(company_id=COMPANY, keycloak_user_id=SUB)
    finally:
        reset_trace_id(token)

    assert result == APPLICATION_USER
    request = seen[0]
    assert request.url.path == "/api/v1/operational-access"
    assert dict(request.url.params) == {"company_id": str(COMPANY), "keycloak_user_id": SUB}
    assert request.headers["authorization"] == "Bearer technical-1"
    assert "4bf92f3577b34da6a3ce929d0e0e4736" in request.headers["traceparent"]


def test_company_inactive() -> None:
    handler = lambda request: _json(200, _body(allowed=False, reason="COMPANY_INACTIVE", application_user_id=None))
    with pytest.raises(CompanyInactiveError):
        _resolver(handler).resolve(company_id=COMPANY, keycloak_user_id=SUB)


@pytest.mark.parametrize("reason", ["USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"])
def test_membership_invalid_carries_reason(reason: str) -> None:
    handler = lambda request: _json(200, _body(allowed=False, reason=reason, application_user_id=None))
    with pytest.raises(ConfirmationMembershipInvalidError) as error:
        _resolver(handler).resolve(company_id=COMPANY, keycloak_user_id=SUB)
    assert error.value.reason == reason


def test_company_not_found() -> None:
    with pytest.raises(CompanyNotFoundError):
        _resolver(lambda request: httpx.Response(404)).resolve(company_id=COMPANY, keycloak_user_id=SUB)


def test_first_401_renews_token_and_retries_exactly_once() -> None:
    tokens = FakeTokens()
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["authorization"])
        if len(seen) == 1:
            return httpx.Response(401)
        return _json(200, _body())

    assert _resolver(handler, tokens).resolve(company_id=COMPANY, keycloak_user_id=SUB) == APPLICATION_USER
    assert seen == ["Bearer technical-1", "Bearer technical-2"]
    assert tokens.invalidations == 1


def test_second_401_is_unavailable_without_more_retries(caplog) -> None:
    caplog.set_level(logging.WARNING)
    tokens = FakeTokens()
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401)

    with pytest.raises(DependencyUnavailableError) as error:
        _resolver(handler, tokens).resolve(company_id=COMPANY, keycloak_user_id=SUB)

    assert len(calls) == 2
    assert error.value.dependency == "operational-context"
    assert error.value.cause == OPERATIONAL_CONTEXT_VALIDATION_DENIED
    assert OPERATIONAL_CONTEXT_VALIDATION_DENIED in caplog.text


def test_403_is_unavailable_without_retry() -> None:
    tokens = FakeTokens()
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(403)

    with pytest.raises(DependencyUnavailableError) as error:
        _resolver(handler, tokens).resolve(company_id=COMPANY, keycloak_user_id=SUB)

    assert len(calls) == 1 and tokens.invalidations == 0
    assert error.value.cause == OPERATIONAL_CONTEXT_VALIDATION_DENIED


def _raise(exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception("fallo", request=request)

    return handler


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500),
        lambda request: httpx.Response(422),
        lambda request: _json(200, _body(allowed=False, reason="BRANCH_INACTIVE", application_user_id=None)),
        lambda request: _json(200, _body(application_user_id=None)),
        lambda request: _json(200, {"allowed": True}),
        lambda request: httpx.Response(200, content=b"no-json"),
        _raise(httpx.ReadTimeout),
        _raise(httpx.ConnectError),
    ],
)
def test_other_failures_are_unavailable_without_retry(handler) -> None:
    tokens = FakeTokens()

    with pytest.raises(DependencyUnavailableError) as error:
        _resolver(handler, tokens).resolve(company_id=COMPANY, keycloak_user_id=SUB)

    assert error.value.dependency == "operational-context"
    assert error.value.cause == OPERATIONAL_CONTEXT_UNAVAILABLE
    assert tokens.invalidations == 0


def test_token_failure_is_keycloak_dependency() -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        _resolver(lambda request: _json(200, _body()), FakeTokens(fail=True)).resolve(
            company_id=COMPANY, keycloak_user_id=SUB
        )

    assert error.value.dependency == "keycloak"
    assert error.value.cause == KEYCLOAK_TOKEN_UNAVAILABLE
