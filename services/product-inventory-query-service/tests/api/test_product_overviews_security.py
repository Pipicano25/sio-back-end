"""Seguridad de `product-overviews` (T103; FR-022-10 a FR-022-15, FR-022-20 a FR-022-23, RC-022-1, RC-022-8).

CP-47, CP-48, CP-56 a CP-64 y CP-125. La autorización con OC (token del usuario) va **antes** de cualquier llamada
a CR, PC o Inventory, y la cuenta técnica nunca amplía lo que ve el usuario.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import USER_ROLES

TECHNICAL = {"search_products", "search_products_evaluator", "presentations_by_products", "resolve_prices", "summaries",
             "match_candidates", "match_page", "balances", "policies", "product_set", "below_minimum_pairs",
             "presentations", "summary", "count_adopted"}
ENDPOINTS = ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary")


def technical_calls(world) -> int:
    return sum(world.fakes.log.count(name) for name in TECHNICAL)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_without_token_or_with_invalid_token_is_401(world, as_token, endpoint) -> None:
    """CP-56 y CP-57."""
    for token in (None, "no-es-un-jwt"):
        response = as_token(token).get(f"{world.base}/{endpoint}")
        assert response.status_code == 401
        assert response.json()["code"] == "PRODUCT_INVENTORY_QUERY.UNAUTHENTICATED"
    assert world.fakes.log.total() == 0


@pytest.mark.parametrize("user", ["compras.test", "reportes.test", "consulta.test"])
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_without_functional_permission_is_403_without_revealing_it(world, as_user, user, endpoint) -> None:
    """CP-58: `compras`, `reportes` y `consulta` no tienen ninguna de las cuatro consultas."""
    response = as_user(user).get(f"{world.base}/{endpoint}")
    assert response.status_code == 403
    assert "perm:" not in response.text
    assert world.fakes.log.total() == 0


def test_non_member_and_unknown_company_are_404_and_nothing_else_is_called(world, as_user) -> None:
    """CP-48 y CP-59: el mismo `404` para otra empresa y para una inexistente; ninguna llamada técnica."""
    world.product("Producto")
    client = as_user("ventas.test")
    responses = [client.get(f"/api/v1/companies/{company}/product-overviews")
                 for company in (world.other_company, uuid4())]
    assert [r.status_code for r in responses] == [404, 404]
    assert responses[0].json()["detail"] == responses[1].json()["detail"]
    assert technical_calls(world) == 0


def test_branch_of_another_company_is_404(world, as_user) -> None:
    """CP-47."""
    response = as_user("ventas.test").get(f"{world.base}/product-overviews?branch_id={world.other_branches[0]}")
    assert response.status_code == 404
    assert technical_calls(world) == 0


def test_branch_and_scope_together_is_422(world, as_user) -> None:
    response = as_user("ventas.test").get(f"{world.base}/product-overviews?branch_id={world.branches[0]}&scope=COMPANY")
    assert response.status_code == 422


def test_membership_is_checked_with_the_user_token_before_anything_else(world, as_user, authorizations, user_token) -> None:
    """FR-022-11 y FR-022-13: OC recibe el token del usuario y va primero."""
    world.product("Producto")
    response = as_user("ventas.test").get(f"{world.base}/product-overviews")
    assert response.status_code == 200
    assert authorizations[-1].startswith("Bearer ") and authorizations[-1] != "Bearer token-tecnico"
    order = world.fakes.log.order
    first_technical = min(index for index, name in enumerate(order) if name in TECHNICAL)
    assert {"operational_access", "branches"} <= set(order[:first_technical])


def test_stock_filter_without_stock_permission_is_403(world, as_token, make_token) -> None:
    """CP-63: un filtro de un bloque no visible es `403`, antes de llamar a cualquier dependencia."""
    roles = [role for role in USER_ROLES["ventas.test"] if not role.endswith(":stock:read")]
    response = as_token(make_token(*roles)).get(f"{world.base}/product-overviews?stock_state=IN_STOCK")
    assert response.status_code == 403
    assert world.fakes.log.total() == 0


def test_technical_account_does_not_widen_the_response(world, as_token, make_token) -> None:
    """CP-64: aunque la cuenta técnica puede leer precios y existencias, el usuario sin esos permisos no los ve."""
    item = world.product("Producto")
    world.fakes.cr.set_price(item.presentations[0], "1000.00")
    world.stock(item, "9")
    roles = ["perm:product-inventory-query:product_overviews:read"]
    body = as_token(make_token(*roles)).get(f"{world.base}/product-overviews").json()
    (found,) = body["items"]
    assert "stock" not in found and all("price" not in p for p in found["presentations"])
    assert world.fakes.log.count("resolve_prices") == 0 and world.fakes.log.count("balances") == 0


def test_ventas_has_no_costs_or_valuation_and_inventario_has_no_prices(world, as_user) -> None:
    """CP-60 y CP-61."""
    item = world.product("Producto")
    world.fakes.cr.set_price(item.presentations[0], "1000.00")
    world.stock(item, "9")
    ventas = as_user("ventas.test").get(f"{world.base}/product-overviews").text
    inventario = as_user("inventario.test").get(f"{world.base}/product-overviews").text
    assert "inventory_value" not in ventas and "cost" not in ventas
    assert '"price"' in ventas and '"price"' not in inventario
    assert "minimum_state" not in ventas and "minimum_state" in inventario


def test_valid_cursor_after_losing_membership_is_404_and_after_losing_permission_is_403(world, as_user, as_token,
                                                                                        make_token) -> None:
    """CP-125 y RC-022-8: el cursor nunca reemplaza la autorización."""
    for index in range(25):
        world.product(f"Producto {index:02d}")
    cursor = as_user("ventas.test").get(f"{world.base}/product-overviews").json()["next_cursor"]

    without_permission = as_token(make_token("perm:operational-context:all:read"))
    assert without_permission.get(f"{world.base}/product-overviews?cursor={cursor}").status_code == 403

    world.fakes.oc.members.discard(world.company)
    assert as_user("ventas.test").get(f"{world.base}/product-overviews?cursor={cursor}").status_code == 404


def test_rows_of_another_company_never_appear(world, as_user) -> None:
    """CP-70 y FR-022-12: CR solo devuelve productos de la empresa de la ruta; los de otra empresa no aparecen."""
    own = world.product("Propio")
    world.product("Ajeno", company=world.other_company)
    items = as_user("ventas.test").get(f"{world.base}/product-overviews").json()["items"]
    assert [i["company_product_id"] for i in items] == [own.id]


def test_errors_never_reveal_the_dependency(world, as_user) -> None:
    """FR-022-71: la dependencia que falló queda solo en el log."""
    world.product("Producto")
    world.fakes.inventory.fail.add("balances")
    response = as_user("ventas.test").get(f"{world.base}/product-overviews")
    assert response.status_code == 503
    body = response.json()
    assert not {"dependency", "provider", "operation", "cause"} & set(body)
    assert "inventory" not in body["detail"].lower() and "balances" not in response.text
