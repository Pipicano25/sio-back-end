"""El OpenAPI publicado coincide con `contracts/rest-api.md` y `contracts/errors.md` (RC-09; T069)."""

from __future__ import annotations

import logging

import pytest
from sio_auth import DENIED_PERMISSION_ATTRIBUTE, LOGGER_NAME

from tests.api.routes import ROUTES

EXPECTED_OPERATIONS = {
    ("/api/v1/inventory-entries", "post"),
    ("/api/v1/inventory-outputs", "post"),
    ("/api/v1/inventory-entries/{operation_id}/reversal", "post"),
    ("/api/v1/inventory-outputs/{operation_id}/reversal", "post"),
    ("/api/v1/companies/{company_id}/branches/{branch_id}/balances", "get"),
    ("/api/v1/companies/{company_id}/branches/{branch_id}/balances/{company_product_id}", "get"),
    ("/api/v1/companies/{company_id}/branches/{branch_id}/balances/lookup", "post"),
    ("/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}", "get"),
    ("/api/v1/companies/{company_id}/inventory-operations/{operation_id}", "get"),
    ("/api/v1/companies/{company_id}/inventory-operations/by-key/{operation_key}", "get"),
    ("/health/live", "get"),
    ("/health/ready", "get"),
}

OPERATION_STATUSES = {"200", "201", "400", "401", "403", "409", "422", "503"}
REVERSAL_STATUSES = OPERATION_STATUSES | {"404"}
QUERY_STATUSES = {"200", "401", "403", "404", "422", "503"}


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


@pytest.mark.parametrize(("path", "method"), sorted(EXPECTED_OPERATIONS))
def test_each_operation_publishes_its_contract_statuses(schema, path, method) -> None:
    if path.startswith("/health"):
        return
    responses = set(schema["paths"][path][method]["responses"])
    if path.endswith("/reversal"):
        expected = REVERSAL_STATUSES
    elif path in ("/api/v1/inventory-entries", "/api/v1/inventory-outputs"):
        expected = OPERATION_STATUSES
    else:
        expected = QUERY_STATUSES
    assert expected <= responses, (path, expected - responses)


def test_query_routes_document_operational_access_denied(schema) -> None:
    for path, item in schema["paths"].items():
        if path.startswith("/api/v1/companies/"):
            for operation in item.values():
                assert "INVENTORY.OPERATIONAL_ACCESS_DENIED" in operation["responses"]["403"]["description"]


def test_query_parameters(schema) -> None:
    paths = schema["paths"]
    stock = paths["/api/v1/companies/{company_id}/branches/{branch_id}/balances"]["get"]["parameters"]
    kardex = paths["/api/v1/companies/{company_id}/branches/{branch_id}/kardex/{company_product_id}"]["get"]["parameters"]
    assert {p["name"] for p in stock if p["in"] == "query"} == {"page", "page_size", "company_product_id", "in_stock_only"}
    assert {p["name"] for p in kardex if p["in"] == "query"} == {
        "page", "page_size", "occurred_at_from", "occurred_at_to", "movement_type", "origin_type", "origin_id",
    }


def test_request_schemas_forbid_extra_fields_and_require_company_in_reversals(schema) -> None:
    components = schema["components"]["schemas"]
    for name in ("OperationIn", "LineIn", "ReversalIn", "BalanceLookupIn"):
        assert components[name]["additionalProperties"] is False, name
    assert set(components["OperationIn"]["required"]) == {
        "operation_key", "company_id", "branch_id", "origin_type", "origin_id", "application_user_id",
        "correlation_id", "lines",
    }
    assert set(components["ReversalIn"]["required"]) == {"operation_key", "company_id", "application_user_id", "correlation_id"}
    response = components["InventoryOperationResponse"]["properties"]
    assert {"movements", "balances", "reversed_by_operation_id", "reverses_operation_id"} <= set(response)
    assert "request_hash" not in response and "requested_by_client" not in response


def test_error_codes_match_errors_contract() -> None:
    from inventory_service.api import errors

    produced = {f"{errors.CODE_PREFIX}{code}": status for code, status in errors._STATUS_BY_CODE.items()}
    produced |= {f"{errors.CODE_PREFIX}{code}": status for status, (code, _) in errors._HTTP_CODES.items()}
    contract = {
        "INVENTORY.UNAUTHENTICATED": 401,
        "INVENTORY.FORBIDDEN": 403,
        "INVENTORY.OPERATIONAL_ACCESS_DENIED": 403,
        "INVENTORY.NOT_FOUND": 404,
        "INVENTORY.MALFORMED_BODY": 400,
        "INVENTORY.VALIDATION_ERROR": 422,
        "INVENTORY.OPERATION_KEY_CONFLICT": 409,
        "INVENTORY.INSUFFICIENT_STOCK": 409,
        "INVENTORY.ALREADY_REVERSED": 409,
        "INVENTORY.REVERSAL_NOT_ALLOWED": 409,
        "INVENTORY.DEPENDENCY_UNAVAILABLE": 503,
    }
    for code, status in contract.items():
        assert produced.get(code) == status, code


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
    token = service_token() if method == "POST" and "/companies/" not in path else make_token(sub="nadie")
    handler = _Denied()
    log = logging.getLogger(LOGGER_NAME)
    log.addHandler(handler)
    try:
        response = as_token(token).request(method, path, json={})
    finally:
        log.removeHandler(handler)

    assert response.status_code == 403
    assert handler.values == [permission]
