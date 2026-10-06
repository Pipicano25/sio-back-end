"""Adaptador de Commercial Relationship con `httpx.MockTransport` (contracts/dependencies.md; T014)."""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from inventory_service.application.exceptions import DependencyUnavailableError
from inventory_service.infrastructure.commercial_relationship_directory import HTTPCompanyProductDirectory

BASE = "http://cr.test/api/v1"


class Tokens:
    def __init__(self) -> None:
        self.invalidated = 0

    def get_token(self) -> str:
        return "tecnico"

    def invalidate(self) -> None:
        self.invalidated += 1


def directory(handler) -> HTTPCompanyProductDirectory:
    return HTTPCompanyProductDirectory(
        base_url=BASE, timeout_seconds=1, tokens=Tokens(), transport=httpx.MockTransport(handler)
    )


def test_batch_lookup_single_call_with_distinct_ids() -> None:
    a, b, missing, company = uuid4(), uuid4(), uuid4(), uuid4()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers["authorization"], json.loads(request.content)))
        return httpx.Response(
            200,
            json={"items": [
                {"id": str(a), "found": True, "company_id": str(company), "status": "ACTIVE",
                 "inventory_control_enabled": True, "display_name": "x"},
                {"id": str(b), "found": True, "company_id": str(company), "status": "INACTIVE",
                 "inventory_control_enabled": False},
                {"id": str(missing), "found": False},
            ]},
        )

    found = directory(handler).lookup([a, b, a, missing])
    assert len(seen) == 1
    assert seen[0][0] == f"{BASE}/company-products/batch-lookup"
    assert seen[0][1] == "Bearer tecnico"
    assert seen[0][2] == {"ids": [str(a), str(b), str(missing)]}
    assert set(found) == {a, b}
    assert found[b].status == "INACTIVE" and found[b].inventory_control_enabled is False


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(403),
        httpx.Response(422),
        httpx.Response(200, json={"x": 1}),
        httpx.Response(200, json={"items": [{"id": "x"}]}),
        httpx.Response(200, json={"items": [{"found": True, "id": "no-uuid"}]}),
    ],
)
def test_unavailable_answers(response) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        directory(lambda request: response).lookup([uuid4()])
    assert error.value.provider == "commercial-relationship"


def test_network_error_is_unavailable() -> None:
    def broken(request):
        raise httpx.ConnectTimeout("caido")

    with pytest.raises(DependencyUnavailableError):
        directory(broken).lookup([uuid4()])
