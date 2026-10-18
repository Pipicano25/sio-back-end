"""Adaptador de Operational Context con el token del usuario (T062; FR-022-11, D5)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.infrastructure.operational_context import HTTPOperationalContext
from tests.contract.adapter_support import Recorder, dependency

USER = "Bearer token-del-usuario"


def _oc(responder) -> tuple[HTTPOperationalContext, Recorder]:
    recorder = Recorder(responder)
    return HTTPOperationalContext(dependency("operational-context", recorder), USER), recorder


def _access(body, status=200):
    return lambda request: httpx.Response(status, json=body)


def test_access_allowed_denied_and_uses_the_user_token() -> None:
    company = uuid4()
    oc, recorder = _oc(_access({"allowed": True, "reason": None, "company_id": str(company)}))
    assert asyncio.run(oc.has_company_access(company)) is True
    request = recorder.requests[0]
    assert request.url.path == "/api/v1/operational-access"
    assert request.url.params["company_id"] == str(company)
    assert request.headers["authorization"] == USER

    for body, status in (({"allowed": False, "reason": "NOT_MEMBER"}, 200), ({}, 403), ({}, 404)):
        oc, _ = _oc(_access(body, status))
        assert asyncio.run(oc.has_company_access(company)) is False


def test_access_for_another_company_in_the_answer_is_denied() -> None:
    oc, _ = _oc(_access({"allowed": True, "company_id": str(uuid4())}))
    assert asyncio.run(oc.has_company_access(uuid4())) is False


@pytest.mark.parametrize("response", [httpx.Response(500, json={}), httpx.Response(200, json={"allowed": "si"}),
                                      httpx.Response(200, content=b"x")])
def test_access_errors_are_503(response) -> None:
    oc, _ = _oc(lambda request: response)
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(oc.has_company_access(uuid4()))


def test_branches_follow_pages_and_discard_other_companies() -> None:
    company = uuid4()
    first, second, foreign = uuid4(), uuid4(), uuid4()

    def responder(request):
        page = int(request.url.params["page"])
        assert request.url.params["status"] == "ACTIVE" and request.url.params["page_size"] == "100"
        rows = [{"id": str(first), "company_id": str(company), "status": "ACTIVE"},
                {"id": str(foreign), "company_id": str(uuid4()), "status": "ACTIVE"}] if page == 1 else \
               [{"id": str(second), "company_id": str(company), "status": "ACTIVE"}]
        return httpx.Response(200, json={"items": rows, "page": page, "page_size": 100, "total_records": 3, "total_pages": 2})

    oc, recorder = _oc(responder)
    branches = asyncio.run(oc.branches(company, status="ACTIVE"))
    assert [b.id for b in branches] == [first, second]
    assert all(r.headers["authorization"] == USER for r in recorder.requests)


def test_branches_of_a_non_member_are_empty_and_other_errors_503() -> None:
    oc, _ = _oc(lambda request: httpx.Response(403, json={}))
    assert asyncio.run(oc.branches(uuid4(), status="ACTIVE")) == []
    oc, _ = _oc(lambda request: httpx.Response(502, json={}))
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(oc.branches(uuid4(), status="ACTIVE"))

