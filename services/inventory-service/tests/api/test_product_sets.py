"""INV-2: productos por estado de inventario, en modo conductor (spec 022, FR-022-86; T040)."""

from __future__ import annotations

from uuid import UUID, uuid4

from tests.conftest import BALANCES_READ, PLATFORM_LOOKUP, PRODUCT_POLICIES_READ
from tests.spec022_support import insert_balance, insert_policy


def url(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-product-sets"


def _post(client, world, **body):
    response = client.post(url(world), json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _walk(client, world, limit: int, **body) -> list:
    seen = []
    after = None
    for _ in range(100):
        page = _post(client, world, limit=limit, **({"after": after} if after else {}), **body)
        assert set(page) == {"items", "has_more"}
        seen.extend(page["items"])
        if not page["has_more"]:
            return seen
        after = page["items"][-1]["position"]
    raise AssertionError("no terminó")


def _ids(items) -> list[str]:
    return [item["company_product_id"] for item in items]


def _products(n: int) -> list[UUID]:
    return sorted(uuid4() for _ in range(n))


def test_in_stock_sums_requested_branches(as_user, world, test_engine) -> None:
    a, b, c, d = _products(4)
    insert_balance(test_engine, world.company, world.branch, a, "3")
    insert_balance(test_engine, world.company, world.branch, b, "0")
    insert_balance(test_engine, world.company, world.other_branch, b, "2")
    insert_balance(test_engine, world.company, world.branch, c, "0")
    insert_balance(test_engine, world.company, world.other_branch, d, "1")
    reader = as_user("inventario.test")
    both = [str(world.branch), str(world.other_branch)]

    assert _ids(_walk(reader, world, 10, branch_ids=both, stock_state="IN_STOCK")) == [str(a), str(b), str(d)]
    assert _ids(_walk(reader, world, 10, branch_ids=[str(world.branch)], stock_state="IN_STOCK")) == [str(a)]


def test_minimum_states_with_unregistered_balance_counting_as_zero(as_user, world, test_engine) -> None:
    below, at, above, unregistered, inactive_policy = _products(5)
    insert_balance(test_engine, world.company, world.branch, below, "3")
    insert_policy(test_engine, world.company, world.branch, below, "5")
    insert_balance(test_engine, world.company, world.branch, at, "5")
    insert_policy(test_engine, world.company, world.branch, at, "5")
    insert_balance(test_engine, world.company, world.branch, above, "9")
    insert_policy(test_engine, world.company, world.branch, above, "5")
    insert_policy(test_engine, world.company, world.branch, unregistered, "2")
    insert_policy(test_engine, world.company, world.branch, inactive_policy, "50", active=False)
    reader = as_user("inventario.test")
    scope = [str(world.branch)]

    def ids(state: str) -> set[str]:
        return set(_ids(_walk(reader, world, 10, branch_ids=scope, minimum_state=state)))

    assert ids("BELOW_MINIMUM") == {str(below), str(unregistered)}
    assert ids("AT_MINIMUM") == {str(at)}
    assert ids("ABOVE_MINIMUM") == {str(above)}
    assert ids("WITH_POLICY") == {str(below), str(at), str(above), str(unregistered)}
    combined = _walk(reader, world, 10, branch_ids=scope, stock_state="IN_STOCK", minimum_state="BELOW_MINIMUM")
    assert _ids(combined) == [str(below)]


def test_minimum_state_matches_if_any_branch_in_scope_has_it(as_user, world, test_engine) -> None:
    product = uuid4()
    insert_balance(test_engine, world.company, world.branch, product, "9")
    insert_policy(test_engine, world.company, world.branch, product, "5")
    insert_policy(test_engine, world.company, world.other_branch, product, "1")  # sin saldo: bajo mínimo
    reader = as_user("inventario.test")
    both = [str(world.branch), str(world.other_branch)]
    assert _ids(_walk(reader, world, 10, branch_ids=both, minimum_state="BELOW_MINIMUM")) == [str(product)]
    assert _ids(_walk(reader, world, 10, branch_ids=both, minimum_state="ABOVE_MINIMUM")) == [str(product)]


def test_products_keyset_walk_without_gaps_or_duplicates(as_user, world, test_engine) -> None:
    products = _products(7)
    for product in products:
        insert_balance(test_engine, world.company, world.branch, product, "1")
    reader = as_user("inventario.test")
    for limit in (1, 2, 3, 7):
        assert _ids(_walk(reader, world, limit, branch_ids=[str(world.branch)], stock_state="IN_STOCK")) == [
            str(p) for p in products
        ]


def test_pairs_ordered_by_shortfall_desc_with_ties(as_user, world, test_engine) -> None:
    a, b, c = _products(3)
    insert_balance(test_engine, world.company, world.branch, a, "1")
    insert_policy(test_engine, world.company, world.branch, a, "5")  # faltante 4
    insert_policy(test_engine, world.company, world.other_branch, a, "4")  # sin saldo: faltante 4
    insert_balance(test_engine, world.company, world.branch, b, "2")
    insert_policy(test_engine, world.company, world.branch, b, "10")  # faltante 8
    insert_balance(test_engine, world.company, world.branch, c, "4")
    insert_policy(test_engine, world.company, world.branch, c, "5")  # faltante 1
    reader = as_user("inventario.test")
    scope = [str(world.branch), str(world.other_branch)]
    branches = sorted([world.branch, world.other_branch])

    for limit in (1, 2, 4):
        pairs = _walk(reader, world, limit, branch_ids=scope, minimum_state="BELOW_MINIMUM", unit="PAIRS")
        assert [(p["company_product_id"], p["branch_id"], p["shortfall"]) for p in pairs] == [
            (str(b), str(world.branch), "8.0000"),
            (str(a), str(branches[0]), "4.0000"),
            (str(a), str(branches[1]), "4.0000"),
            (str(c), str(world.branch), "1.0000"),
        ]
    first = pairs[0]
    assert (first["base_quantity"], first["minimum_stock"]) == ("2.0000", "10.0000")


def test_never_returns_costs_or_totals(as_user, world, test_engine) -> None:
    product = uuid4()
    insert_balance(test_engine, world.company, world.branch, product, "5", inventory_value="5000", average_unit_cost="1000")
    insert_policy(test_engine, world.company, world.branch, product, "9")
    reader = as_user("inventario.test")
    for body in (
        {"branch_ids": [str(world.branch)], "stock_state": "IN_STOCK", "limit": 5},
        {"branch_ids": [str(world.branch)], "minimum_state": "BELOW_MINIMUM", "unit": "PAIRS", "limit": 5},
    ):
        text = str(_post(reader, world, **body))
        for forbidden in ("inventory_value", "average_unit_cost", "cost", "total"):
            assert forbidden not in text


def test_other_company_rows_are_never_returned(as_user, world, test_engine) -> None:
    insert_balance(test_engine, world.other_company, world.other_company_branch, world.other_company_product, "3")
    page = _post(as_user("inventario.test"), world, branch_ids=[str(world.other_company_branch)], stock_state="IN_STOCK", limit=5)
    assert page == {"items": [], "has_more": False}


def test_validation(as_user, world) -> None:
    reader = as_user("inventario.test")
    branch = [str(world.branch)]
    cases = [
        {"branch_ids": branch, "limit": 5},
        {"branch_ids": [], "stock_state": "IN_STOCK", "limit": 5},
        {"branch_ids": branch, "stock_state": "IN_STOCK", "limit": 0},
        {"branch_ids": branch, "stock_state": "IN_STOCK", "limit": 101},
        {"branch_ids": branch, "stock_state": "OUT_OF_STOCK", "limit": 5},
        {"branch_ids": branch, "minimum_state": "NO_POLICY", "limit": 5},
        {"branch_ids": branch, "stock_state": "IN_STOCK", "unit": "PAIRS", "limit": 5},
        {"branch_ids": branch, "minimum_state": "AT_MINIMUM", "unit": "PAIRS", "limit": 5},
        {"branch_ids": branch, "stock_state": "IN_STOCK", "limit": 5, "after": {"k": [], "id": "x"}},
        {"branch_ids": branch, "stock_state": "IN_STOCK", "limit": 5, "extra": 1},
    ]
    for body in cases:
        assert reader.post(url(world), json=body).status_code == 422, body


def test_permissions(as_user, as_token, service_token, world) -> None:
    body = {"branch_ids": [str(world.branch)], "stock_state": "IN_STOCK", "limit": 5}
    assert as_user("ventas.test").post(url(world), json=body).status_code == 403
    only_balances = as_token(service_token(BALANCES_READ, PLATFORM_LOOKUP, client_id="product-inventory-query-service"))
    assert only_balances.post(url(world), json=body).status_code == 403
    both = as_token(service_token(BALANCES_READ, PRODUCT_POLICIES_READ, PLATFORM_LOOKUP, client_id="product-inventory-query-service"))
    assert both.post(url(world), json=body).status_code == 200
