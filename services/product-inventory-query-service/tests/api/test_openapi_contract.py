"""OpenAPI frente a `contracts/product-inventory-query-api.md` (T126; Principio XI).

Rutas, métodos, parámetros por endpoint, permisos en la descripción, respuestas de error y campos de cada
esquema. Sin `total_records`, `total_pages` ni `page`.
"""

from __future__ import annotations

import pytest

LISTING = {"branch_id", "scope", "search", "internal_code", "sku", "barcode", "identifier", "brand_id", "category_id",
           "include_descendants", "status", "product_type", "has_image", "sort", "page_size", "cursor"}
PARAMETERS = {
    "product-overviews": LISTING | {"stock_state", "price_list_id"},
    "inventory-overviews": LISTING | {"stock_state", "minimum_state"},
    "low-stock-products": LISTING,
    "inventory-summary": {"branch_id", "scope"},
}
PERMISSIONS = {
    "product-overviews": "perm:product-inventory-query:product_overviews:read",
    "inventory-overviews": "perm:product-inventory-query:inventory_overviews:read",
    "low-stock-products": "perm:product-inventory-query:low_stock_products:read",
    "inventory-summary": "perm:product-inventory-query:inventory_summary:read",
}
PAGE_FIELDS = {"items", "page_size", "has_next", "next_cursor", "pagination_reset", "pagination_reset_reason",
               "partial", "partial_reason", "sort_applied", "resolved_at"}
IDENTITY = {"company_product_id", "global_product_id", "display_name", "canonical_name", "internal_code",
            "reference_code", "status", "global_status", "product_type", "brand", "categories", "identifiers",
            "base_unit", "has_image", "asset_id", "image_url", "presentations"}
SCHEMAS = {
    "ProductOverview": IDENTITY | {"stock"},
    "InventoryOverview": IDENTITY | {"stock"},
    "ProductPresentationOut": {"company_product_presentation_id", "global_product_presentation_id", "code", "name",
                               "sku", "internal_code", "status", "is_sellable", "base_quantity_factor", "price"},
    "PresentationOut": {"company_product_presentation_id", "global_product_presentation_id", "code", "name", "sku",
                        "internal_code", "status", "is_sellable", "base_quantity_factor"},
    "PriceOut": {"price_list_id", "price_list_item_id", "unit_price", "currency_code", "resolution"},
    "StockOut": {"base_unit", "total_base_quantity", "branches", "equivalences"},
    "BranchStockOut": {"branch_id", "base_quantity", "balance_state", "minimum_stock", "minimum_state"},
    "EquivalenceOut": {"company_product_presentation_id", "whole_units", "remainder_base_quantity"},
    "LowStockPair": {"company_product_id", "display_name", "internal_code", "base_unit", "branch_id", "base_quantity",
                     "minimum_stock", "shortfall", "policy_status", "has_image", "asset_id", "image_url"},
    "InventorySummaryOut": {"company_id", "resolved_at", "adopted_products", "branches", "consolidated"},
    "SummaryCountsOut": {"products_with_positive_balance", "products_with_zero_balance", "products_with_policy",
                         "products_below_minimum"},
}


@pytest.fixture
def openapi(test_client) -> dict:
    return test_client.get("/openapi.json").json()


COMPANY_PATH = "/api/v1/companies/{{company_id}}/{}"
BRANCH_PATH = "/api/v1/companies/{{company_id}}/branches/{{branch_id}}/{}"


def test_routes_and_methods(openapi) -> None:
    paths = {path for path in openapi["paths"] if path.startswith("/api/v1")}
    assert paths == {template.format(name) for name in PARAMETERS for template in (COMPANY_PATH, BRANCH_PATH)}
    for path in paths:
        assert set(openapi["paths"][path]) == {"get"}  # solo lectura (FR-022-01)


@pytest.mark.parametrize("endpoint", list(PARAMETERS))
def test_parameters_permissions_and_errors(openapi, endpoint) -> None:
    operation = openapi["paths"][f"/api/v1/companies/{{company_id}}/{endpoint}"]["get"]
    query = {p["name"] for p in operation["parameters"] if p["in"] == "query"}
    assert query == PARAMETERS[endpoint]
    assert PERMISSIONS[endpoint] in operation["description"]
    assert {"200", "401", "403", "404", "422", "503"} <= set(operation["responses"])
    assert operation["security"] == [{"BearerAuth": []}]
    if endpoint != "inventory-summary":
        page_size = next(p for p in operation["parameters"] if p["name"] == "page_size")["schema"]
        assert (page_size["minimum"], page_size["maximum"]) == (1, 20)


@pytest.mark.parametrize("endpoint", list(PARAMETERS))
def test_branch_routes_mirror_the_company_routes(openapi, endpoint) -> None:
    """Variante por sucursal: misma respuesta, permiso y errores; `branch_id` en la ruta y sin `scope`."""
    company = openapi["paths"][COMPANY_PATH.format(endpoint)]["get"]
    branch = openapi["paths"][BRANCH_PATH.format(endpoint)]["get"]
    query = {p["name"] for p in branch["parameters"] if p["in"] == "query"}
    assert query == PARAMETERS[endpoint] - {"branch_id", "scope"}
    path = {p["name"]: p for p in branch["parameters"] if p["in"] == "path"}
    assert set(path) == {"company_id", "branch_id"} and all(p["required"] for p in path.values())
    assert path["branch_id"]["schema"]["format"] == "uuid"
    assert PERMISSIONS[endpoint] in branch["description"]
    assert set(branch["responses"]) == set(company["responses"])
    assert branch["responses"]["200"] == company["responses"]["200"]
    assert branch["security"] == company["security"]
    assert branch["operationId"] != company["operationId"]


def test_listings_document_the_default_sorts(openapi) -> None:
    for endpoint in ("product-overviews", "inventory-overviews"):
        description = openapi["paths"][f"/api/v1/companies/{{company_id}}/{endpoint}"]["get"]["description"]
        for sort in ("display_name:asc", "canonical_name:asc", "company_product_id:asc"):
            assert sort in description
    low_stock = openapi["paths"]["/api/v1/companies/{company_id}/low-stock-products"]["get"]["description"]
    assert "shortfall:desc" in low_stock


@pytest.mark.parametrize("item", ["ProductOverview", "InventoryOverview", "LowStockPair"])
def test_cursor_page_envelope_without_totals(openapi, item) -> None:
    properties = set(openapi["components"]["schemas"][f"CursorPage_{item}_"]["properties"])
    assert properties == PAGE_FIELDS
    assert not {"total_records", "total_pages", "page"} & properties


@pytest.mark.parametrize("name", list(SCHEMAS))
def test_schema_fields(openapi, name) -> None:
    assert set(openapi["components"]["schemas"][name]["properties"]) == SCHEMAS[name]


def test_branch_summary_fields(openapi) -> None:
    fields = set(openapi["components"]["schemas"]["BranchSummaryOut"]["properties"])
    assert fields == {"branch_id"} | SCHEMAS["SummaryCountsOut"]
    summary = set(openapi["components"]["schemas"]["InventorySummaryOut"]["properties"])
    assert not {"quantities_by_base_unit", "products_out_of_stock"} & summary
