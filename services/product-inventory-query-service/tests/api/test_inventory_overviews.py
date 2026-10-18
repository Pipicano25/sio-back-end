"""`inventory-overviews` con dobles (T108; FR-022-40 a FR-022-43, RC-022-5; CP-31 a CP-48).

Historia 3, escenarios 1 a 5: equivalencias sin multiplicar existencias, cualquier sucursal de la empresa con
membresía (A-08), consolidado igual a la suma de las sucursales, `NOT_REGISTERED` frente a saldo 0 y otra
empresa con `404`.
"""

from __future__ import annotations

from dataclasses import replace

from tests.api.support import COST_WORDS, TABLET, keys_in, walk


def overviews(world, client, query: str = "") -> dict:
    response = client.get(f"{world.base}/inventory-overviews{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def only(body) -> dict:
    (item,) = body["items"]
    return item


def test_equivalences_never_multiply_stock_by_presentation(world, as_user) -> None:
    """Escenario 1, CP-34 y CP-35: 120 tabletas y caja x 10 → 12 cajas y resto 0, nunca 120 cajas."""
    item = world.product("Clarityne", unit=TABLET,
                         presentations=(("TAB", "Tableta", "1"), ("CJ10", "Caja x 10", "10"), ("CJ7", "Caja x 7", "7")))
    world.stock(item, "120")
    found = only(overviews(world, as_user("inventario.test")))
    stock = found["stock"]
    assert stock["base_unit"]["code"] == "TAB" and stock["total_base_quantity"] == "120.0000"
    equivalences = {e["company_product_presentation_id"]: e for e in stock["equivalences"]}
    box10 = equivalences[str(item.presentations[1].id)]
    box7 = equivalences[str(item.presentations[2].id)]
    assert (box10["whole_units"], box10["remainder_base_quantity"]) == (12, "0.0000")
    assert (box7["whole_units"], box7["remainder_base_quantity"]) == (17, "1.0000")
    assert len(found["presentations"]) == 3 and all("price" not in p for p in found["presentations"])
    assert len(stock["branches"]) == 2  # una fila por sucursal, no por presentación


def test_decimals_have_four_places(world, as_user) -> None:
    """CP-36."""
    item = world.product("Aceite a granel", presentations=(("L", "Litro", "1"), ("G", "Garrafa 3.5 L", "3.5")))
    world.stock(item, "10.25")
    stock = only(overviews(world, as_user("inventario.test")))["stock"]
    assert stock["total_base_quantity"] == "10.2500"
    garrafa = next(e for e in stock["equivalences"] if e["company_product_presentation_id"] == str(item.presentations[1].id))
    assert (garrafa["whole_units"], garrafa["remainder_base_quantity"]) == (2, "3.2500")


def test_one_branch_several_branches_and_company(world, as_user) -> None:
    """Escenario 3, CP-37 y CP-43 a CP-45: el consolidado es la suma de las sucursales del alcance."""
    item = world.product("Arroz")
    world.stock(item, "7", branch=0)
    world.stock(item, "5", branch=1)
    client = as_user("inventario.test")
    one = only(overviews(world, client, f"branch_id={world.branches[1]}"))["stock"]
    assert one["total_base_quantity"] == "5.0000" and [b["branch_id"] for b in one["branches"]] == [str(world.branches[1])]
    both = only(overviews(world, client, f"branch_id={world.branches[0]}&branch_id={world.branches[1]}"))["stock"]
    assert both["total_base_quantity"] == "12.0000" and len(both["branches"]) == 2
    company = only(overviews(world, client, "scope=COMPANY"))["stock"]
    assert company["total_base_quantity"] == "12.0000"
    assert sorted(b["base_quantity"] for b in company["branches"]) == ["5.0000", "7.0000"]


def test_any_branch_of_the_company_is_readable(world, as_user) -> None:
    """Escenario 2, CP-46 y A-08: no se exige asignación a la sucursal, solo membresía y permiso de lectura."""
    item = world.product("Arroz")
    world.stock(item, "3", branch=1)
    body = overviews(world, as_user("ventas.test"), f"branch_id={world.branches[1]}")
    assert only(body)["stock"]["total_base_quantity"] == "3.0000"


def test_inactive_branch_only_when_requested_explicitly(world, as_user) -> None:
    """FR-022-23: el consolidado usa las sucursales activas; una inactiva solo si se pide por `branch_id`."""
    inactive = next(b.id for b in world.fakes.oc.branch_rows[world.company] if b.status == "ACTIVE")
    world.fakes.oc.branch_rows[world.company] = [
        row if row.id != inactive else replace(row, status="INACTIVE") for row in world.fakes.oc.branch_rows[world.company]
    ]
    item = world.product("Arroz")
    world.fakes.inventory.set_balance(world.company, inactive, item.product.id, "4")
    client = as_user("inventario.test")
    company = only(overviews(world, client))["stock"]
    assert str(inactive) not in {b["branch_id"] for b in company["branches"]}
    explicit = only(overviews(world, client, f"branch_id={inactive}"))["stock"]
    assert explicit["total_base_quantity"] == "4.0000"


def test_not_registered_is_distinct_from_a_registered_zero(world, as_user) -> None:
    """Escenario 4, CP-32, CP-33 y FR-022-70."""
    item = world.product("Arroz")
    world.stock(item, "0", branch=0)
    branches = {b["branch_id"]: b for b in only(overviews(world, as_user("inventario.test")))["stock"]["branches"]}
    assert branches[str(world.branches[0])] == {"branch_id": str(world.branches[0]), "base_quantity": "0.0000",
                                                "balance_state": "REGISTERED", "minimum_stock": None,
                                                "minimum_state": "NO_POLICY"}
    assert branches[str(world.branches[1])]["balance_state"] == "NOT_REGISTERED"
    assert branches[str(world.branches[1])]["base_quantity"] == "0.0000"


def test_minimums_only_with_the_policies_permission(world, as_user) -> None:
    """CP-38 a CP-42: sin política, mínimo 0, menor, igual y mayor; `ventas` no ve mínimos."""
    cases = {"Sin politica": ("3", None), "Minimo cero": ("0", "0"), "Menor": ("3", "5"), "Igual": ("5", "5"),
             "Mayor": ("9", "5")}
    for name, (quantity, minimum) in cases.items():
        item = world.product(name)
        world.stock(item, quantity)
        if minimum is not None:
            world.minimum(item, minimum)
    body = overviews(world, as_user("inventario.test"), f"branch_id={world.branches[0]}")
    states = {i["display_name"]: i["stock"]["branches"][0] for i in body["items"]}
    assert {name: b["minimum_state"] for name, b in states.items()} == {
        "Sin politica": "NO_POLICY", "Minimo cero": "AT_MINIMUM", "Menor": "BELOW_MINIMUM", "Igual": "AT_MINIMUM",
        "Mayor": "ABOVE_MINIMUM",
    }
    assert states["Sin politica"]["minimum_stock"] is None and states["Menor"]["minimum_stock"] == "5.0000"

    ventas = overviews(world, as_user("ventas.test"), f"branch_id={world.branches[0]}")
    assert all("minimum_state" not in b for i in ventas["items"] for b in i["stock"]["branches"])
    assert world.fakes.log.count("policies") == 1  # solo la consulta de inventario


def test_minimum_state_filter(world, as_user) -> None:
    """FR-022-43: `minimum_state` (R-D si hay política, evaluado sobre candidatos si es `NO_POLICY`)."""
    below = world.product("Menor")
    world.stock(below, "1")
    world.minimum(below, "4")
    above = world.product("Mayor")
    world.stock(above, "8")
    world.minimum(above, "4")
    none = world.product("Sin politica")
    world.stock(none, "8")
    client = as_user("inventario.test")
    body = overviews(world, client, "minimum_state=BELOW_MINIMUM")
    assert [i["company_product_id"] for i in body["items"]] == [below.id]
    assert body["sort_applied"] == "company_product_id:asc"
    no_policy = overviews(world, client, "minimum_state=NO_POLICY")
    assert none.id in {i["company_product_id"] for i in no_policy["items"]}
    assert no_policy["sort_applied"] == "display_name:asc"


def test_minimum_state_filter_without_policies_permission_is_403(world, as_user) -> None:
    """CP-63: `ventas` no tiene `product-policies:read`."""
    response = as_user("ventas.test").get(f"{world.base}/inventory-overviews?minimum_state=BELOW_MINIMUM")
    assert response.status_code == 403
    assert world.fakes.log.total() == 0


def test_stock_state_filters(world, as_user) -> None:
    """`IN_STOCK` conduce Inventory (R-D); `OUT_OF_STOCK` se evalúa sobre los candidatos de CR (R-E)."""
    with_stock = world.product("Con saldo")
    world.stock(with_stock, "2")
    zero = world.product("Saldo cero")
    world.stock(zero, "0")
    never = world.product("Sin registro")
    client = as_user("inventario.test")
    in_stock = overviews(world, client, "stock_state=IN_STOCK")
    assert [i["company_product_id"] for i in in_stock["items"]] == [with_stock.id]
    out = overviews(world, client, "stock_state=OUT_OF_STOCK")
    assert {i["company_product_id"] for i in out["items"]} == {zero.id, never.id}


def test_base_set_is_products_with_inventory_control(world, as_user) -> None:
    """FR-022-40: un producto sin control de inventario no aparece, ni siquiera conduciendo Inventory."""
    controlled = world.product("Controlado")
    service = world.product("Servicio de domicilio", inventory_control_enabled=False)
    world.stock(controlled, "1")
    world.stock(service, "1")
    client = as_user("inventario.test")
    assert [i["company_product_id"] for i in overviews(world, client)["items"]] == [controlled.id]
    assert [i["company_product_id"] for i in overviews(world, client, "stock_state=IN_STOCK")["items"]] == [controlled.id]


def test_other_company_is_404(world, as_user) -> None:
    """Escenario 5 y CP-48."""
    response = as_user("inventario.test").get(f"/api/v1/companies/{world.other_company}/inventory-overviews")
    assert response.status_code == 404


def test_product_appears_once_and_walk_has_no_duplicates(world, as_user) -> None:
    """CP-31 y CP-34: un producto con varias presentaciones y saldo en dos sucursales es un solo elemento."""
    created = [world.product(f"P {index:02d}", presentations=(("U", "Unidad", "1"), ("C", "Caja", "6")))
               for index in range(12)]
    for item in created:
        world.stock(item, "6", branch=0)
        world.stock(item, "6", branch=1)
    walked, _ = walk(as_user("inventario.test"), f"{world.base}/inventory-overviews?page_size=5")
    assert [i["company_product_id"] for i in walked] == [item.id for item in created]
    assert all(i["stock"]["total_base_quantity"] == "12.0000" for i in walked)


def test_no_cost_fields(world, as_user) -> None:
    item = world.product("Arroz")
    world.stock(item, "3")
    for user in ("ventas.test", "inventario.test", "supervisor.test"):
        keys = keys_in(overviews(world, as_user(user)))
        assert not {key for key in keys if any(word in key for word in COST_WORDS)}
        assert "inventory_value" not in keys
