"""Propagación de extremo a extremo del W3C trace-id (D14, R-03, C1).

Con los adaptadores HTTP **reales** sobre `httpx.MockTransport`, el mismo
trace-id aparece en el `traceparent` entrante, `X-Trace-Id`, el Problem
Details `503`, los logs y el `traceparent` saliente. Se compara solo el
trace-id: el `span-id` saliente es nuevo.
"""

import logging
import re

import httpx
import pytest
from fastapi.testclient import TestClient

from operational_context_service.infrastructure.geography_directory import HTTPGeographyDirectory
from operational_context_service.infrastructure.party_identity_organization_directory import (
    HTTPPartyIdentityOrganizationDirectory,
)
from operational_context_service.main import create_app
from operational_context_service.observability import SERVICE_LOGGER
from tests.conftest import ApiClient, company_payload, random_uuid

INCOMING_TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
INCOMING_SPAN_ID = "00f067aa0ba902b7"
TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-01$")


@pytest.fixture
def outgoing():
    return []


@pytest.fixture
def real_adapter_client(test_settings, clean_database, test_auth, make_token, outgoing):
    def handler(request):
        outgoing.append(request)
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    app = create_app(
        test_settings,
        auth=test_auth,
        organization_directory_factory=lambda request: HTTPPartyIdentityOrganizationDirectory(
            base_url=test_settings.party_identity_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=1.0,
            transport=transport,
        ),
        geography_directory_factory=lambda request: HTTPGeographyDirectory(
            base_url=test_settings.geography_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=1.0,
            transport=transport,
        ),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield ApiClient(client, make_token("perm:operational-context:all:all"))


def _assert_same_trace(response, outgoing, caplog, expected_trace_id):
    # (2) X-Trace-Id
    assert response.headers["x-trace-id"] == expected_trace_id
    # (3) Problem Details 503
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert body["trace_id"] == expected_trace_id
    # (4) logs con la causa interna
    cause_records = [
        record for record in caplog.records
        if record.name == SERVICE_LOGGER and "PARTY_IDENTITY_UNAVAILABLE" in record.getMessage()
    ]
    assert cause_records
    assert {record.trace_id for record in cause_records} == {expected_trace_id}
    # (5) traceparent saliente: mismo trace-id, span nuevo
    assert outgoing, "No se llamó al proveedor"
    match = TRACEPARENT.match(outgoing[0].headers["traceparent"])
    assert match and match.group(1) == expected_trace_id
    return match.group(2)


def test_incoming_trace_id_is_propagated_everywhere(real_adapter_client, outgoing, caplog):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)
    incoming = f"00-{INCOMING_TRACE_ID}-{INCOMING_SPAN_ID}-01"

    response = real_adapter_client.post(
        "/api/v1/companies",
        json=company_payload(random_uuid()),
        headers={"traceparent": incoming},  # (1) traceparent entrante
    )

    outgoing_span = _assert_same_trace(response, outgoing, caplog, INCOMING_TRACE_ID)
    assert outgoing_span != INCOMING_SPAN_ID
    assert outgoing[0].headers["authorization"].startswith("Bearer ")


def test_generated_trace_id_is_coherent_everywhere(real_adapter_client, outgoing, caplog):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    response = real_adapter_client.post("/api/v1/companies", json=company_payload(random_uuid()))

    generated = response.headers["x-trace-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    _assert_same_trace(response, outgoing, caplog, generated)
