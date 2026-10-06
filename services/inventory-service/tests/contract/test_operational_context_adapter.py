"""Adaptadores de Operational Context con `httpx.MockTransport` (contracts/dependencies.md; T014)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from inventory_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from inventory_service.infrastructure.operational_context_directory import (
    HTTPCompanyAccessDirectory,
    HTTPOperationalContextDirectory,
)

BASE = "http://oc.test/api/v1"


class Tokens:
    def __init__(self) -> None:
        self.issued = 0
        self.invalidated = 0

    def get_token(self) -> str:
        self.issued += 1
        return f"tecnico-{self.issued}"

    def invalidate(self) -> None:
        self.invalidated += 1


def technical(handler, tokens: Tokens | None = None) -> HTTPOperationalContextDirectory:
    return HTTPOperationalContextDirectory(
        base_url=BASE, timeout_seconds=1, tokens=tokens or Tokens(), transport=httpx.MockTransport(handler)
    )


def test_branch_with_technical_token_and_mapping() -> None:
    branch, company = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"id": str(branch), "company_id": str(company), "status": "ACTIVE",
                                         "company_status": "INACTIVE", "code": "X", "version": 1})

    info = technical(handler).get_branch(branch)
    assert seen["url"] == f"{BASE}/branches/{branch}"
    assert seen["auth"] == "Bearer tecnico-1"
    assert (info.company_id, info.status, info.company_status) == (company, "ACTIVE", "INACTIVE")


def test_branch_404_is_none_and_user_mapping() -> None:
    user, company, keycloak = uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        if "/branches/" in request.url.path:
            return httpx.Response(404, json={})
        return httpx.Response(200, json={"id": str(user), "company_id": str(company), "status": "INACTIVE",
                                         "keycloak_user_id": str(keycloak)})

    directory = technical(handler)
    assert directory.get_branch(uuid4()) is None
    info = directory.get_application_user(user)
    assert (info.company_id, info.status, info.keycloak_user_id) == (company, "INACTIVE", keycloak)


def test_token_renewed_once_on_401() -> None:
    tokens = Tokens()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers["authorization"])
        if len(calls) == 1:
            return httpx.Response(401)
        return httpx.Response(404)

    assert technical(handler, tokens).get_branch(uuid4()) is None
    assert calls == ["Bearer tecnico-1", "Bearer tecnico-2"]
    assert tokens.invalidated == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(503),
        httpx.Response(403),
        httpx.Response(401),
        httpx.Response(200, text="no-json"),
        httpx.Response(200, json={"id": "x"}),
    ],
)
def test_unavailable_answers(response) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        technical(lambda request: response).get_branch(uuid4())
    assert error.value.provider == "operational-context"


def test_network_error_and_timeout_are_unavailable() -> None:
    def broken(request):
        raise httpx.ConnectError("caido")

    def slow(request):
        raise httpx.ReadTimeout("lento")

    for handler in (broken, slow):
        with pytest.raises(DependencyUnavailableError):
            technical(handler).get_application_user(uuid4())


def access(handler, authorization="Bearer token-del-usuario") -> HTTPCompanyAccessDirectory:
    return HTTPCompanyAccessDirectory(
        base_url=BASE, authorization=authorization, timeout_seconds=1, transport=httpx.MockTransport(handler)
    )


def test_operational_access_uses_the_user_token() -> None:
    company = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"allowed": True, "reason": None})

    assert access(handler).is_member(company) is True
    assert seen["url"] == f"{BASE}/operational-access?company_id={company}"
    assert seen["auth"] == "Bearer token-del-usuario"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"allowed": False, "reason": "USER_NOT_MEMBER"}, False),
        ({"allowed": False, "reason": "USER_MEMBERSHIP_INACTIVE"}, False),
        ({"allowed": False, "reason": "COMPANY_INACTIVE"}, True),
    ],
)
def test_operational_access_reasons(body, expected) -> None:
    assert access(lambda request: httpx.Response(200, json=body)).is_member(uuid4()) is expected


def test_operational_access_403_and_unavailable() -> None:
    with pytest.raises(OperationalAccessDeniedError):
        access(lambda request: httpx.Response(403)).is_member(uuid4())
    for response in (httpx.Response(500), httpx.Response(401), httpx.Response(200, json={"x": 1})):
        with pytest.raises(DependencyUnavailableError):
            access(lambda request, response=response: response).is_member(uuid4())
