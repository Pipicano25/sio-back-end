"""`PUT` parcial y versión opcional en políticas (constitución 4.0.0: Principio VII, D9, D10 y D28)."""

from __future__ import annotations

import pytest

from tests.api.test_company_policy import BODY
from tests.api.test_company_policy import url as company_url
from tests.api.test_product_policies import body as product_body
from tests.api.test_product_policies import url as product_url


@pytest.fixture
def admin(as_user):
    return as_user("admin.sio")


@pytest.fixture
def product_policy(admin, world):
    response = admin.post(product_url(world), json=product_body(world))
    assert response.status_code == 201, response.text
    return response.json()


def test_product_policy_put_with_one_field_keeps_the_rest(admin, world, product_policy) -> None:
    response = admin.request("PUT", f"{product_url(world)}/{product_policy['id']}", json={"replenishment_mode": "AUTO_DRAFT"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["replenishment_mode"] == "AUTO_DRAFT"
    assert (data["minimum_stock"], data["target_stock"], data["service_level"]) == ("5.0000", "20.0000", "0.9500")
    assert data["version"] == product_policy["version"] + 1


def test_product_policy_ranges_are_checked_on_the_result(admin, world, product_policy) -> None:
    """Solo el mínimo enviado, mayor que el objetivo guardado (20) → `422 INVALID_LEVELS`."""
    response = admin.request("PUT", f"{product_url(world)}/{product_policy['id']}", json={"minimum_stock": "30"})

    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "INVALID_LEVELS"


def test_product_policy_null_clears_target_and_stale_version_is_409(admin, world, product_policy) -> None:
    cleared = admin.request("PUT", f"{product_url(world)}/{product_policy['id']}", json={"target_stock": None})
    stale = admin.request("PUT", 
        f"{product_url(world)}/{product_policy['id']}", json={"minimum_stock": "1", "version": product_policy["version"]}
    )

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["target_stock"] is None
    assert stale.status_code == 409


@pytest.mark.parametrize("payload", [{}, {"version": 1}, {"safety_stock_method": None}, {"desconocido": 1}])
def test_product_policy_body_without_valid_changes_is_422(admin, world, product_policy, payload) -> None:
    assert admin.request("PUT", f"{product_url(world)}/{product_policy['id']}", json=payload).status_code == 422


def test_product_policy_deactivate_without_body(admin, world, product_policy) -> None:
    response = admin.post(f"{product_url(world)}/{product_policy['id']}/deactivate")

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_company_policy_put_with_one_field_keeps_the_rest(admin, world) -> None:
    assert admin.post(company_url(world), json={**BODY, "inventory_system": "PERIODIC"}).status_code == 201

    response = admin.request("PUT", company_url(world), json={"replenishment_strategy": "JIT"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["inventory_system"], data["valuation_method"], data["replenishment_strategy"]) == (
        "PERIODIC",
        "FIFO",
        "JIT",
    )


def test_company_policy_put_keeps_fifo_rule(admin, world) -> None:
    assert admin.post(company_url(world), json=BODY).status_code == 201

    response = admin.request("PUT", company_url(world), json={"valuation_method": "LIFO"})

    assert response.status_code == 422
