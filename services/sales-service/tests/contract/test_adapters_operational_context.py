"""Adaptador de Operational Context (`contracts/dependencies.md`; T015)."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from sales_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from sales_service.infrastructure.operational_context_directory import HTTPAccessDirectory, HTTPOperationalContextDirectory
from tests.contract.adapter_support import Recorder, Tokens, expired_then, json_response, timeout

BASE = "http://operational-context.test/api/v1"


def directory(handler, tokens=None) -> tuple[HTTPOperationalContextDirectory, Recorder, Tokens]:
    recorder, tokens = Recorder(handler), tokens or Tokens()
    return HTTPOperationalContextDirectory(base_url=BASE, timeout_seconds=1, tokens=tokens, transport=recorder.transport), recorder, tokens


def test_company_branch_and_user_with_technical_token() -> None:
    company, branch, user = uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Bearer tecnico-")
        if request.url.path.endswith(f"/companies/{company}"):
            return httpx.Response(200, json={"id": str(company), "status": "ACTIVE", "default_currency": "COP"})
        if request.url.path.endswith(f"/branches/{branch}"):
            return httpx.Response(
                200, json={"id": str(branch), "company_id": str(company), "status": "ACTIVE", "effective_timezone": "America/Bogota"}
            )
        return httpx.Response(200, json={"id": str(user), "company_id": str(company), "status": "INACTIVE"})

    adapter, recorder, _ = directory(handler)
    assert adapter.get_company(company).default_currency == "COP"
    assert adapter.get_branch(branch).effective_timezone == "America/Bogota"
    assert adapter.get_application_user(user).status == "INACTIVE"
    assert [request.url.path for request in recorder.requests] == [
        f"/api/v1/companies/{company}",
        f"/api/v1/branches/{branch}",
        f"/api/v1/application-users/{user}",
    ]


def test_404_is_none_and_401_renews_once() -> None:
    adapter, _, _ = directory(json_response(404))
    assert adapter.get_company(uuid4()) is None
    adapter, recorder, tokens = directory(expired_then({"id": "x", "status": "ACTIVE", "default_currency": "COP"}))
    assert adapter.get_company(uuid4()).status == "ACTIVE"
    assert tokens.invalidated == 1 and len(recorder.requests) == 2


@pytest.mark.parametrize("handler", [json_response(500), json_response(403), json_response(401), timeout, json_response(200, {"status": "ACTIVE"})])
def test_unavailable(handler) -> None:
    adapter, _, _ = directory(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        adapter.get_company(uuid4())
    assert error.value.provider == "operational-context"


def test_token_unavailable_is_dependency_error() -> None:
    adapter, _, _ = directory(json_response(200), Tokens(fail=True))
    with pytest.raises(DependencyUnavailableError):
        adapter.get_branch(uuid4())


def test_access_uses_user_token_never_technical() -> None:
    company, branch, user = uuid4(), uuid4(), uuid4()
    recorder = Recorder(
        lambda request: httpx.Response(
            200, json={"allowed": True, "reason": None, "company_id": str(company), "application_user_id": str(user)}
        )
    )
    access = HTTPAccessDirectory(base_url=BASE, authorization="Bearer usuario", timeout_seconds=1, transport=recorder.transport)
    result = access.check_branch(branch)
    assert result.allowed and result.application_user_id == user
    access.check_company(company)
    assert all(request.headers["authorization"] == "Bearer usuario" for request in recorder.requests)
    assert recorder.requests[0].url.params["branch_id"] == str(branch)
    assert recorder.requests[1].url.params["company_id"] == str(company)


def test_access_403_and_unexpected() -> None:
    access = HTTPAccessDirectory(base_url=BASE, authorization="Bearer u", timeout_seconds=1, transport=httpx.MockTransport(json_response(403)))
    with pytest.raises(OperationalAccessDeniedError):
        access.check_company(uuid4())
    access = HTTPAccessDirectory(base_url=BASE, authorization="Bearer u", timeout_seconds=1, transport=httpx.MockTransport(json_response(200, {"x": 1})))
    with pytest.raises(DependencyUnavailableError):
        access.check_company(uuid4())
