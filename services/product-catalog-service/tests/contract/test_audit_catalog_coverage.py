"""Cobertura del catálogo de auditoría frente al OpenAPI (feature 016; FR-003; T055).

`specs/016-existing-services-audit/contracts/audit-actions.md`, sección Product Catalog: 63 escrituras
(62 acciones: las dos rutas de primer uso comparten `REGISTER_PRODUCT_FIRST_USE`, DS-10) y 3 lecturas
por `POST` excluidas.
"""

from __future__ import annotations

from product_catalog_service.application import audit_events as audit

V = "/api/v1"


def _lifecycle(path: str, item: str, suffix: str, entity: str) -> dict:
    return {
        ("POST", f"{V}/{path}"): (f"CREATE_{suffix}", entity),
        ("PUT", f"{V}/{path}/{{{item}}}"): (f"UPDATE_{suffix}", entity),
        ("POST", f"{V}/{path}/{{{item}}}/deactivate"): (f"DEACTIVATE_{suffix}", entity),
        ("POST", f"{V}/{path}/{{{item}}}/reactivate"): (f"REACTIVATE_{suffix}", entity),
    }


P = f"{V}/products/{{product_id}}"
CATALOG = {
    **_lifecycle("units-of-measure", "item_id", "UNIT_OF_MEASURE", "UnitOfMeasure"),
    **_lifecycle("packaging-types", "item_id", "PACKAGING_TYPE", "PackagingType"),
    **_lifecycle("brands", "item_id", "BRAND", "Brand"),
    **_lifecycle("categories", "item_id", "CATEGORY", "Category"),
    **_lifecycle("categories/{category_id}/attributes", "association_id", "CATEGORY_ATTRIBUTE", "CategoryAttribute"),
    **_lifecycle("attribute-definitions", "item_id", "ATTRIBUTE_DEFINITION", "AttributeDefinition"),
    **_lifecycle("attribute-definitions/{definition_id}/options", "option_id", "ATTRIBUTE_OPTION", "AttributeOption"),
    **_lifecycle("group-types", "item_id", "PRODUCT_GROUP_TYPE", "ProductGroupType"),
    ("POST", f"{V}/group-types/{{group_type_id}}/groups"): ("CREATE_PRODUCT_GROUP", "ProductGroup"),
    ("PUT", f"{V}/groups/{{group_id}}"): ("UPDATE_PRODUCT_GROUP", "ProductGroup"),
    ("POST", f"{V}/groups/{{group_id}}/deactivate"): ("DEACTIVATE_PRODUCT_GROUP", "ProductGroup"),
    ("POST", f"{V}/groups/{{group_id}}/reactivate"): ("REACTIVATE_PRODUCT_GROUP", "ProductGroup"),
    ("POST", f"{V}/products"): ("CREATE_PRODUCT", "Product"),
    ("PUT", P): ("UPDATE_PRODUCT", "Product"),
    ("POST", f"{P}/deactivate"): ("DEACTIVATE_PRODUCT", "Product"),
    ("POST", f"{P}/reactivate"): ("REACTIVATE_PRODUCT", "Product"),
    ("POST", f"{P}/categories"): ("ADD_PRODUCT_CATEGORY", "ProductCategory"),
    ("POST", f"{P}/categories/{{association_id}}/set-primary"): ("SET_PRIMARY_PRODUCT_CATEGORY", "ProductCategory"),
    ("POST", f"{P}/categories/{{association_id}}/deactivate"): ("DEACTIVATE_PRODUCT_CATEGORY", "ProductCategory"),
    ("PUT", f"{P}/attribute-values/{{definition_id}}"): ("SET_PRODUCT_ATTRIBUTE_VALUE", "ProductAttributeValue"),
    ("DELETE", f"{P}/attribute-values/{{definition_id}}"): ("DELETE_PRODUCT_ATTRIBUTE_VALUE", "ProductAttributeValue"),
    ("POST", f"{P}/presentations"): ("CREATE_PRODUCT_PRESENTATION", "ProductPresentation"),
    ("PUT", f"{V}/presentations/{{presentation_id}}"): ("UPDATE_PRODUCT_PRESENTATION", "ProductPresentation"),
    ("POST", f"{V}/presentations/{{presentation_id}}/deactivate"): ("DEACTIVATE_PRODUCT_PRESENTATION", "ProductPresentation"),
    ("POST", f"{V}/presentations/{{presentation_id}}/reactivate"): ("REACTIVATE_PRODUCT_PRESENTATION", "ProductPresentation"),
    ("POST", f"{P}/identifiers"): ("CREATE_PRODUCT_IDENTIFIER", "ProductIdentifier"),
    ("POST", f"{P}/identifiers/{{identifier_id}}/set-primary"): ("SET_PRIMARY_PRODUCT_IDENTIFIER", "ProductIdentifier"),
    ("POST", f"{P}/identifiers/{{identifier_id}}/deactivate"): ("DEACTIVATE_PRODUCT_IDENTIFIER", "ProductIdentifier"),
    ("POST", f"{P}/identifiers/{{identifier_id}}/reactivate"): ("REACTIVATE_PRODUCT_IDENTIFIER", "ProductIdentifier"),
    ("POST", f"{P}/group-assignments"): ("CREATE_PRODUCT_GROUP_ASSIGNMENT", "ProductGroupAssignment"),
    ("POST", f"{P}/group-assignments/{{assignment_id}}/deactivate"): ("DEACTIVATE_PRODUCT_GROUP_ASSIGNMENT", "ProductGroupAssignment"),
    ("POST", f"{P}/group-assignments/{{assignment_id}}/reactivate"): ("REACTIVATE_PRODUCT_GROUP_ASSIGNMENT", "ProductGroupAssignment"),
    ("POST", f"{P}/assets"): ("CREATE_PRODUCT_ASSET", "ProductAsset"),
    ("PUT", f"{P}/assets/{{asset_id}}"): ("UPDATE_PRODUCT_ASSET", "ProductAsset"),
    ("POST", f"{P}/assets/{{asset_id}}/set-primary"): ("SET_PRIMARY_PRODUCT_ASSET", "ProductAsset"),
    ("POST", f"{P}/assets/{{asset_id}}/deactivate"): ("DEACTIVATE_PRODUCT_ASSET", "ProductAsset"),
    ("POST", f"{P}/assets/{{asset_id}}/reactivate"): ("REACTIVATE_PRODUCT_ASSET", "ProductAsset"),
    ("POST", f"{P}/first-use"): ("REGISTER_PRODUCT_FIRST_USE", "Product"),
    ("POST", f"{P}/first-use/manual"): ("REGISTER_PRODUCT_FIRST_USE", "Product"),
}
READS_BY_POST = {
    ("POST", f"{V}/units-of-measure/batch-lookup"),
    ("POST", f"{V}/products/batch-lookup"),
    ("POST", f"{V}/presentations/batch-lookup"),
}


def _writes(app) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method in {"post", "put", "patch", "delete"}
    }


def test_every_write_has_exactly_one_action(app) -> None:
    writes = _writes(app)
    assert READS_BY_POST <= writes
    assert writes - READS_BY_POST == set(CATALOG)
    assert len(CATALOG) == 63


def test_catalog_matches_the_service_constants() -> None:
    assert {action for action, _ in CATALOG.values()} == set(audit.ACTIONS)
    assert len(set(audit.ACTIONS)) == 62
    assert {entity for _, entity in CATALOG.values()} == set(audit.ENTITY_TYPES)
