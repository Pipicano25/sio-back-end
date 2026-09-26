"""Adaptador HTTP de personas de Party Identity (R-08, FR-017, FR-064, RC-05).

Contrato: `specs/005-operational-context-users/contracts/party-identity-dependency.md`.
"""

from uuid import uuid4

import httpx
import pytest

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.infrastructure.party_identity_person_directory import (
    HTTPPartyIdentityPersonDirectory,
)
from operational_context_service.observability import configure_logging, reset_trace_id, set_trace_id

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
TOKEN = "Bearer token-secreto-del-usuario"


@pytest.fixture(autouse=True)
def trace_context():
    configure_logging()
    token = set_trace_id(TRACE_ID)
    yield
    reset_trace_id(token)


def _adapter(handler):
    return HTTPPartyIdentityPersonDirectory(
        base_url="http://party-identity.test/api/v1/",
        authorization=TOKEN,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE"])
def test_200_returns_person_with_status(status):
    person_id = uuid4()
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(
            200,
            json={"id": str(person_id), "status": status, "first_name": "Ficticio"},
        )

    result = _adapter(handler).get_person(person_id)

    assert result.id == person_id and result.status == status
    request = seen["request"]
    assert str(request.url) == f"http://party-identity.test/api/v1/person-identities/{person_id}"
    assert request.headers["authorization"] == TOKEN
    assert request.headers["traceparent"].split("-")[1] == TRACE_ID


def test_404_returns_none():
    assert _adapter(lambda request: httpx.Response(404)).get_person(uuid4()) is None


@pytest.mark.parametrize("status", [401, 403, 500, 502, 409])
def test_error_statuses_are_dependency_unavailable(status):
    with pytest.raises(DependencyUnavailableError) as error:
        _adapter(lambda request: httpx.Response(status)).get_person(uuid4())

    assert error.value.provider == "party-identity"


def test_network_error_and_timeout_are_dependency_unavailable():
    def network(request):
        raise httpx.ConnectError("sin red")

    def timeout(request):
        raise httpx.ReadTimeout("tiempo agotado")

    for handler in (network, timeout):
        with pytest.raises(DependencyUnavailableError):
            _adapter(handler).get_person(uuid4())


def test_unexpected_body_is_dependency_unavailable():
    with pytest.raises(DependencyUnavailableError):
        _adapter(lambda request: httpx.Response(200, json={"id": "x"})).get_person(uuid4())
