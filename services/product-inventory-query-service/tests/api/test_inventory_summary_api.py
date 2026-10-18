"""`inventory-summary` con dobles (T112; FR-022-55 a FR-022-58, D-022-9, D-022-10, D-022-11).

CP-145 a CP-153: indicadores por propietario (CR cuenta los adoptados; INV-3 los de Inventory), como máximo 4
llamadas, ningún recorrido de saldos desde este servicio, categorías A a E, valoración solo con el permiso y sin
`quantities_by_base_unit` ni `products_out_of_stock`. Sin valoración económica (fuera de la spec 022).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.api.support import COST_WORDS, keys_in

READ_PATHS = {"balances", "policies", "product_set", "below_minimum_pairs", "search_products",
              "search_products_evaluator", "summaries", "presentations_by_products", "resolve_prices", "match_page",
              "match_candidates", "presentations", "units"}


def summary(world, client, query: str = "") -> dict:
    response = client.get(f"{world.base}/inventory-summary{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def seed_categories(world):
    """Un producto de cada categoría de FR-022-55 en la sucursal 0 (CP-151)."""
    positive = world.product("A saldo positivo")
    world.stock(positive, "5")
    zero = world.product("B saldo cero")
    world.stock(zero, "0")
    world.minimum(zero, "2")  # además, bajo mínimo con saldo 0
    world.product("C sin registro de saldo")
    inactive = world.product("D inactivo", status="INACTIVE")
    world.stock(inactive, "3")
    no_control = world.product("E sin control", inventory_control_enabled=False)
    world.stock(no_control, "4")
    return positive, zero, inactive, no_control


def test_indicators_by_owner_with_categories_a_to_e(world, as_user) -> None:
    """CP-150 a CP-152 y escenario 1 de la historia 5."""
    seed_categories(world)
    body = summary(world, as_user("inventario.test"))
    assert body["adopted_products"] == 3  # A, B y C: ACTIVE con control (D y E excluidos por CR)
    branch = next(b for b in body["branches"] if b["branch_id"] == str(world.branches[0]))
    # Inventory no conoce el estado comercial: D y E cuentan con saldo positivo (CP-150).
    assert branch == {"branch_id": str(world.branches[0]), "products_with_positive_balance": 3,
                      "products_with_zero_balance": 1, "products_with_policy": 1, "products_below_minimum": 1}
    # C (sin registro) no cuenta en ningún indicador de saldo (CP-152).
    assert body["consolidated"] == {"products_with_positive_balance": 3, "products_with_zero_balance": 1,
                                    "products_with_policy": 1, "products_below_minimum": 1}
    other = next(b for b in body["branches"] if b["branch_id"] == str(world.branches[1]))
    assert other["products_with_positive_balance"] == other["products_with_zero_balance"] == 0


@pytest.mark.parametrize("user", ["inventario.test", "supervisor.test"])
def test_at_most_four_calls_and_no_balance_walks(world, as_user, user) -> None:
    """FR-022-57 y CP-149: OC (2), CR (conteo) e INV-3; los dobles fallan si se recorren saldos o productos."""
    seed_categories(world)
    world.fakes.inventory.forbidden |= {"balances", "policies", "product_set", "below_minimum_pairs"}
    world.fakes.cr.forbidden |= {"search_products", "presentations_by_products", "resolve_prices"}
    world.fakes.pc.forbidden |= {"summaries", "match_page", "match_candidates", "presentations", "units"}
    summary(world, as_user(user))
    log = world.fakes.log
    assert log.total() <= 4
    assert (log.count("count_adopted"), log.count("summary")) == (1, 1)
    assert not any(log.count(name) for name in READ_PATHS)


def test_branch_scope(world, as_user) -> None:
    """Una sucursal: el consolidado es solo de esa sucursal; `adopted_products` sigue siendo de la empresa."""
    seed_categories(world)
    body = summary(world, as_user("inventario.test"), f"branch_id={world.branches[1]}")
    assert [b["branch_id"] for b in body["branches"]] == [str(world.branches[1])]
    assert body["consolidated"]["products_with_positive_balance"] == 0
    assert body["adopted_products"] == 3


def test_no_quantities_by_unit_no_out_of_stock_and_no_costs(world, as_user) -> None:
    """CP-147, CP-153 y D-022-10."""
    seed_categories(world)
    for user in ("inventario.test", "supervisor.test"):
        keys = keys_in(summary(world, as_user(user)))
        assert "quantities_by_base_unit" not in keys and "products_out_of_stock" not in keys
        assert not {key for key in keys if any(word in key for word in COST_WORDS)}


def test_summary_is_operational_only_for_every_user(world, as_user) -> None:
    """La valoración está fuera de la spec 022: ni `supervisor` ni `admin` la reciben; INV-3 no la recibe pedida."""
    seed_categories(world)
    for user in ("inventario.test", "supervisor.test", "admin.test"):
        body = summary(world, as_user(user))
        assert set(body) == {"company_id", "resolved_at", "adopted_products", "branches", "consolidated"}
        assert "inventory_value" not in keys_in(body) and "currency_code" not in keys_in(body)
    requested = [arguments for (name, arguments) in world.fakes.log.calls if name == "summary"]
    assert requested and all(len(arguments) == 2 for arguments in requested)  # (empresa, sucursales)
    assert world.fakes.log.count("company") == 0  # no se pide la moneda a Operational Context


def test_failure_of_cr_or_inventory_is_503(world, as_user) -> None:
    """FR-022-71: nunca indicadores parciales."""
    seed_categories(world)
    client = as_user("inventario.test")
    for fake, operation in ((world.fakes.cr, "count_adopted"), (world.fakes.inventory, "summary")):
        fake.fail = {operation}
        response = client.get(f"{world.base}/inventory-summary")
        assert response.status_code == 503 and "consolidated" not in response.json()
        fake.fail = set()


def test_missing_branch_in_inv3_is_503_not_zero(world, as_user) -> None:
    """Una sucursal pedida sin indicadores es una respuesta inválida de INV-3, no un cero."""
    seed_categories(world)
    original = world.fakes.inventory.summary

    async def partial(company_id, branch_ids):
        result = await original(company_id, branch_ids)
        return replace(result, branches=dict(list(result.branches.items())[:1]))

    world.fakes.inventory.summary = partial
    assert as_user("inventario.test").get(f"{world.base}/inventory-summary").status_code == 503


def test_summary_rejects_product_filters_and_cursor(world, as_user) -> None:
    """Contrato §4.4: solo `branch_id` o `scope`."""
    client = as_user("inventario.test")
    for query in ("search=arroz", "cursor=v1.a.b", "page_size=5", f"branch_id={world.branches[0]}&scope=COMPANY"):
        assert client.get(f"{world.base}/inventory-summary?{query}").status_code == 422, query
    assert world.fakes.log.total() == 0


def test_ventas_has_no_summary_permission(world, as_user) -> None:
    assert as_user("ventas.test").get(f"{world.base}/inventory-summary").status_code == 403


def test_other_company_is_404(world, as_user) -> None:
    response = as_user("inventario.test").get(f"/api/v1/companies/{world.other_company}/inventory-summary")
    assert response.status_code == 404
    assert world.fakes.log.count("summary") == world.fakes.log.count("count_adopted") == 0
