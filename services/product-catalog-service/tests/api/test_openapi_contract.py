"""El OpenAPI coincide con `contracts/rest-api.md` (puerta de calidad 5, RC-14).

`EXPECTED` transcribe las rutas del contrato; cualquier ruta nueva, eliminada o
renombrada obliga a actualizar el contrato y esta prueba en el mismo cambio.
"""

from product_catalog_service.main import create_app

P = "/api/v1"


def _catalog(prefix: str, extra: set[tuple[str, str]] = frozenset()) -> set[tuple[str, str]]:
    item = f"{prefix}/{{item_id}}"
    return {
        ("GET", prefix),
        ("POST", prefix),
        ("GET", item),
        ("PUT", item),
        ("POST", f"{item}/deactivate"),
        ("POST", f"{item}/reactivate"),
        *extra,
    }


EXPECTED = (
    _catalog(f"{P}/units-of-measure", {("POST", f"{P}/units-of-measure/batch-lookup")})
    | _catalog(f"{P}/packaging-types")
    | _catalog(f"{P}/brands")
    | _catalog(f"{P}/group-types")
    | _catalog(
        f"{P}/categories",
        {
            ("GET", f"{P}/categories/{{category_id}}/children"),
            ("GET", f"{P}/categories/{{category_id}}/descendants"),
            ("GET", f"{P}/categories/{{category_id}}/ancestors"),
            ("GET", f"{P}/categories/{{category_id}}/attributes"),
            ("POST", f"{P}/categories/{{category_id}}/attributes"),
            ("PUT", f"{P}/categories/{{category_id}}/attributes/{{association_id}}"),
            ("POST", f"{P}/categories/{{category_id}}/attributes/{{association_id}}/deactivate"),
            ("POST", f"{P}/categories/{{category_id}}/attributes/{{association_id}}/reactivate"),
        },
    )
    | _catalog(
        f"{P}/attribute-definitions",
        {
            ("GET", f"{P}/attribute-definitions/{{definition_id}}/options"),
            ("POST", f"{P}/attribute-definitions/{{definition_id}}/options"),
            ("PUT", f"{P}/attribute-definitions/{{definition_id}}/options/{{option_id}}"),
            ("POST", f"{P}/attribute-definitions/{{definition_id}}/options/{{option_id}}/deactivate"),
            ("POST", f"{P}/attribute-definitions/{{definition_id}}/options/{{option_id}}/reactivate"),
        },
    )
    | {
        # Productos §6.1
        ("GET", f"{P}/products"),
        ("POST", f"{P}/products"),
        ("GET", f"{P}/products/{{product_id}}"),
        ("PUT", f"{P}/products/{{product_id}}"),
        ("POST", f"{P}/products/{{product_id}}/deactivate"),
        ("POST", f"{P}/products/{{product_id}}/reactivate"),
        ("GET", f"{P}/products/{{product_id}}/completeness"),
        ("GET", f"{P}/products/{{product_id}}/applicable-attributes"),
        ("POST", f"{P}/products/batch-lookup"),
        ("GET", f"{P}/products/by-identifier/{{value}}"),
        # Spec 022: PC-1 y PC-2 (lecturas por POST)
        ("POST", f"{P}/products/summaries/batch-lookup"),
        ("POST", f"{P}/products/match"),
        # Categorías del producto §6.2
        ("GET", f"{P}/products/{{product_id}}/categories"),
        ("POST", f"{P}/products/{{product_id}}/categories"),
        ("POST", f"{P}/products/{{product_id}}/categories/{{association_id}}/set-primary"),
        ("POST", f"{P}/products/{{product_id}}/categories/{{association_id}}/deactivate"),
        # Valores §6.3
        ("GET", f"{P}/products/{{product_id}}/attribute-values"),
        ("PUT", f"{P}/products/{{product_id}}/attribute-values/{{definition_id}}"),
        ("DELETE", f"{P}/products/{{product_id}}/attribute-values/{{definition_id}}"),
        # Presentaciones §6.4
        ("GET", f"{P}/products/{{product_id}}/presentations"),
        ("POST", f"{P}/products/{{product_id}}/presentations"),
        ("GET", f"{P}/presentations/{{presentation_id}}"),
        ("PUT", f"{P}/presentations/{{presentation_id}}"),
        ("POST", f"{P}/presentations/{{presentation_id}}/deactivate"),
        ("POST", f"{P}/presentations/{{presentation_id}}/reactivate"),
        ("POST", f"{P}/presentations/batch-lookup"),
        # Identificadores §6.5
        ("GET", f"{P}/products/{{product_id}}/identifiers"),
        ("POST", f"{P}/products/{{product_id}}/identifiers"),
        ("POST", f"{P}/products/{{product_id}}/identifiers/{{identifier_id}}/set-primary"),
        ("POST", f"{P}/products/{{product_id}}/identifiers/{{identifier_id}}/deactivate"),
        ("POST", f"{P}/products/{{product_id}}/identifiers/{{identifier_id}}/reactivate"),
        # Grupos del producto §6.6
        ("GET", f"{P}/products/{{product_id}}/group-assignments"),
        ("POST", f"{P}/products/{{product_id}}/group-assignments"),
        ("POST", f"{P}/products/{{product_id}}/group-assignments/{{assignment_id}}/deactivate"),
        ("POST", f"{P}/products/{{product_id}}/group-assignments/{{assignment_id}}/reactivate"),
        # Activos §6.7
        ("GET", f"{P}/products/{{product_id}}/assets"),
        ("POST", f"{P}/products/{{product_id}}/assets"),
        ("PUT", f"{P}/products/{{product_id}}/assets/{{asset_id}}"),
        ("POST", f"{P}/products/{{product_id}}/assets/{{asset_id}}/set-primary"),
        ("POST", f"{P}/products/{{product_id}}/assets/{{asset_id}}/deactivate"),
        ("POST", f"{P}/products/{{product_id}}/assets/{{asset_id}}/reactivate"),
        ("GET", f"{P}/products/{{product_id}}/assets/{{asset_id}}/content"),
        # Primer uso §6.8
        ("POST", f"{P}/products/{{product_id}}/first-use"),
        ("POST", f"{P}/products/{{product_id}}/first-use/manual"),
        # Grupos §7
        ("GET", f"{P}/group-types/{{group_type_id}}/groups"),
        ("POST", f"{P}/group-types/{{group_type_id}}/groups"),
        ("GET", f"{P}/groups/{{group_id}}"),
        ("PUT", f"{P}/groups/{{group_id}}"),
        ("GET", f"{P}/groups/{{group_id}}/children"),
        ("GET", f"{P}/groups/{{group_id}}/ancestors"),
        ("POST", f"{P}/groups/{{group_id}}/deactivate"),
        ("POST", f"{P}/groups/{{group_id}}/reactivate"),
        # Salud §8
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
    }
)


def _implemented() -> set[tuple[str, str]]:
    schema = create_app().openapi()
    return {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
    }


def test_openapi_matches_contract() -> None:
    implemented = _implemented()
    assert implemented - EXPECTED == set(), "Rutas sin contrato"
    assert EXPECTED - implemented == set(), "Rutas del contrato sin implementar"


def test_only_delete_is_attribute_value_removal() -> None:
    deletes = {path for method, path in _implemented() if method == "DELETE"}
    assert deletes == {f"{P}/products/{{product_id}}/attribute-values/{{definition_id}}"}
