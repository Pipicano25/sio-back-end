"""`product-overviews` con dobles (T100; FR-022-30 a FR-022-35, FR-022-70; CP-01 a CP-09, CP-49 a CP-55, CP-74).

Historia 1, escenarios 1 a 5: presentaciones con y sin precio, filtros combinados, bloque de existencias según el
permiso, producto sin marca, imagen ni precio, y CR caído (`503`, nunca una lista vacía).
"""

from __future__ import annotations

from uuid import uuid4

from product_inventory_query_service.application.ports import PriceResult
from tests.api.support import COST_WORDS, keys_in, walk
from tests.conftest import USER_ROLES

PIQ = "perm:product-inventory-query"


def overviews(world, client, query: str = ""):
    response = client.get(f"{world.base}/product-overviews{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def by_id(body) -> dict:
    return {item["company_product_id"]: item for item in body["items"]}


def by_code(item) -> dict:
    """Las presentaciones van en el orden estable de CR-2 (`company_product_id`, `id`)."""
    return {presentation["code"]: presentation for presentation in item["presentations"]}


def test_one_and_several_presentations_with_and_without_price(world, as_user) -> None:
    """CP-01, CP-02, CP-06, CP-07 y escenario 1: las dos presentaciones aparecen; una sin precio."""
    single = world.product("Agua 600 ml")
    double = world.product("Crema dental 100 ml", presentations=(("UND", "Unidad", "1"), ("CJ12", "Caja x 12", "12")))
    priced = world.fakes.cr.set_price(double.presentations[1], "4500.00")

    body = overviews(world, as_user("ventas.test"))
    items = by_id(body)
    assert len(items[single.id]["presentations"]) == 1
    presentations = by_code(items[double.id])
    unit, box = presentations["UND"], presentations["CJ12"]
    assert (box["code"], box["name"], box["base_quantity_factor"]) == ("CJ12", "Caja x 12", "12.0000")
    assert box["price"] == {"price_list_id": str(priced.price_list_id), "price_list_item_id": str(priced.price_list_item_id),
                            "unit_price": "4500.00", "currency_code": "COP", "resolution": "PRICE_LIST_ITEM"}
    # Sin precio configurado, precio y moneda son `null`: la moneda solo viene con el precio de CR.
    assert unit["price"]["unit_price"] is None and unit["price"]["currency_code"] is None
    assert unit["price"]["resolution"] == "NO_PRICE_IN_LIST"


def test_product_fields_categories_and_brand(world, as_user) -> None:
    """CP-03, CP-04, CP-05 y FR-022-31: varias categorías anidadas, una sola fila por producto."""
    first, second, brand = uuid4(), uuid4(), uuid4()
    branded = world.product("Jabón", brand=brand, categories={first, second}, identifiers={"7701234"})
    plain = world.product("Bolsa", internal_code="B-01")

    items = by_id(overviews(world, as_user("ventas.test"), f"category_id={first}&category_id={second}"))
    assert list(items) == [branded.id]
    item = items[branded.id]
    assert item["brand"]["id"] == str(brand) and len(item["categories"]) == 2
    assert item["identifiers"][0]["value"] == "7701234"
    assert set(item) == {
        "company_product_id", "global_product_id", "display_name", "canonical_name", "internal_code", "reference_code",
        "status", "global_status", "product_type", "brand", "categories", "identifiers", "base_unit",
        "presentations", "stock",
    }
    assert item["base_unit"] == {"id": "00000000-0000-4000-8000-0000000000aa", "code": "UND", "name": "Unidad"}

    no_brand = by_id(overviews(world, as_user("ventas.test"), "internal_code=b-01"))[plain.id]
    assert no_brand["brand"] is None and no_brand["categories"] == []


def test_status_active_by_default_inactive_with_status(world, as_user) -> None:
    """CP-08, CP-09 y FR-022-35."""
    active = world.product("Activo")
    inactive = world.product("Inactivo", status="INACTIVE")
    client = as_user("ventas.test")
    assert list(by_id(overviews(world, client))) == [active.id]
    assert list(by_id(overviews(world, client, "status=INACTIVE"))) == [inactive.id]
    assert set(by_id(overviews(world, client, "status=ALL"))) == {active.id, inactive.id}


def test_global_product_inactive_still_appears_with_its_global_status(world, as_user) -> None:
    item = world.product("Descontinuado global", global_status="INACTIVE")
    assert by_id(overviews(world, as_user("ventas.test")))[item.id]["global_status"] == "INACTIVE"


def test_product_without_brand_image_or_price(world, as_user) -> None:
    """Escenario 4: aparece con `brand = null`, presentación sin imagen (spec 024) y precio no configurado."""
    item = world.product("Sin datos")
    found = by_id(overviews(world, as_user("ventas.test")))[item.id]
    presentation = found["presentations"][0]
    assert found["brand"] is None
    assert (presentation["has_image"], presentation["asset_id"], presentation["image_url"]) == (False, None, None)
    assert presentation["price"]["unit_price"] is None


def test_stock_block_only_with_stock_permission_and_without_minimums_for_ventas(world, as_user, make_token, as_token) -> None:
    """Escenario 3 y FR-022-14: sin `stock:read` no hay bloque `stock`; `ventas` no ve mínimos."""
    item = world.product("Arroz")
    world.stock(item, "7")
    world.minimum(item, "10")

    seen = by_id(overviews(world, as_user("ventas.test")))[item.id]
    assert seen["stock"]["total_base_quantity"] == "7.0000"
    assert all("minimum_stock" not in b and "minimum_state" not in b for b in seen["stock"]["branches"])

    without_stock = [role for role in USER_ROLES["ventas.test"] if role != f"{PIQ}:stock:read"]
    hidden = by_id(overviews(world, as_token(make_token(*without_stock))))[item.id]
    assert "stock" not in hidden

    with_minimums = by_id(overviews(world, as_user("supervisor.test")))[item.id]
    branch = next(b for b in with_minimums["stock"]["branches"] if b["branch_id"] == str(world.branches[0]))
    assert (branch["minimum_stock"], branch["minimum_state"]) == ("10.0000", "BELOW_MINIMUM")


def test_prices_block_only_with_price_permission(world, as_user) -> None:
    """CP-61: `inventario` no tiene `price_list_items:read`: ninguna presentación lleva `price`."""
    item = world.product("Aceite")
    world.fakes.cr.set_price(item.presentations[0], "9800.00")
    seen = by_id(overviews(world, as_user("inventario.test")))[item.id]
    assert all("price" not in p for p in seen["presentations"])
    assert world.fakes.log.count("resolve_prices") == 0


def test_price_list_id_is_the_only_list_and_resolution_codes_pass_through(world, as_user) -> None:
    """CP-49 a CP-55 y FR-022-33: una sola lista; el precio de otra lista no se usa; las `resolution` de CR."""
    item = world.product("Leche", presentations=(("UND", "Unidad", "1"), ("SIX", "Six pack", "6")))
    own_list = uuid4()
    world.fakes.cr.set_price(item.presentations[0], "3200.00", price_list_id=own_list)
    # CR informa que su lista no aplica a la segunda presentación: se entrega tal cual, sin buscar en otra lista.
    world.fakes.cr.prices[item.presentations[1].id] = PriceResult(
        item.presentations[1].id, "PRICE_LIST_NOT_APPLICABLE", None, None, own_list, None)

    body = overviews(world, as_user("ventas.test"), f"price_list_id={own_list}")
    presentations = by_code(by_id(body)[item.id])
    unit, six = presentations["UND"], presentations["SIX"]
    assert unit["price"]["unit_price"] == "3200.00" and unit["price"]["price_list_id"] == str(own_list)
    assert six["price"] == {"price_list_id": str(own_list), "price_list_item_id": None, "unit_price": None,
                            "currency_code": None, "resolution": "PRICE_LIST_NOT_APPLICABLE"}
    assert world.fakes.cr.price_lists_requested == {own_list}


def test_combined_filters(world, as_user) -> None:
    """CP-74: `search` + marca + imagen + existencias en una sucursal (R-B con PC e Inventory por lote)."""
    brand = uuid4()
    hit = world.product("Colgate Triple", brand=brand, has_image=True)
    no_image = world.product("Colgate Herbal", brand=brand)
    no_stock = world.product("Colgate Kids", brand=brand, has_image=True)
    other_brand = world.product("Colgate Max", brand=uuid4(), has_image=True)
    world.product("Otra crema", brand=brand, has_image=True)
    for item in (hit, no_image, other_brand):
        world.stock(item, "5")
    world.stock(no_stock, "0")

    query = f"search=colgate&brand_id={brand}&has_image=true&stock_state=IN_STOCK&branch_id={world.branches[0]}"
    body = overviews(world, as_user("ventas.test"), query)
    assert [item["company_product_id"] for item in body["items"]] == [hit.id]
    assert body["sort_applied"] == "display_name:asc"


def test_commercial_relationship_down_is_503_never_an_empty_list(world, as_user) -> None:
    """Escenario 5 y CP-65."""
    world.product("Producto")
    world.fakes.cr.fail.add("search_products")
    response = as_user("ventas.test").get(f"{world.base}/product-overviews")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE" and "items" not in body
    assert "commercial" not in response.text.lower()


def test_any_dependency_failure_during_enrichment_is_503(world, as_user) -> None:
    """CP-65 a CP-67: un fallo de PC, CR-2 o Inventory al enriquecer es `503` completo."""
    world.product("Producto")
    client = as_user("ventas.test")
    for fake, operation in ((world.fakes.pc, "summaries"), (world.fakes.cr, "presentations_by_products"),
                            (world.fakes.inventory, "balances"), (world.fakes.pc, "presentations"),
                            (world.fakes.cr, "resolve_prices")):
        fake.fail = {operation}
        assert client.get(f"{world.base}/product-overviews").status_code == 503, operation
        fake.fail = set()


def test_no_cost_fields_in_the_response(world, as_user) -> None:
    item = world.product("Arroz")
    world.stock(item, "3")
    for user in ("ventas.test", "inventario.test", "supervisor.test"):
        keys = keys_in(overviews(world, as_user(user)))
        assert not {key for key in keys if any(word in key for word in COST_WORDS)}
        assert "inventory_value" not in keys


def test_pages_have_at_most_page_size_and_walk_the_whole_list(world, as_user) -> None:
    for index in range(23):
        world.product(f"Producto {index:02d}")
    items, pages = walk(as_user("ventas.test"), f"{world.base}/product-overviews?page_size=10")
    assert [len(page["items"]) for page in pages] == [10, 10, 3]
    assert [item["display_name"] for item in items] == [f"Producto {index:02d}" for index in range(23)]
