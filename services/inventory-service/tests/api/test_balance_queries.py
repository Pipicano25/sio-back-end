"""Saldo, stock de sucursal y saldos por lote (Historia 5; FR-040, FR-041; T046)."""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def base(world, branch=None) -> str:
    return f"/api/v1/companies/{world.company}/branches/{branch or world.branch}"


def test_balance_of_a_product(operator, as_user, world) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "10")))
    operator.post(OUTPUTS, json=operation_body(world, line(product, "2.5"), origin_type="SALE"))

    response = as_user("inventario.test").get(f"{base(world)}/balances/{product}")

    assert response.status_code == 200
    data = response.json()
    assert (data["quantity"], data["balance_sequence"]) == ("7.5000", 2)
    assert data["last_movement_at"] is not None
    assert (data["company_id"], data["branch_id"], data["company_product_id"]) == (
        str(world.company), str(world.branch), str(product)
    )


def test_product_without_movements_has_zero(as_user, world) -> None:
    response = as_user("inventario.test").get(f"{base(world)}/balances/{world.products[2]}")
    assert response.status_code == 200
    assert (response.json()["quantity"], response.json()["last_movement_at"], response.json()["balance_sequence"]) == (
        "0.0000", None, 0
    )


def test_branch_stock_paginated_and_filtered(operator, as_user, world) -> None:
    p1, p2, p3 = world.products
    operator.post(ENTRIES, json=operation_body(world, line(p1, "1"), line(p2, "2"), line(p3, "3")))
    operator.post(OUTPUTS, json=operation_body(world, line(p2, "2"), origin_type="SALE"))
    reader = as_user("inventario.test")

    full = reader.get(f"{base(world)}/balances").json()
    assert (full["page"], full["page_size"], full["total_records"], full["total_pages"]) == (1, 20, 3, 1)
    assert [item["company_product_id"] for item in full["items"]] == sorted(str(p) for p in (p1, p2, p3))

    in_stock = reader.get(f"{base(world)}/balances", params={"in_stock_only": "true"}).json()
    assert {item["company_product_id"] for item in in_stock["items"]} == {str(p1), str(p3)}

    one = reader.get(f"{base(world)}/balances", params={"company_product_id": str(p3)}).json()
    assert [item["quantity"] for item in one["items"]] == ["3.0000"]

    page = reader.get(f"{base(world)}/balances", params={"page": 2, "page_size": 2}).json()
    assert (len(page["items"]), page["total_pages"]) == (1, 2)


def test_page_size_and_unknown_parameters(as_user, world) -> None:
    reader = as_user("inventario.test")
    too_big = reader.get(f"{base(world)}/balances", params={"page_size": 101})
    assert too_big.status_code == 422
    assert too_big.json()["errors"][0]["code"] == "PAGE_SIZE_OUT_OF_RANGE"
    assert reader.get(f"{base(world)}/balances", params={"desconocido": 1}).status_code == 422


def test_lookup_by_batch(operator, as_user, world) -> None:
    p1, p2, p3 = world.products
    operator.post(ENTRIES, json=operation_body(world, line(p1, "4"), line(p3, "1")))
    response = as_user("inventario.test").post(
        f"{base(world)}/balances/lookup", json={"company_product_ids": [str(p3), str(p2), str(p1), str(p3)]}
    )
    assert response.status_code == 200
    assert [(item["company_product_id"], item["quantity"]) for item in response.json()["items"]] == [
        (str(p3), "1.0000"), (str(p2), "0.0000"), (str(p1), "4.0000")
    ]


def test_lookup_limits(as_user, world) -> None:
    reader = as_user("inventario.test")
    assert reader.post(f"{base(world)}/balances/lookup", json={"company_product_ids": []}).status_code == 422
    too_many = [str(uuid4()) for _ in range(101)]
    assert reader.post(f"{base(world)}/balances/lookup", json={"company_product_ids": too_many}).status_code == 422


def test_branch_of_another_company_reveals_nothing(operator, as_user, world) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "9")))
    reader = as_user("inventario.test")
    assert reader.get(f"{base(world, world.other_company_branch)}/balances/{product}").json()["quantity"] == "0.0000"
    assert reader.get(f"{base(world, world.other_company_branch)}/balances").json()["items"] == []
