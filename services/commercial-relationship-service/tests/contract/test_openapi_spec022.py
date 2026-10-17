"""OpenAPI de las ampliaciones de la spec 022 (CR-1, CR-2; T017, Principio XI, CP-86).

Las rutas nuevas existen con sus esquemas y las respuestas existentes no cambian de forma.
"""

from __future__ import annotations


def _schema(as_token) -> dict:
    return as_token(None).get("/openapi.json").json()


def _resolve(schema: dict, ref: dict) -> dict:
    name = ref["$ref"].rsplit("/", 1)[-1]
    return schema["components"]["schemas"][name]


def _response_schema(schema: dict, path: str, method: str) -> dict:
    content = schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
    return _resolve(schema, content) if "$ref" in content else content


def test_search_route_has_no_totals(as_token) -> None:
    schema = _schema(as_token)
    path = "/api/v1/companies/{company_id}/company-products/search"
    assert "post" in schema["paths"][path]
    response = _response_schema(schema, path, "post")
    assert set(response["properties"]) == {"items", "has_more"}
    request_ref = schema["paths"][path]["post"]["requestBody"]["content"]["application/json"]["schema"]
    request = _resolve(schema, request_ref)
    assert {"search", "internal_code", "sku", "sort", "after", "limit", "company_product_ids", "global_product_ids"} <= set(
        request["properties"]
    )
    assert "limit" in request["required"]


def test_by_products_route_exists(as_token) -> None:
    schema = _schema(as_token)
    path = "/api/v1/companies/{company_id}/company-product-presentations/by-products"
    item = _resolve(schema, _response_schema(schema, path, "post")["properties"]["items"]["items"])
    assert {"internal_code", "sku", "reference_code", "company_product_id"} <= set(item["properties"])


def test_existing_listing_keeps_total_records(as_token) -> None:
    schema = _schema(as_token)
    listing = _response_schema(schema, "/api/v1/companies/{company_id}/company-products", "get")
    assert {"items", "page", "page_size", "total_records", "total_pages"} <= set(listing["properties"])


def test_existing_batch_lookup_only_gains_fields(as_token) -> None:
    schema = _schema(as_token)
    item = _resolve(schema, {"$ref": "#/components/schemas/PresentationBatchLookupItem"})
    previous = {
        "id", "found", "company_id", "company_product_id", "global_product_presentation_id", "is_purchasable",
        "is_sellable", "is_default_purchase", "is_default_sale", "status", "version",
    }
    assert previous <= set(item["properties"])
    assert set(item["required"]) == {"id", "found"}
