"""Adaptador de Operational Context con `httpx.MockTransport` (FR-033, FR-050; T040)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from audit_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from audit_service.infrastructure.operational_context_directory import HTTPCompanyAccessDirectory

BASE = "http://operational-context.test/api/v1"
AUTH = "Bearer token-del-usuario"


def directory(handler) -> HTTPCompanyAccessDirectory:
    return HTTPCompanyAccessDirectory(
        base_url=BASE, authorization=AUTH, timeout_seconds=1.0, transport=httpx.MockTransport(handler)
    )


def test_request_shape() -> None:
    company = uuid4()
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"allowed": True})

    assert directory(handler).check_company_access(company).member_active is True
    [request] = seen
    assert request.url.path == "/api/v1/operational-access"
    assert request.url.params["company_id"] == str(company)
    assert request.headers["authorization"] == AUTH
    assert "keycloak_user_id" not in request.url.params


@pytest.mark.parametrize(
    ("body", "member"),
    [
        ({"allowed": True}, True),
        ({"allowed": False, "reason": "COMPANY_INACTIVE"}, True),
        ({"allowed": False, "reason": "USER_NOT_MEMBER"}, False),
        ({"allowed": False, "reason": "USER_MEMBERSHIP_INACTIVE"}, False),
    ],
)
def test_access_mapping(body, member) -> None:
    result = directory(lambda request: httpx.Response(200, json=body)).check_company_access(uuid4())
    assert result.member_active is member


def test_forbidden_maps_to_operational_access_denied() -> None:
    with pytest.raises(OperationalAccessDeniedError):
        directory(lambda request: httpx.Response(403, json={})).check_company_access(uuid4())


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={}),
        httpx.Response(500, json={}),
        httpx.Response(503, json={}),
        httpx.Response(200, text="no-json"),
        httpx.Response(200, json={"allowed": "si"}),
        httpx.Response(200, json={"allowed": False, "reason": "OTRA"}),
    ],
)
def test_unexpected_responses_are_unavailable(response) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        directory(lambda request: response).check_company_access(uuid4())
    assert error.value.provider == "operational-context"


@pytest.mark.parametrize("exc", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_network_errors_are_unavailable(exc) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    with pytest.raises(DependencyUnavailableError):
        directory(handler).check_company_access(uuid4())
