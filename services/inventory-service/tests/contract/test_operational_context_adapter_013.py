"""Adaptador de Operational Context: acceso a la sucursal y moneda (`dependencies-delta.md`; T010)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from inventory_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from tests.contract.test_operational_context_adapter import BASE, Tokens, access, technical


def test_branch_access_uses_the_user_token_and_returns_the_raw_result() -> None:
    branch, company, user = uuid4(), uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "allowed": True,
                "reason": None,
                "keycloak_user_id": "sub-x",
                "company_id": str(company),
                "branch_id": str(branch),
                "application_user_id": str(user),
                "permission": None,
            },
        )

    result = access(handler).check_branch(branch)
    assert seen["url"] == f"{BASE}/operational-access?branch_id={branch}"
    assert seen["auth"] == "Bearer token-del-usuario"  # nunca el técnico
    assert (result.allowed, result.reason, result.company_id, result.application_user_id) == (True, None, company, user)


@pytest.mark.parametrize(
    "reason",
    ["USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE", "BRANCH_NOT_ASSIGNED", "USER_BRANCH_INACTIVE", "BRANCH_INACTIVE", "COMPANY_INACTIVE"],
)
def test_branch_access_denials_are_returned_with_their_reason(reason) -> None:
    company = uuid4()
    body = {"allowed": False, "reason": reason, "company_id": str(company), "application_user_id": None}
    result = access(lambda request: httpx.Response(200, json=body)).check_branch(uuid4())
    assert (result.allowed, result.reason, result.company_id, result.application_user_id) == (False, reason, company, None)


def test_company_access_returns_application_user() -> None:
    company, user = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(
            200, json={"allowed": True, "reason": None, "company_id": str(company), "application_user_id": str(user)}
        )

    result = access(handler).check_company(company)
    assert seen["url"] == f"{BASE}/operational-access?company_id={company}"
    assert (result.allowed, result.application_user_id) == (True, user)


def test_branch_access_403_and_unavailable() -> None:
    with pytest.raises(OperationalAccessDeniedError):
        access(lambda request: httpx.Response(403)).check_branch(uuid4())
    for response in (
        httpx.Response(500),
        httpx.Response(401),
        httpx.Response(200, text="no-json"),
        httpx.Response(200, json={"reason": None}),
        httpx.Response(200, json={"allowed": True, "company_id": "no-uuid"}),
    ):
        with pytest.raises(DependencyUnavailableError) as error:
            access(lambda request, response=response: response).check_branch(uuid4())
        assert error.value.provider == "operational-context"


def test_company_currency_with_technical_token() -> None:
    company = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"id": str(company), "default_currency": "COP", "status": "ACTIVE"})

    assert technical(handler).get_company_currency(company) == "COP"
    assert seen["url"] == f"{BASE}/companies/{company}"
    assert seen["auth"] == "Bearer tecnico-1"


def test_company_not_found_is_none_and_token_renewed_once() -> None:
    tokens = Tokens()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.headers["authorization"])
        return httpx.Response(401) if len(calls) == 1 else httpx.Response(404)

    assert technical(handler, tokens).get_company_currency(uuid4()) is None
    assert tokens.invalidated == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(403),
        httpx.Response(200, json={"id": "x"}),
        httpx.Response(200, json={"default_currency": "pesos"}),
        httpx.Response(200, json={"default_currency": 5}),
    ],
)
def test_company_currency_unavailable_answers(response) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        technical(lambda request: response).get_company_currency(uuid4())
    assert error.value.provider == "operational-context"
