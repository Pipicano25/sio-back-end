"""El OpenAPI publicado coincide con `contracts/rest-api.md` y `contracts/errors.md` (RC-09; T073)."""

from __future__ import annotations

import logging

import pytest
from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.api.routes import ROUTES

EXPECTED_OPERATIONS = {
    ("/api/v1/audit-events", "post"),
    ("/api/v1/audit-events/batch", "post"),
    ("/api/v1/companies/{company_id}/audit-events", "get"),
    ("/api/v1/companies/{company_id}/audit-events/{audit_id}", "get"),
    ("/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}", "get"),
    ("/api/v1/platform-audit-events", "get"),
    ("/api/v1/platform-audit-events/{audit_id}", "get"),
    ("/api/v1/platform-entity-history/{entity_type}/{entity_id}", "get"),
    ("/health/live", "get"),
    ("/health/ready", "get"),
}

COMPANY_FILTERS = {
    "page", "page_size", "occurred_at_from", "occurred_at_to", "result", "action", "entity_type",
    "entity_id", "source_service", "keycloak_user_id", "application_user_id", "branch_id", "event_id",
    "correlation_id", "request_id",
}


@pytest.fixture
def schema(as_token):
    response = as_token(None).get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_operations_match_contract(schema) -> None:
    published = {(path, method) for path, item in schema["paths"].items() for method in item}
    assert published == EXPECTED_OPERATIONS


def test_security_and_transversal_responses(schema) -> None:
    for path, item in schema["paths"].items():
        for operation in item.values():
            if path.startswith("/health"):
                assert operation["security"] == []
            else:
                assert operation["security"] == [{"BearerAuth": []}]
                assert {"401", "403", "503"} <= set(operation["responses"])


def test_registration_responses(schema) -> None:
    single = schema["paths"]["/api/v1/audit-events"]["post"]["responses"]
    batch = schema["paths"]["/api/v1/audit-events/batch"]["post"]["responses"]
    assert {"200", "201", "409", "422"} <= set(single)
    assert {"200", "409", "422"} <= set(batch)


# Estados que cada operación debe publicar según `contracts/rest-api.md` y `contracts/errors.md`.
EXPECTED_STATUSES = {
    ("/api/v1/audit-events", "post"): {"200", "201", "400", "401", "403", "409", "422", "503"},
    ("/api/v1/audit-events/batch", "post"): {"200", "400", "401", "403", "409", "422", "503"},
    ("/api/v1/companies/{company_id}/audit-events", "get"): {"200", "401", "403", "404", "422", "503"},
    ("/api/v1/companies/{company_id}/audit-events/{audit_id}", "get"): {
        "200", "401", "403", "404", "422", "503",
    },
    ("/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}", "get"): {
        "200", "401", "403", "404", "422", "503",
    },
    ("/api/v1/platform-audit-events", "get"): {"200", "401", "403", "422", "503"},
    ("/api/v1/platform-audit-events/{audit_id}", "get"): {"200", "401", "403", "404", "422", "503"},
    ("/api/v1/platform-entity-history/{entity_type}/{entity_id}", "get"): {
        "200", "401", "403", "422", "503",
    },
}


@pytest.mark.parametrize(("path", "method"), sorted(EXPECTED_STATUSES))
def test_each_operation_publishes_its_contract_statuses(schema, path, method) -> None:
    responses = schema["paths"][path][method]["responses"]
    assert EXPECTED_STATUSES[(path, method)] <= set(responses)


def test_company_routes_document_operational_access_denied(schema) -> None:
    for path, item in schema["paths"].items():
        if path.startswith("/api/v1/companies/"):
            assert "AUDIT.OPERATIONAL_ACCESS_DENIED" in item["get"]["responses"]["403"]["description"]


def test_error_codes_match_errors_contract() -> None:
    """Cada `code` de `contracts/errors.md` lo produce el módulo de errores con su estado."""
    from audit_service.api import errors

    produced = {f"{errors.CODE_PREFIX}{code}": status for code, status in errors._STATUS_BY_CODE.items()}
    produced |= {f"{errors.CODE_PREFIX}{code}": status for status, (code, _) in errors._HTTP_CODES.items()}
    contract = {
        "AUDIT.UNAUTHENTICATED": 401,
        "AUDIT.FORBIDDEN": 403,
        "AUDIT.OPERATIONAL_ACCESS_DENIED": 403,
        "AUDIT.NOT_FOUND": 404,
        "AUDIT.MALFORMED_BODY": 400,
        "AUDIT.VALIDATION_ERROR": 422,
        "AUDIT.EVENT_ID_CONFLICT": 409,
        "AUDIT.DEPENDENCY_UNAVAILABLE": 503,
    }
    for code, status in contract.items():
        assert produced.get(code) == status, code


def test_query_parameters(schema) -> None:
    company = schema["paths"]["/api/v1/companies/{company_id}/audit-events"]["get"]["parameters"]
    platform = schema["paths"]["/api/v1/platform-audit-events"]["get"]["parameters"]
    history = schema["paths"]["/api/v1/companies/{company_id}/entity-history/{entity_type}/{entity_id}"]["get"]["parameters"]

    assert {p["name"] for p in company if p["in"] == "query"} == COMPANY_FILTERS
    assert {p["name"] for p in platform if p["in"] == "query"} == COMPANY_FILTERS - {"branch_id"}
    assert {p["name"] for p in history if p["in"] == "query"} == {
        "page", "page_size", "occurred_at_from", "occurred_at_to", "result",
    }


def test_event_schema_forbids_extra_fields(schema) -> None:
    event = schema["components"]["schemas"]["AuditEventIn"]
    assert event["additionalProperties"] is False
    assert set(event["required"]) == {"event_id", "action", "entity_type", "result", "occurred_at"}
    response = schema["components"]["schemas"]["AuditEventResponse"]["properties"]
    assert {"recorded_at", "source_service", "created_by", "redacted_paths"} <= set(response)
    assert "content_hash" not in response


class _Denied(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.values: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        value = getattr(record, DENIED_PERMISSION_ATTRIBUTE, None)
        if value:
            self.values.append(value)


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_each_route_requires_the_documented_permission(as_token, make_token, service_token, method, path, permission):
    token = service_token() if path.endswith(("audit-events", "batch")) and method == "POST" else make_token(sub="nadie")
    handler = _Denied()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = as_token(token).request(method, path, json={})
    finally:
        log.removeHandler(handler)

    assert response.status_code == 403
    assert handler.values == [permission]
