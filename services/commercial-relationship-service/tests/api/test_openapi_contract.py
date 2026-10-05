"""OpenAPI = `contracts/rest-api.md` (puerta de calidad 5, RC-10, FR-052)."""

from __future__ import annotations

import re
from pathlib import Path

from tests.api.routes import ROUTES

SPECS = Path(__file__).resolve().parents[4] / "specs"
CONTRACTS = (
    SPECS / "007-commercial-relationship-core" / "contracts" / "rest-api.md",
    SPECS / "010-commercial-relationship-commercial-product" / "contracts" / "rest-api.md",
)
CONTRACT_ROUTE = re.compile(r"^\| `(GET|POST|PUT|DELETE|PATCH) (/api/v1/[^`]+)`", re.MULTILINE)


def _contract_operations() -> set[tuple[str, str]]:
    operations = set()
    for contract in CONTRACTS:
        for method, path in CONTRACT_ROUTE.findall(contract.read_text(encoding="utf-8")):
            operations.add((method, path))
    return operations


def _openapi_operations(schema) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in schema["paths"].items()
        if path.startswith("/api/v1")
        for method in item
        if method in {"get", "post", "put", "delete", "patch"}
    }


def test_openapi_matches_contract_exactly(as_token):
    schema = as_token(None).get("/openapi.json").json()
    assert _openapi_operations(schema) == _contract_operations()
    assert len(_contract_operations()) == len(ROUTES) == 55


def test_no_delete_routes(as_token):
    schema = as_token(None).get("/openapi.json").json()
    assert not any(method == "DELETE" for method, _ in _openapi_operations(schema))


def test_user_routes_document_403_with_operational_access_denied(as_token):
    """Regla transversal "Acceso operativo denegado" (FR-052): `403` documentado en toda ruta de usuario."""
    schema = as_token(None).get("/openapi.json").json()
    missing = []
    for path, item in schema["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in item.items():
            response = operation.get("responses", {}).get("403")
            if response is None or "OPERATIONAL_ACCESS_DENIED" not in response.get("description", ""):
                missing.append(f"{method.upper()} {path}")
    assert not missing, missing


def test_routes_require_bearer(as_token):
    schema = as_token(None).get("/openapi.json").json()
    for path, item in schema["paths"].items():
        if path.startswith("/api/v1"):
            for operation in item.values():
                assert operation["security"] == [{"BearerAuth": []}], path


def test_phase_b_amounts_are_documented_as_strings(as_token):
    """R-11: los importes de la Fase B se exponen como cadena decimal, nunca como número JSON."""
    schemas = as_token(None).get("/openapi.json").json()["components"]["schemas"]
    amounts = {
        "PriceListItemResponse": ("unit_price",),
        "SupplierPaymentConditionResponse": ("credit_limit", "interest_rate_percentage", "cash_discount_percentage"),
        "SupplierProductResponse": ("minimum_order_quantity", "pack_quantity", "negotiated_unit_cost"),
        "ApplicablePriceItem": ("unit_price",),
    }

    for schema_name, fields in amounts.items():
        schema = schemas.get(schema_name) or schemas[f"{schema_name}-Output"]
        for field in fields:
            definition = schema["properties"][field]
            types = {option.get("type") for option in definition.get("anyOf", [definition])}
            assert "number" not in types and "string" in types, (schema_name, field, definition)
