"""OpenAPI de las ampliaciones de la spec 022 (PC-1, PC-2, PC-3; T031, Principio XI, CP-87)."""

from __future__ import annotations

from product_catalog_service.main import create_app


def _schema() -> dict:
    return create_app().openapi()


def _component(schema: dict, name: str) -> dict:
    return schema["components"]["schemas"][name]


def test_new_routes_exist_without_totals() -> None:
    schema = _schema()
    assert "post" in schema["paths"]["/api/v1/products/summaries/batch-lookup"]
    match = schema["paths"]["/api/v1/products/match"]["post"]
    content = match["responses"]["200"]["content"]["application/json"]["schema"]
    text = str(content) + str(schema["components"]["schemas"].get("ProductMatchConductorResponse", {}))
    assert "total" not in text


def test_existing_batch_lookups_keep_their_fields() -> None:
    schema = _schema()
    product = _component(schema, "ProductLookupItem")
    assert set(product["properties"]) == {"id", "found", "status", "is_complete", "eligible_for_adoption", "first_used_at"}
    unit = _component(schema, "UnitLookupItem")
    assert {"id", "found", "status", "measurement_type", "allows_decimals"} <= set(unit["properties"])
    assert {"code", "name"} <= set(unit["properties"])
