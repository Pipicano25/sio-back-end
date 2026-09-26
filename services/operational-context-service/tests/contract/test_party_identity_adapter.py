"""Adaptador HTTP de Party Identity (FR-042, FR-043, R-03, R-06).

Contrato: `specs/004-operational-context-core/contracts/party-identity-dependency.md`.
"""

import logging
from uuid import uuid4

import httpx
import pytest

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.infrastructure.party_identity_organization_directory import (
    HTTPPartyIdentityOrganizationDirectory,
)
from operational_context_service.observability import (
    SERVICE_LOGGER,
    configure_logging,
    reset_trace_id,
    set_trace_id,
)

TRACE_ID = "0af7651916cd43dd8448eb211c80319c"
TOKEN = "Bearer token-secreto-del-usuario"


@pytest.fixture(autouse=True)
def trace_context():
    configure_logging()
    token = set_trace_id(TRACE_ID)
    yield
    reset_trace_id(token)


def _adapter(handler, timeout=1.0):
    return HTTPPartyIdentityOrganizationDirectory(
        base_url="http://party-identity.test/api/v1/",
        authorization=TOKEN,
        timeout_seconds=timeout,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE"])
def test_200_returns_reference_with_status(status):
    organization_id = uuid4()
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"id": str(organization_id), "status": status, "legal_name": "X"})

    result = _adapter(handler).get_organization(organization_id)

    assert result.id == organization_id and result.status == status
    request = seen["request"]
    assert str(request.url) == f"http://party-identity.test/api/v1/organization-identities/{organization_id}"
    assert request.headers["authorization"] == TOKEN
    traceparent = request.headers["traceparent"].split("-")
    assert traceparent[1] == TRACE_ID and len(traceparent[2]) == 16


def test_404_returns_none():
    assert _adapter(lambda request: httpx.Response(404)).get_organization(uuid4()) is None


def _assert_log(caplog, cause, level):
    records = [r for r in caplog.records if r.name == SERVICE_LOGGER and cause in r.getMessage()]
    assert records, f"No se registró la causa {cause}"
    record = records[-1]
    assert record.levelno == level
    assert record.trace_id == TRACE_ID
    assert "token-secreto" not in record.getMessage()


@pytest.mark.parametrize("status", [401, 403])
def test_denied_is_unavailable_with_internal_cause(caplog, status):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    with pytest.raises(DependencyUnavailableError) as error:
        _adapter(lambda request: httpx.Response(status)).get_organization(uuid4())

    assert error.value.cause == "ORGANIZATION_VALIDATION_DENIED"
    assert error.value.provider == "party-identity"
    assert "ORGANIZATION_VALIDATION_DENIED" not in error.value.message
    _assert_log(caplog, "ORGANIZATION_VALIDATION_DENIED", logging.WARNING)


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500),
        lambda request: httpx.Response(400),
        lambda request: httpx.Response(200, json={"id": "x"}),
        lambda request: httpx.Response(200, json={"id": "x", "status": "DELETED"}),
        lambda request: httpx.Response(200, content=b"no-json"),
    ],
    ids=["500", "400", "sin-status", "status-invalido", "no-json"],
)
def test_unexpected_responses_are_unavailable(caplog, handler):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    with pytest.raises(DependencyUnavailableError) as error:
        _adapter(handler).get_organization(uuid4())

    assert error.value.cause == "PARTY_IDENTITY_UNAVAILABLE"
    _assert_log(caplog, "PARTY_IDENTITY_UNAVAILABLE", logging.ERROR)


@pytest.mark.parametrize("exception", [httpx.ReadTimeout, httpx.ConnectError])
def test_timeout_and_network_errors_are_unavailable(caplog, exception):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    def handler(request):
        raise exception("fallo", request=request)

    with pytest.raises(DependencyUnavailableError) as error:
        _adapter(handler).get_organization(uuid4())

    assert error.value.cause == "PARTY_IDENTITY_UNAVAILABLE"
    _assert_log(caplog, "PARTY_IDENTITY_UNAVAILABLE", logging.ERROR)


def test_uses_configured_timeout(monkeypatch):
    captured = {}
    original = httpx.Client.__init__

    def spy(self, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        original(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", spy)
    _adapter(lambda request: httpx.Response(404), timeout=2.5).get_organization(uuid4())

    assert captured["timeout"] == 2.5
