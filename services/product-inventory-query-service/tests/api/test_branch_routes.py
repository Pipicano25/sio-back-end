"""Variantes por sucursal `/companies/{company_id}/branches/{branch_id}/…` (ampliación aditiva de la spec 022).

Las cuatro rutas reutilizan el mismo caso de uso que las rutas de la empresa con un único `branch_id`: misma
respuesta, filtros, permisos y paginación. Se prueba la equivalencia, que Inventory solo se consulta para la
sucursal de la ruta, la pertenencia de la sucursal a la empresa (`404`), el aislamiento entre sucursales y
empresas, el rechazo de `branch_id`/`scope` por consulta y los permisos por bloque.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.support import walk

ENDPOINTS = ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary")
LISTINGS = ENDPOINTS[:3]
INVENTORY_BY_BRANCH = {"balances": 1, "policies": 1}            # argumento (company, branch, ids)
INVENTORY_BY_BRANCHES = {"product_set": 1, "below_minimum_pairs": 1, "summary": 1}  # (company, [branches], …)
DEPENDENCIES = {"search_products", "search_products_evaluator", "presentations_by_products", "resolve_prices",
                "count_adopted", "summaries", "match_candidates", "match_page", "units", "presentations",
                "balances", "policies", "product_set", "below_minimum_pairs", "summary"}


def branch_url(world, endpoint: str, branch=None, company=None) -> str:
    return f"/api/v1/companies/{company or world.company}/branches/{branch or world.branches[0]}/{endpoint}"


def without_time(body: dict) -> dict:
    return {key: value for key, value in body.items() if key != "resolved_at"}


@pytest.fixture
def seeded(world):
    """Sucursal 0 y sucursal 1 con existencias y mínimos distintos (un producto bajo mínimo en cada una)."""
    only_0 = world.product("Solo en la sucursal 0")
    world.stock(only_0, "5", branch=0)
    only_1 = world.product("Solo en la sucursal 1")
    world.stock(only_1, "7", branch=1)
    low_0 = world.product("Bajo mínimo en la 0")
    world.stock(low_0, "1", branch=0)
    world.minimum(low_0, "4", branch=0)
    low_1 = world.product("Bajo mínimo en la 1")
    world.stock(low_1, "2", branch=1)
    world.minimum(low_1, "9", branch=1)
    both = world.product("En las dos")
    world.stock(both, "3", branch=0)
    world.stock(both, "8", branch=1)
    for index in range(25):  # más de una página
        world.stock(world.product(f"Relleno {index:02d}"), str(index + 1), branch=index % 2)
    return {"only_0": only_0, "only_1": only_1, "low_0": low_0, "low_1": low_1, "both": both}


def inventory_branches(world) -> set[str]:
    """Sucursales con que se consultó Inventory, a partir del registro de llamadas de los dobles."""
    branches: set[str] = set()
    for (operation, arguments), _ in world.fakes.log.calls.items():
        if operation in INVENTORY_BY_BRANCH:
            branches.add(str(arguments[INVENTORY_BY_BRANCH[operation]]))
        elif operation in INVENTORY_BY_BRANCHES:
            branches |= {str(branch) for branch in arguments[INVENTORY_BY_BRANCHES[operation]]}
    return branches


# --------------------------------------------------------------------------- equivalencia y alcance


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_same_response_as_the_company_route_with_one_branch_id(world, seeded, as_user, endpoint) -> None:
    client = as_user("supervisor.test")
    branch = world.branches[1]
    by_path = client.get(branch_url(world, endpoint, branch))
    by_query = client.get(f"{world.base}/{endpoint}?branch_id={branch}")
    assert by_path.status_code == by_query.status_code == 200, by_path.text
    assert without_time(by_path.json()) == without_time(by_query.json())


@pytest.mark.parametrize("endpoint", LISTINGS)
def test_walking_all_pages_matches_the_company_route(world, seeded, as_user, endpoint) -> None:
    client = as_user("supervisor.test")
    branch = world.branches[0]
    by_path, _ = walk(client, branch_url(world, endpoint, branch) + "?page_size=7")
    by_query, _ = walk(client, f"{world.base}/{endpoint}?branch_id={branch}&page_size=7")
    assert by_path == by_query
    keys = [item.get("company_product_id") for item in by_path]
    assert len(keys) == len(set(keys)) or endpoint == "low-stock-products"


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_inventory_is_queried_only_for_the_branch_in_the_path(world, seeded, as_user, endpoint) -> None:
    response = as_user("supervisor.test").get(branch_url(world, endpoint, world.branches[1]))
    assert response.status_code == 200, response.text
    assert inventory_branches(world) == {str(world.branches[1])}


def test_stock_and_minimums_are_only_from_the_branch(world, seeded, as_user) -> None:
    client = as_user("supervisor.test")
    body = client.get(branch_url(world, "inventory-overviews", world.branches[0]) + "?page_size=20").json()
    for item in body["items"]:
        assert {row["branch_id"] for row in item["stock"]["branches"]} == {str(world.branches[0])}
    both = next(item for item in walk(client, branch_url(world, "inventory-overviews", world.branches[0]))[0]
                if item["company_product_id"] == seeded["both"].id)
    assert both["stock"]["total_base_quantity"] == both["stock"]["branches"][0]["base_quantity"]
    assert float(both["stock"]["total_base_quantity"]) == 3


def test_low_stock_isolation_between_branches(world, seeded, as_user) -> None:
    client = as_user("inventario.test")
    zero = client.get(branch_url(world, "low-stock-products", world.branches[0])).json()["items"]
    one = client.get(branch_url(world, "low-stock-products", world.branches[1])).json()["items"]
    assert {pair["company_product_id"] for pair in zero} == {seeded["low_0"].id}
    assert {pair["company_product_id"] for pair in one} == {seeded["low_1"].id}
    assert {pair["branch_id"] for pair in zero} == {str(world.branches[0])}


def test_summary_of_one_branch(world, seeded, as_user) -> None:
    client = as_user("inventario.test")
    body = client.get(branch_url(world, "inventory-summary", world.branches[0])).json()
    assert [row["branch_id"] for row in body["branches"]] == [str(world.branches[0])]
    branch = {key: value for key, value in body["branches"][0].items() if key != "branch_id"}
    assert body["consolidated"] == branch
    company = client.get(f"{world.base}/inventory-summary").json()
    assert body["adopted_products"] == company["adopted_products"]  # adopción: siempre de la empresa (CR)
    assert body["consolidated"] != company["consolidated"]


def test_product_overviews_stock_only_for_the_branch(world, seeded, as_user) -> None:
    items, _ = walk(as_user("supervisor.test"), branch_url(world, "product-overviews", world.branches[1]))
    only_0 = next(item for item in items if item["company_product_id"] == seeded["only_0"].id)
    assert [row["branch_id"] for row in only_0["stock"]["branches"]] == [str(world.branches[1])]
    assert only_0["stock"]["branches"][0]["balance_state"] == "NOT_REGISTERED"  # su saldo es de la sucursal 0


# --------------------------------------------------------------------------- pertenencia y aislamiento


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_branch_of_another_company_is_404_before_any_dependency(world, as_user, endpoint) -> None:
    response = as_user("supervisor.test").get(branch_url(world, endpoint, world.other_branches[0]))
    assert response.status_code == 404
    assert "PRODUCT_INVENTORY_QUERY.NOT_FOUND" in response.text or response.json()["status"] == 404
    assert not any(world.fakes.log.count(name) for name in DEPENDENCIES)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_unknown_branch_and_foreign_company_are_404(world, as_user, endpoint) -> None:
    client = as_user("supervisor.test")
    assert client.get(branch_url(world, endpoint, uuid4())).status_code == 404
    foreign = branch_url(world, endpoint, world.other_branches[0], company=world.other_company)
    assert client.get(foreign).status_code == 404
    assert not any(world.fakes.log.count(name) for name in DEPENDENCIES)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_invalid_branch_id_in_path_is_422(world, as_user, endpoint) -> None:
    response = as_user("supervisor.test").get(f"{world.base}/branches/no-es-uuid/{endpoint}")
    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("query", ["branch_id={other}", "scope=COMPANY", "branch_id={same}"])
def test_branch_or_scope_in_the_query_is_rejected(world, as_user, endpoint, query) -> None:
    url = branch_url(world, endpoint) + "?" + query.format(other=world.branches[1], same=world.branches[0])
    response = as_user("supervisor.test").get(url)
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"
    assert not any(world.fakes.log.count(name) for name in DEPENDENCIES | {"operational_access"})


def test_a_cursor_from_another_branch_restarts_without_leaking(world, seeded, as_user) -> None:
    client = as_user("supervisor.test")
    first = client.get(branch_url(world, "inventory-overviews", world.branches[0]) + "?page_size=5").json()
    assert first["next_cursor"]
    moved = client.get(branch_url(world, "inventory-overviews", world.branches[1])
                       + f"?page_size=5&cursor={first['next_cursor']}").json()
    assert moved["pagination_reset"] is True and moved["pagination_reset_reason"] == "FILTERS_CHANGED"
    fresh = client.get(branch_url(world, "inventory-overviews", world.branches[1]) + "?page_size=5").json()
    assert moved["items"] == fresh["items"]


def test_a_cursor_from_another_company_is_rejected(world, as_user, fakes) -> None:
    other, other_branches = fakes.oc.add_company(branches=1)
    for index in range(8):
        item = world.product(f"Otra empresa {index}", company=other)
        fakes.inventory.set_balance(other, other_branches[0], item.product.id, "1")
    for index in range(8):
        world.stock(world.product(f"Propio {index}"), "1")
    client = as_user("supervisor.test")
    page = client.get(f"/api/v1/companies/{other}/branches/{other_branches[0]}/inventory-overviews?page_size=2")
    cursor = page.json()["next_cursor"]
    assert cursor
    response = client.get(branch_url(world, "inventory-overviews") + f"?page_size=2&cursor={cursor}")
    assert response.status_code == 422 and "INVALID_CURSOR" in response.text


# --------------------------------------------------------------------------- permisos


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_anonymous_is_401(world, as_token, endpoint) -> None:
    assert as_token(None).get(branch_url(world, endpoint)).status_code == 401


@pytest.mark.parametrize("user", ["compras.test", "reportes.test", "consulta.test"])
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_users_without_the_functional_permission_are_403(world, as_user, user, endpoint) -> None:
    response = as_user(user).get(branch_url(world, endpoint))
    assert response.status_code == 403 and "perm:" not in response.text


def test_ventas_sees_prices_and_stock_but_not_minimums_and_no_low_stock(world, seeded, as_user) -> None:
    client = as_user("ventas.test")
    body = client.get(branch_url(world, "inventory-overviews")).json()
    assert body["items"] and all("minimum_state" not in row for item in body["items"]
                                 for row in item["stock"]["branches"])
    assert client.get(branch_url(world, "low-stock-products")).status_code == 403
    assert client.get(branch_url(world, "inventory-summary")).status_code == 403
    assert client.get(branch_url(world, "inventory-overviews") + "?minimum_state=BELOW_MINIMUM").status_code == 403


def test_inventario_does_not_see_prices(world, seeded, as_user) -> None:
    items = as_user("inventario.test").get(branch_url(world, "product-overviews")).json()["items"]
    assert items and all("price" not in presentation for item in items for presentation in item["presentations"])


# --------------------------------------------------------------------------- costo comparativo (determinista)


def calls_of(world, client, url: str) -> tuple[int, int]:
    """(llamadas totales, llamadas a Inventory) de una solicitud, con el registro de los dobles reiniciado."""
    world.fakes.log.calls.clear()
    world.fakes.log.order.clear()
    response = client.get(url)
    assert response.status_code == 200, response.text
    inventory = sum(world.fakes.log.count(name) for name in {**INVENTORY_BY_BRANCH, **INVENTORY_BY_BRANCHES})
    return world.fakes.log.total(), inventory


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_branch_route_costs_the_same_as_one_branch_id_and_no_more_than_the_company(world, seeded, as_user,
                                                                                  endpoint) -> None:
    """Rendimiento comparativo sin tiempos: mismas llamadas que `?branch_id=` y nunca más que el consolidado."""
    client = as_user("supervisor.test")
    by_path = calls_of(world, client, branch_url(world, endpoint))
    by_query = calls_of(world, client, f"{world.base}/{endpoint}?branch_id={world.branches[0]}")
    consolidated = calls_of(world, client, f"{world.base}/{endpoint}")
    assert by_path == by_query
    assert by_path[0] <= consolidated[0] and by_path[1] <= consolidated[1]
