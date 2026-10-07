"""Políticas de reposición por producto y sucursal (Historia 5, escenarios 1–5; FR-020 a FR-022; DS-03; RC-17; T048)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


def url(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-policies"


def body(world, product=None, **overrides):
    data = {
        "branch_id": str(world.branch),
        "company_product_id": str(product or world.products[0]),
        "minimum_stock": "5",
        "target_stock": "20",
        "service_level": "0.95",
        "safety_stock_method": "BASIC",
        "calculation_window_days": 90,
        "replenishment_mode": "MANUAL",
        "auto_purchase_enabled": False,
    }
    data.update(overrides)
    return data


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def actions(test_engine) -> list[str]:
    with test_engine.connect() as connection:
        rows = connection.execute(text("SELECT payload FROM audit_outbox ORDER BY created_at")).all()
    return [(row.payload if isinstance(row.payload, dict) else json.loads(row.payload))["action"] for row in rows]


def test_create_update_deactivate_and_recreate(admin, world, test_engine) -> None:
    """Historia 5 escenarios 1, 2 y 4."""
    created = admin.post(url(world), json=body(world))
    assert created.status_code == 201, created.text
    data = created.json()
    assert (data["minimum_stock"], data["target_stock"], data["service_level"], data["version"], data["is_active"]) == (
        "5.0000",
        "20.0000",
        "0.9500",
        1,
        True,
    )

    duplicate = admin.post(url(world), json=body(world))
    assert (duplicate.status_code, duplicate.json()["code"]) == (409, "INVENTORY.ACTIVE_POLICY_EXISTS")

    update = {key: value for key, value in body(world, minimum_stock="7").items() if key not in ("branch_id", "company_product_id")}
    updated = admin.request("PUT", f"{url(world)}/{data['id']}", json={**update, "version": 1})
    assert updated.status_code == 200, updated.text
    assert (updated.json()["minimum_stock"], updated.json()["version"]) == ("7.0000", 2)
    stale = admin.request("PUT", f"{url(world)}/{data['id']}", json={**update, "version": 1})
    assert (stale.status_code, stale.json()["code"]) == (409, "INVENTORY.VERSION_CONFLICT")

    deactivated = admin.post(f"{url(world)}/{data['id']}/deactivate", json={"version": 2})
    assert deactivated.status_code == 200
    assert (deactivated.json()["is_active"], deactivated.json()["version"]) == (False, 3)
    assert admin.post(url(world), json=body(world)).status_code == 201

    assert actions(test_engine) == [
        "CREATE_INVENTORY_POLICY",
        "UPDATE_INVENTORY_POLICY",
        "DEACTIVATE_INVENTORY_POLICY",
        "CREATE_INVENTORY_POLICY",
    ]


@pytest.mark.parametrize(
    ("overrides", "field", "code"),
    [
        ({"minimum_stock": "-1"}, "minimum_stock", "INVALID_LEVELS"),
        ({"minimum_stock": "10", "target_stock": "5"}, "target_stock", "INVALID_LEVELS"),
        ({"service_level": "1"}, "service_level", "INVALID_SERVICE_LEVEL"),
        ({"service_level": "0"}, "service_level", "INVALID_SERVICE_LEVEL"),
        ({"calculation_window_days": 0}, "calculation_window_days", "INVALID_WINDOW"),
        ({"calculation_window_days": 3651}, "calculation_window_days", "INVALID_WINDOW"),
    ],
)
def test_invalid_levels(admin, world, overrides, field, code) -> None:
    """Historia 5 escenario 3."""
    response = admin.post(url(world), json=body(world, **overrides))
    assert response.status_code == 422
    assert (field, code) in [(e["field"], e["code"]) for e in response.json()["errors"]]


def test_auto_draft_is_only_configuration(admin, world, test_engine) -> None:
    """Historia 5 escenario 5 (DS-03): no genera compras ni movimientos."""
    response = admin.post(url(world), json=body(world, replenishment_mode="AUTO_DRAFT", auto_purchase_enabled=True))
    assert response.status_code == 201
    assert (response.json()["replenishment_mode"], response.json()["auto_purchase_enabled"]) == ("AUTO_DRAFT", True)
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM inventory_operations")).scalar_one() == 0


def test_branch_and_product_are_validated(admin, world, fake_oc, fake_cr) -> None:
    inactive_branch = fake_oc.add_branch(world.company, status="INACTIVE")
    cases = [
        (body(world, branch_id=str(world.other_company_branch)), "branch_id", "BRANCH_NOT_IN_COMPANY"),
        (body(world, branch_id=str(inactive_branch)), "branch_id", "BRANCH_INACTIVE"),
        (body(world, branch_id=str(uuid4())), "branch_id", "BRANCH_NOT_FOUND"),
        (body(world, product=world.other_company_product), "company_product_id", "COMPANY_PRODUCT_NOT_FOUND"),
        (body(world, product=fake_cr.add_product(world.company, inventory_control_enabled=False)), "company_product_id", "INVENTORY_CONTROL_DISABLED"),
    ]
    for data, field, code in cases:
        response = admin.post(url(world), json=data)
        assert response.status_code == 422, (field, code)
        assert (field, code) in [(e["field"], e["code"]) for e in response.json()["errors"]]


def test_list_filters_and_get(admin, world) -> None:
    first = admin.post(url(world), json=body(world)).json()
    admin.post(url(world), json=body(world, product=world.products[1]))
    admin.post(f"{url(world)}/{first['id']}/deactivate", json={"version": 1})

    page = admin.get(url(world), params={"branch_id": str(world.branch), "is_active": "true"}).json()
    assert [item["company_product_id"] for item in page["items"]] == [str(world.products[1])]
    by_product = admin.get(url(world), params={"company_product_id": str(world.products[0])}).json()
    assert [item["id"] for item in by_product["items"]] == [first["id"]]
    assert admin.get(f"{url(world)}/{first['id']}").json()["is_active"] is False
    assert admin.get(f"{url(world)}/{uuid4()}").status_code == 404
    other = f"/api/v1/companies/{world.other_company}/inventory-policies/{first['id']}"
    assert admin.get(other).status_code == 404


def test_permissions(as_user, as_token, service_token, world) -> None:
    for username in ("inventario.test", "compras.test"):
        assert as_user(username).post(url(world), json=body(world)).status_code == 403
    assert as_token(service_token("perm:all:all:all")).post(url(world), json=body(world)).status_code == 403
    assert as_user("inventario.test").get(url(world)).status_code == 200
    assert as_user("consulta.test").get(url(world)).status_code == 403


def test_simultaneous_creations_keep_one_active_policy(app, user_token, world) -> None:
    def send(_):
        client = TestClient(app, raise_server_exceptions=False)
        return client.post(url(world), json=body(world), headers={"Authorization": f"Bearer {user_token('admin.test')}"}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(send, range(8)))
    assert statuses.count(201) == 1
    assert statuses.count(409) == 7
