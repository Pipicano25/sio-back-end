"""OpenAPI frente a `contracts/business-reporting-api.md` (Principio XI)."""

from __future__ import annotations

import pytest

C = "/api/v1/companies/{company_id}/reports/"
B = "/api/v1/companies/{company_id}/branches/{branch_id}/reports/"
PERMISSIONS = {
    C + "top-selling-products": "perm:business-reporting:top_selling_products:read",
    C + "sales-by-branch": "perm:business-reporting:sales_by_branch:read",
    C + "purchases": "perm:business-reporting:purchases:read",
    C + "stock-evolution": "perm:business-reporting:stock_evolution:read",
    B + "top-selling-products": "perm:business-reporting:top_selling_products:read",
    B + "sales-by-branch": "perm:business-reporting:sales_by_branch:read",
    B + "purchases": "perm:business-reporting:purchases:read",
    B + "stock-evolution": "perm:business-reporting:stock_evolution:read",
}

OWNER = {
    "top-selling-products": "perm:sales:sales:read",
    "sales-by-branch": "perm:sales:sales:read",
    "purchases": "perm:purchase:purchases:read",
    "stock-evolution": "perm:inventory:stock_evolution:read",
}


@pytest.fixture
def openapi(test_client) -> dict:
    return test_client.get("/openapi.json").json()


def test_exactly_eight_reporting_routes_and_only_get(openapi) -> None:
    paths = {p for p in openapi["paths"] if p.startswith("/api/v1")}
    assert paths == set(PERMISSIONS) and len(paths) == 8
    assert all(set(openapi["paths"][p]) == {"get"} for p in paths)
    assert not any("margin" in p for p in openapi["paths"])  # margen: fase 2


@pytest.mark.parametrize("path", list(PERMISSIONS))
def test_permissions_errors_and_parameters(openapi, path) -> None:
    operation = openapi["paths"][path]["get"]
    assert PERMISSIONS[path] in operation["description"]
    assert OWNER[path.rsplit("/", 1)[1]] in operation["description"]
    assert {"200", "401", "403", "404", "422", "503"} <= set(operation["responses"])
    assert operation["security"] == [{"BearerAuth": []}]
    names = {p["name"] for p in operation["parameters"] if p["in"] == "query"}
    assert {"date_from", "date_to", "format", "bom"} <= names
    if path.startswith(B):
        assert "branch_id" not in names  # la sucursal va en la ruta
        assert {p["name"] for p in operation["parameters"] if p["in"] == "path"} == {"company_id", "branch_id"}
    else:
        assert "branch_id" in names
