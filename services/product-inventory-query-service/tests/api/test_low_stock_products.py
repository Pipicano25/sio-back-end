"""`low-stock-products` con dobles (T116; FR-022-50 a FR-022-52, FR-022-65; CP-95).

Historia 4, escenarios 1 a 4: solo aparecen los pares con `stock < mínimo` y política activa. Orden
`shortfall:desc` con continuación por pares; con `sort` explícito conduce CR (R-F) e Inventory evalúa el faltante.
"""

from __future__ import annotations

from uuid import uuid4

from tests.api.support import COST_WORDS, TABLET, keys_in, walk


def low_stock(world, client, query: str = "") -> dict:
    response = client.get(f"{world.base}/low-stock-products{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def test_only_strictly_below_minimum_with_active_policy(world, as_user) -> None:
    """Escenarios 1 a 4: 3 < 5 aparece con `shortfall = 2`; 5 = 5, 0 con mínimo 0 y sin política no aparecen.

    Spec 024 (FR-024-43): el par no trae imágenes aunque la presentación tenga una.
    """
    below = world.product("Clarityne", unit=TABLET, has_image=True)
    world.stock(below, "3")
    world.minimum(below, "5")
    at = world.product("Igual")
    world.stock(at, "5")
    world.minimum(at, "5")
    zero = world.product("Minimo cero")
    world.stock(zero, "0")
    world.minimum(zero, "0")
    world.product("Sin politica")  # stock 0 y sin política

    body = low_stock(world, as_user("inventario.test"))
    (pair,) = body["items"]
    assert pair == {
        "company_product_id": below.id, "display_name": "Clarityne", "internal_code": below.product.internal_code,
        "base_unit": {"id": str(TABLET.id), "code": "TAB", "name": "Tableta"}, "branch_id": str(world.branches[0]),
        "base_quantity": "3.0000", "minimum_stock": "5.0000", "shortfall": "2.0000", "policy_status": "ACTIVE",
    }
    assert body["sort_applied"] == "shortfall:desc" and body["has_next"] is False


def test_unregistered_balance_counts_as_zero(world, as_user) -> None:
    """FR-022-50: un par con política y sin registro de saldo tiene cantidad 0."""
    item = world.product("Sin movimientos")
    world.minimum(item, "2")
    (pair,) = low_stock(world, as_user("inventario.test"))["items"]
    assert (pair["base_quantity"], pair["shortfall"]) == ("0.0000", "2.0000")


def test_pairs_in_shortfall_order_and_continuation_by_pairs(world, as_user) -> None:
    """Varias sucursales por producto; `page_size = 1` recorre todos los pares sin omisiones ni duplicados."""
    expected = []
    for index in range(6):
        item = world.product(f"P {index}")
        for branch in (0, 1):
            world.stock(item, str(index), branch=branch)
            world.minimum(item, str(10 + branch), branch=branch)
            expected.append((10 + branch - index, item.id, str(world.branches[branch])))
    expected.sort(key=lambda row: (-row[0], row[1], row[2]))

    walked, pages = walk(as_user("inventario.test"), f"{world.base}/low-stock-products?page_size=1")
    assert [(item["company_product_id"], item["branch_id"]) for item in walked] == [(p, b) for _, p, b in expected]
    assert [item["shortfall"] for item in walked] == [f"{s}.0000" for s, _, _ in expected]
    assert all(page["sort_applied"] == "shortfall:desc" for page in pages)


def test_explicit_sort_makes_cr_drive_and_inventory_evaluate(world, as_user) -> None:
    """R-F: `sort=display_name` → CR conduce; Inventory calcula el faltante por lote con `balances` e INV-1."""
    for index, name in enumerate(["Zeta", "Alfa", "Media", "Beta"]):
        item = world.product(name)
        world.stock(item, "1", branch=0)
        world.minimum(item, str(2 + index), branch=0)
        if index % 2 == 0:  # además bajo mínimo en la sucursal 1
            world.minimum(item, "1", branch=1)
    world.product("Sin politica")
    client = as_user("inventario.test")
    walked, pages = walk(client, f"{world.base}/low-stock-products?sort=display_name&page_size=1")
    assert all(page["sort_applied"] == "display_name:asc" for page in pages)
    rows = [(item["display_name"], item["branch_id"]) for item in walked]
    order = {"Alfa": [str(world.branches[0])], "Beta": [str(world.branches[0])],
             "Media": sorted([str(world.branches[0]), str(world.branches[1])]),
             "Zeta": sorted([str(world.branches[0]), str(world.branches[1])])}
    assert rows == [(name, branch) for name in ("Alfa", "Beta", "Media", "Zeta") for branch in order[name]]
    log = world.fakes.log
    assert log.count("below_minimum_pairs") == 0
    assert log.count("search_products") > 0 and log.count("policies") > 0 and log.count("balances") > 0


def test_explicit_sort_walk_with_more_pairs_than_page_size_in_one_product(world, as_user) -> None:
    """R-F con un producto bajo mínimo en las dos sucursales y `page_size = 1`: el par pendiente no se pierde."""
    item = world.product("Unico")
    for branch in (0, 1):
        world.minimum(item, "3", branch=branch)
    walked, _ = walk(as_user("inventario.test"), f"{world.base}/low-stock-products?sort=internal_code:desc&page_size=1")
    assert sorted(i["branch_id"] for i in walked) == sorted(str(b) for b in world.branches)


def test_filters_apply_to_the_pairs(world, as_user) -> None:
    """Filtros de catálogo y de búsqueda se evalúan sobre los pares (CR y PC evaluadores de R-D)."""
    brand = uuid4()
    hit = world.product("Colgate", brand=brand)
    miss = world.product("Otra", brand=uuid4())
    inactive = world.product("Colgate inactivo", brand=brand, status="INACTIVE")
    for item in (hit, miss, inactive):
        world.minimum(item, "1")
    client = as_user("inventario.test")
    assert [i["company_product_id"] for i in low_stock(world, client, f"brand_id={brand}")["items"]] == [hit.id]
    assert [i["company_product_id"] for i in low_stock(world, client, "search=colgate")["items"]] == [hit.id]
    assert {i["company_product_id"] for i in low_stock(world, client, "status=ALL")["items"]} == {
        hit.id, miss.id, inactive.id}


def test_without_policies_the_answer_is_empty_and_final(world, as_user) -> None:
    """CP-95."""
    item = world.product("Sin politica")
    world.stock(item, "0")
    body = low_stock(world, as_user("inventario.test"))
    assert body["items"] == [] and body["has_next"] is False and body["next_cursor"] is None


def test_requires_minimums_and_stock_permissions(world, as_token, make_token, as_user) -> None:
    """FR-022-52: el permiso funcional no basta; hacen falta los de mínimos **y** existencias."""
    functional = "perm:product-inventory-query:low_stock_products:read"
    stock = "perm:product-inventory-query:stock:read"
    minimums = "perm:inventory:product-policies:read"
    for roles in ((functional,), (functional, stock), (functional, minimums)):
        response = as_token(make_token(*roles)).get(f"{world.base}/low-stock-products")
        assert response.status_code == 403, roles
    assert as_token(make_token(functional, stock, minimums)).get(f"{world.base}/low-stock-products").status_code == 200
    assert as_user("ventas.test").get(f"{world.base}/low-stock-products").status_code == 403


def test_stock_state_and_minimum_state_are_not_parameters_here(world, as_user) -> None:
    client = as_user("inventario.test")
    for query in ("stock_state=IN_STOCK", "minimum_state=BELOW_MINIMUM", f"price_list_id={uuid4()}"):
        assert client.get(f"{world.base}/low-stock-products?{query}").status_code == 422, query


def test_inventory_failure_is_503(world, as_user) -> None:
    item = world.product("Producto")
    world.minimum(item, "2")
    world.fakes.inventory.fail.add("below_minimum_pairs")
    assert as_user("inventario.test").get(f"{world.base}/low-stock-products").status_code == 503


def test_no_cost_fields(world, as_user) -> None:
    item = world.product("Producto")
    world.minimum(item, "2")
    keys = keys_in(low_stock(world, as_user("inventario.test")))
    assert not {key for key in keys if any(word in key for word in COST_WORDS)} and "inventory_value" not in keys


def test_include_images_is_not_a_low_stock_parameter(world, as_user) -> None:
    """Spec 024 (FR-024-43): low-stock no trae imágenes; `include_images` responde `422`."""
    response = as_user("inventario.test").get(f"{world.base}/low-stock-products?include_images=true")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "include_images"
