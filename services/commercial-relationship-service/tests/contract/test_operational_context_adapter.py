"""Adaptadores de Operational Context con `httpx.MockTransport` (R-02, R-07, RC-06).

Contrato: `specs/007-commercial-relationship-core/contracts/operational-context-dependency.md`.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    DependencyUnavailableError,
    NotFoundError,
    OperationalAccessDeniedError,
)
from commercial_relationship_service.infrastructure.operational_context_directory import (
    HTTPCompanyAccessDirectory,
    HTTPCompanyDirectory,
)
from commercial_relationship_service.observability import reset_trace_id, set_trace_id

BASE = "http://oc.test/api/v1"
TOKEN = "Bearer user-token"


def _access(handler) -> HTTPCompanyAccessDirectory:
    return HTTPCompanyAccessDirectory(
        base_url=BASE,
        authorization=TOKEN,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def _companies(handler) -> HTTPCompanyDirectory:
    return HTTPCompanyDirectory(
        base_url=BASE,
        authorization=TOKEN,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def test_access_uses_own_path_without_permission_and_propagates_headers():
    company = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        seen["headers"] = request.headers
        return httpx.Response(200, json={"allowed": True, "reason": None})

    token = set_trace_id("4bf92f3577b34da6a3ce929d0e0e4736")
    try:
        result = _access(handler).check_company_access(company)
    finally:
        reset_trace_id(token)

    assert result.member_active and result.company_active
    assert str(seen["url"]).startswith(f"{BASE}/operational-access")
    assert dict(seen["url"].params) == {"company_id": str(company)}
    assert seen["headers"]["authorization"] == TOKEN
    assert seen["headers"]["traceparent"].startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")


@pytest.mark.parametrize("reason", ["USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"])
def test_access_not_member(reason):
    result = _access(lambda request: httpx.Response(200, json={"allowed": False, "reason": reason})).check_company_access(uuid4())
    assert not result.member_active
    assert result.company_active is None


def test_access_company_inactive():
    result = _access(
        lambda request: httpx.Response(200, json={"allowed": False, "reason": "COMPANY_INACTIVE"})
    ).check_company_access(uuid4())
    assert result.member_active
    assert result.company_active is False


def test_access_forbidden_is_403_not_unavailable():
    with pytest.raises(OperationalAccessDeniedError):
        _access(lambda request: httpx.Response(403)).check_company_access(uuid4())


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(500),
        httpx.Response(502),
        httpx.Response(200, text="no-json"),
        httpx.Response(200, json={"reason": "X"}),
        httpx.Response(200, json={"allowed": False, "reason": "BRANCH_INACTIVE"}),
    ],
)
def test_access_unavailable(response):
    with pytest.raises(DependencyUnavailableError) as error:
        _access(lambda request: response).check_company_access(uuid4())
    assert error.value.provider == "operational-context"


@pytest.mark.parametrize("exception", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_access_network_errors(exception):
    def handler(request):
        raise exception

    with pytest.raises(DependencyUnavailableError) as error:
        _access(handler).check_company_access(uuid4())
    assert error.value.provider == "operational-context"


def test_company_organization():
    organization = uuid4()
    company = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/companies/{company}"
        assert request.headers["authorization"] == TOKEN
        return httpx.Response(
            200, json={"id": str(company), "organization_identity_id": str(organization), "legal_name": "x"}
        )

    assert _companies(handler).get_company_organization(company) == organization


def test_company_errors():
    with pytest.raises(NotFoundError):
        _companies(lambda request: httpx.Response(404)).get_company_organization(uuid4())

    with pytest.raises(OperationalAccessDeniedError):
        _companies(lambda request: httpx.Response(403)).get_company_organization(uuid4())

    for response in (httpx.Response(401), httpx.Response(503), httpx.Response(200, json={})):
        with pytest.raises(DependencyUnavailableError):
            _companies(lambda request, r=response: r).get_company_organization(uuid4())


def test_timeout_is_configured():
    directory = HTTPCompanyAccessDirectory(base_url=BASE, authorization=TOKEN, timeout_seconds=2.5)
    assert directory._client.timeout_seconds == 2.5


# ---------------------------------------------------------------------------
# Resumen de empresas (FR-046, DS-18)
# ---------------------------------------------------------------------------


def _membership(company, *, status="ACTIVE", company_status="ACTIVE"):
    return {
        "application_user_id": str(uuid4()),
        "company_id": str(company),
        "status": status,
        "company_status": company_status,
        "branches": [],
    }


def test_member_companies_only_active_memberships_sorted_with_user_token():
    first, second, inactive = sorted((uuid4(), uuid4(), uuid4()), key=str)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/me/operational-context"
        assert request.headers["authorization"] == TOKEN
        return httpx.Response(200, json={"keycloak_user_id": "sub", "memberships": [
            _membership(second, company_status="INACTIVE"),
            _membership(inactive, status="INACTIVE"),
            _membership(first),
        ]})

    companies = _access(handler).list_member_companies()

    assert [(c.company_id, c.company_status) for c in companies] == [(first, "ACTIVE"), (second, "INACTIVE")]


def test_member_companies_forbidden_is_403():
    with pytest.raises(OperationalAccessDeniedError):
        _access(lambda request: httpx.Response(403)).list_member_companies()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(500),
        httpx.Response(200, text="no-json"),
        httpx.Response(200, json={"memberships": "x"}),
        httpx.Response(200, json={"memberships": [{"company_id": "no-uuid", "status": "ACTIVE", "company_status": "ACTIVE"}]}),
        httpx.Response(200, json={"memberships": [{"company_id": str(uuid4()), "status": "RARO", "company_status": "ACTIVE"}]}),
    ],
)
def test_member_companies_unavailable(response):
    with pytest.raises(DependencyUnavailableError) as error:
        _access(lambda request: response).list_member_companies()
    assert error.value.provider == "operational-context"


@pytest.mark.parametrize("status", [403, 404])
def test_find_company_organization_hidden_is_none(status):
    assert _companies(lambda request: httpx.Response(status)).find_company_organization(uuid4()) is None


def test_find_company_organization():
    company, organization = uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/companies/{company}"
        assert request.headers["authorization"] == TOKEN
        return httpx.Response(200, json={"id": str(company), "organization_identity_id": str(organization)})

    assert _companies(handler).find_company_organization(company) == organization


@pytest.mark.parametrize("response", [httpx.Response(401), httpx.Response(503), httpx.Response(200, json={})])
def test_find_company_organization_unavailable(response):
    with pytest.raises(DependencyUnavailableError):
        _companies(lambda request: response).find_company_organization(uuid4())
