"""INV-1: políticas de producto por lotes (spec 022, FR-022-85; T039)."""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import BALANCES_READ, PLATFORM_LOOKUP, PRODUCT_POLICIES_READ
from tests.spec022_support import insert_policy


def url(world, branch=None) -> str:
    return f"/api/v1/companies/{world.company}/branches/{branch or world.branch}/inventory-policies/lookup"


def test_one_item_per_requested_product_with_active_policy_or_null(as_user, world, test_engine) -> None:
    p1, p2, p3 = world.products
    active = insert_policy(test_engine, world.company, world.branch, p1, "5")
    insert_policy(test_engine, world.company, world.branch, p2, "3", active=False)
    insert_policy(test_engine, world.company, world.other_branch, p3, "7")

    response = as_user("inventario.test").post(url(world), json={"company_product_ids": [str(p1), str(p2), str(p3), str(p1)]})

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["company_product_id"] for item in items] == [str(p1), str(p2), str(p3)]
    assert items[0]["policy"] == {"id": str(active), "minimum_stock": "5.0000", "status": "ACTIVE"}
    assert items[1]["policy"] is None  # inactiva
    assert items[2]["policy"] is None  # de otra sucursal


def test_other_company_data_is_never_returned(as_user, world, test_engine) -> None:
    """Las filas se filtran por la empresa de la ruta: una sucursal o un producto ajenos no aportan datos."""
    insert_policy(test_engine, world.other_company, world.other_company_branch, world.other_company_product, "9")
    response = as_user("inventario.test").post(
        url(world, world.other_company_branch), json={"company_product_ids": [str(world.other_company_product)]}
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["policy"] is None


def test_limits_permissions_and_technical_lookup(as_user, as_token, service_token, world) -> None:
    reader = as_user("inventario.test")
    assert reader.post(url(world), json={"company_product_ids": [str(uuid4()) for _ in range(101)]}).status_code == 422
    assert reader.post(url(world), json={"company_product_ids": []}).status_code == 422
    assert reader.post(url(world), json={"company_product_ids": [str(uuid4())], "x": 1}).status_code == 422
    assert as_user("ventas.test").post(url(world), json={"company_product_ids": [str(uuid4())]}).status_code == 403
    technical = as_token(service_token(PRODUCT_POLICIES_READ, PLATFORM_LOOKUP, client_id="product-inventory-query-service"))
    assert technical.post(url(world), json={"company_product_ids": [str(uuid4())]}).status_code == 200
    without_permission = as_token(service_token(BALANCES_READ, PLATFORM_LOOKUP, client_id="product-inventory-query-service"))
    assert without_permission.post(url(world), json={"company_product_ids": [str(uuid4())]}).status_code == 403
