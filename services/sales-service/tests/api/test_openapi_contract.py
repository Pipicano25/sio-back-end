"""Contrato OpenAPI frente a `contracts/rest-api.md` y `contracts/errors.md` (Principio XI; T090)."""

from __future__ import annotations

import re
from pathlib import Path

from sales_service.api.errors import _STATUS_BY_CODE
from tests.api.routes import ROUTES

SPEC = Path(__file__).resolve().parents[4] / "specs" / "015-sales-core" / "contracts"
DOCUMENTED_EXTRA: set[str] = set()


def test_routes_and_methods_match_the_contract(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    declared = {
        (method.upper(), path)
        for path, item in schema["paths"].items()
        for method in item
        if method in {"get", "post", "put", "delete", "patch"}
    }
    expected = {(method, path.split("?")[0].format(
        company="{company_id}", sale="{sale_id}", detail="{detail_id}", operation="{operation_id}", sequence="{sequence_id}"
    )) for method, path, _ in ROUTES}
    assert expected <= declared
    business = {(method, path) for method, path in declared if path.startswith("/api/v1")}
    assert business == expected


def test_every_route_documents_auth_and_problem_responses(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    for path, item in schema["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in item.items():
            responses = operation["responses"]
            assert {"401", "403", "503"} <= set(responses), (method, path)
            assert operation["security"] == [{"BearerAuth": []}]


def test_error_codes_match_the_catalog() -> None:
    catalog = (SPEC / "errors.md").read_text(encoding="utf-8")
    documented = dict(re.findall(r"^\| `([A-Z_]+)` \| (\d{3}) \|", catalog, re.M))
    assert documented, "catálogo vacío"
    for code, status in documented.items():
        assert _STATUS_BY_CODE.get(code) == int(status), code
    assert set(_STATUS_BY_CODE) - set(documented) == DOCUMENTED_EXTRA


def test_contract_route_table_lists_the_same_routes() -> None:
    table = (SPEC / "rest-api.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| \d+ \| `(GET|POST|PUT|DELETE) ([^`]+)`", table, re.M)
    assert len(rows) == 18  # la fila 18 agrupa deactivate · reactivate
    paths = {(method, path.split("?")[0].split(" ·")[0]) for method, path in rows}
    assert ("POST", "/companies/{c}/sales/{id}/confirmation") in paths
    assert ("GET", "/companies/{c}/sales/{id}/availability") in paths
    assert ("DELETE", "/companies/{c}/sales/{id}/details/{detail_id}") in paths
    assert len(ROUTES) == 21  # 18 filas del contrato + reactivate + 2 agregaciones de la spec 023


def test_profitability_fields_are_optional_and_documented(test_client) -> None:
    """FR-027a: los campos de rentabilidad pueden omitirse; el contrato lo declara."""
    schemas = test_client.get("/openapi.json").json()["components"]["schemas"]
    detail, sale = schemas["SaleDetailResponse"], schemas["SaleResponse"]
    for name in ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage"):
        assert name in detail["properties"] and name not in detail.get("required", []), name
        assert "read-profitability" in detail["properties"][name].get("description", "")
    assert "has_unknown_cost" in sale["properties"] and "has_unknown_cost" not in sale.get("required", [])
    contract = (SPEC / "rest-api.md").read_text(encoding="utf-8")
    assert "perm:sales:sales:read-profitability" in contract


def test_inputs_never_accept_price_date_or_payment_condition(test_client) -> None:
    schemas = test_client.get("/openapi.json").json()["components"]["schemas"]
    line_in = next(value for key, value in schemas.items() if key.startswith("LineIn"))
    assert "unit_price" not in line_in["properties"]
    header = next(value for key, value in schemas.items() if key.startswith("SaleCreateIn"))
    assert not {"operation_date", "customer_payment_condition_id", "due_date"} & set(header["properties"])
