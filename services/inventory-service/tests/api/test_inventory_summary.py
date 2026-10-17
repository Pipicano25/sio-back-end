"""INV-3: indicadores agregados dentro de Inventory (spec 022, FR-022-55, FR-022-88, D-022-9, D-022-11; T041).

Categorías de la spec: A saldo positivo, B saldo registrado en cero, C sin registro de saldo; D (inactivo) y E
(sin control de inventario) son estados comerciales que Inventory no conoce, así que sus saldos cuentan igual.
"""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import BALANCES_READ, PLATFORM_LOOKUP, PRODUCT_POLICIES_READ, VALUATION_READ
from tests.spec022_support import insert_balance, insert_policy

KEYS = {"products_with_positive_balance", "products_with_zero_balance", "products_with_policy", "products_below_minimum"}


def url(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-summary"


def _summary(client, world, branches, **extra):
    response = client.post(url(world), json={"branch_ids": [str(b) for b in branches], **extra})
    assert response.status_code == 200, response.text
    return response.json()


def _counts(block) -> dict:
    return {key: block[key] for key in KEYS}


def test_categories_per_branch(as_user, world, test_engine) -> None:
    positive, zero, never, inactive_in_cr, untracked_in_cr = (uuid4() for _ in range(5))
    insert_balance(test_engine, world.company, world.branch, positive, "4")
    insert_balance(test_engine, world.company, world.branch, zero, "0")
    # D y E: para Inventory son saldos como cualquier otro (no conoce el estado comercial).
    insert_balance(test_engine, world.company, world.branch, inactive_in_cr, "2")
    insert_balance(test_engine, world.company, world.branch, untracked_in_cr, "0")
    insert_policy(test_engine, world.company, world.branch, positive, "10")  # bajo mínimo
    insert_policy(test_engine, world.company, world.branch, never, "1")  # sin registro: cuenta con 0, bajo mínimo
    insert_policy(test_engine, world.company, world.branch, zero, "0")  # 0 < 0 es falso: no hay alerta
    insert_policy(test_engine, world.company, world.branch, inactive_in_cr, "50", active=False)

    body = _summary(as_user("inventario.test"), world, [world.branch])

    [branch] = body["branches"]
    assert branch["branch_id"] == str(world.branch)
    assert _counts(branch) == {
        "products_with_positive_balance": 2,  # positive e inactive_in_cr
        "products_with_zero_balance": 2,  # zero y untracked_in_cr; `never` no tiene registro y NO cuenta
        "products_with_policy": 3,  # la inactiva no cuenta
        "products_below_minimum": 2,  # positive (4 < 10) y never (0 < 1)
    }
    assert "inventory_value" not in branch
    assert "quantities_by_base_unit" not in str(body)
    assert "products_out_of_stock" not in str(body)


def test_consolidated_definitions(as_user, world, test_engine) -> None:
    split, empty_both, mixed_zero, policy_twice = (uuid4() for _ in range(4))
    insert_balance(test_engine, world.company, world.branch, split, "0")
    insert_balance(test_engine, world.company, world.other_branch, split, "3")  # suma > 0: positivo consolidado
    insert_balance(test_engine, world.company, world.branch, empty_both, "0")
    insert_balance(test_engine, world.company, world.other_branch, empty_both, "0")  # suma = 0 con registros
    insert_balance(test_engine, world.company, world.other_branch, mixed_zero, "0")
    insert_policy(test_engine, world.company, world.branch, policy_twice, "5")
    insert_policy(test_engine, world.company, world.other_branch, policy_twice, "5")  # dos pares bajo mínimo

    body = _summary(as_user("inventario.test"), world, [world.branch, world.other_branch])

    assert _counts(body["consolidated"]) == {
        "products_with_positive_balance": 1,
        "products_with_zero_balance": 2,  # empty_both y mixed_zero
        "products_with_policy": 1,
        "products_below_minimum": 1,  # un producto, aunque tenga dos pares
    }
    by_branch = {item["branch_id"]: _counts(item) for item in body["branches"]}
    assert by_branch[str(world.branch)]["products_below_minimum"] == 1
    assert by_branch[str(world.other_branch)]["products_with_positive_balance"] == 1


def test_branch_without_rows_reports_zeros(as_user, world) -> None:
    body = _summary(as_user("inventario.test"), world, [world.branch])
    assert _counts(body["branches"][0]) == dict.fromkeys(KEYS, 0)
    assert _counts(body["consolidated"]) == dict.fromkeys(KEYS, 0)


def test_valuation_only_when_requested_and_authorized(as_user, as_token, service_token, world, test_engine) -> None:
    product = uuid4()
    insert_balance(test_engine, world.company, world.branch, product, "5", inventory_value="5000.50", average_unit_cost="1000.1")
    insert_balance(test_engine, world.company, world.other_branch, product, "1", inventory_value="99.50")
    reader = as_user("inventario.test")

    without = _summary(reader, world, [world.branch])
    assert "inventory_value" not in str(without)

    valued = _summary(reader, world, [world.branch, world.other_branch], include_valuation=True)
    values = {item["branch_id"]: item["inventory_value"] for item in valued["branches"]}
    assert values == {str(world.branch): "5000.50", str(world.other_branch): "99.50"}
    assert valued["consolidated"]["inventory_value"] == "5100.00"
    for forbidden in ("average_unit_cost", "unit_cost", "fifo", "1000.1"):
        assert forbidden not in str(valued)

    no_valuation = as_token(service_token(BALANCES_READ, PRODUCT_POLICIES_READ, PLATFORM_LOOKUP, client_id="product-inventory-query-service"))
    response = no_valuation.post(url(world), json={"branch_ids": [str(world.branch)], "include_valuation": True})
    assert response.status_code == 403
    assert no_valuation.post(url(world), json={"branch_ids": [str(world.branch)]}).status_code == 200


def test_other_company_rows_are_never_counted(as_user, world, test_engine) -> None:
    insert_balance(test_engine, world.other_company, world.other_company_branch, world.other_company_product, "3")
    body = _summary(as_user("inventario.test"), world, [world.other_company_branch])
    assert _counts(body["consolidated"]) == dict.fromkeys(KEYS, 0)


def test_validation_and_permissions(as_user, as_token, service_token, world) -> None:
    reader = as_user("inventario.test")
    assert reader.post(url(world), json={"branch_ids": []}).status_code == 422
    assert reader.post(url(world), json={"branch_ids": [str(world.branch)], "x": 1}).status_code == 422
    assert reader.post(url(world), json={"branch_ids": [str(uuid4()) for _ in range(101)]}).status_code == 422
    assert as_user("ventas.test").post(url(world), json={"branch_ids": [str(world.branch)]}).status_code == 403
    technical = as_token(service_token(BALANCES_READ, PRODUCT_POLICIES_READ, VALUATION_READ, PLATFORM_LOOKUP,
                                       client_id="product-inventory-query-service"))
    assert technical.post(url(world), json={"branch_ids": [str(world.branch)], "include_valuation": True}).status_code == 200
