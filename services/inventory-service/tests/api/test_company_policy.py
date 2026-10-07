"""Política de inventario de la empresa (Historia 4, escenarios 1–4; FR-010 a FR-012; DS-01, DS-02; C-07; RC-16, RC-17; T046)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from tests.conftest import COMPANY_POLICIES_READ, PLATFORM_LOOKUP, line, operation_body


def url(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-policy"


BODY = {"inventory_system": "PERPETUAL", "valuation_method": "FIFO", "replenishment_strategy": "STANDARD"}


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def events(test_engine) -> list[dict]:
    with test_engine.connect() as connection:
        rows = connection.execute(text("SELECT payload FROM audit_outbox ORDER BY created_at")).all()
    return [row.payload if isinstance(row.payload, dict) else json.loads(row.payload) for row in rows]


def test_default_policy_when_none_is_registered(admin, world) -> None:
    """Historia 4 escenario 2 (DS-01)."""
    response = admin.get(url(world))
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "id": None,
        "company_id": str(world.company),
        "inventory_system": "PERPETUAL",
        "valuation_method": "FIFO",
        "replenishment_strategy": "STANDARD",
        "is_active": True,
        "version": None,
        "registered": False,
        "created_at": None,
        "created_by": None,
        "updated_at": None,
        "updated_by": None,
    }


def test_create_once_and_update_with_version(admin, world, test_engine) -> None:
    """Historia 4 escenarios 1 y 4."""
    created = admin.post(url(world), json={**BODY, "inventory_system": "PERIODIC"})
    assert created.status_code == 201, created.text
    data = created.json()
    assert (data["registered"], data["version"], data["inventory_system"], data["is_active"]) == (True, 1, "PERIODIC", True)

    again = admin.post(url(world), json=BODY)
    assert (again.status_code, again.json()["code"]) == (409, "INVENTORY.POLICY_ALREADY_EXISTS")

    updated = admin.request("PUT", url(world), json={**BODY, "replenishment_strategy": "JIT", "version": 1})
    assert updated.status_code == 200, updated.text
    assert (updated.json()["replenishment_strategy"], updated.json()["version"]) == ("JIT", 2)

    stale = admin.request("PUT", url(world), json={**BODY, "version": 1})
    assert (stale.status_code, stale.json()["code"]) == (409, "INVENTORY.VERSION_CONFLICT")
    assert admin.get(url(world)).json()["replenishment_strategy"] == "JIT"

    actions = [event["action"] for event in events(test_engine)]
    assert actions.count("SET_COMPANY_INVENTORY_POLICY") == 2
    update_event = [event for event in events(test_engine) if event["action"] == "SET_COMPANY_INVENTORY_POLICY"][1]
    assert update_event["entity_type"] == "CompanyInventoryPolicy"
    assert update_event["previous_values"]["replenishment_strategy"] == "STANDARD"
    assert update_event["new_values"]["replenishment_strategy"] == "JIT"


def test_update_without_a_registered_policy_is_not_found(admin, world) -> None:
    assert admin.request("PUT", url(world), json={**BODY, "version": 1}).status_code == 404


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_only_fifo_is_accepted(admin, world, method) -> None:
    """Historia 4 escenario 3 (DS-11, RC-16)."""
    if method == "PUT":
        admin.post(url(world), json=BODY)
    body = {**BODY, "valuation_method": "WEIGHTED_AVERAGE", **({"version": 1} if method == "PUT" else {})}
    response = admin.request(method, url(world), json=body)
    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [("valuation_method", "VALUATION_METHOD_NOT_SUPPORTED")]


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_is_active_cannot_be_set(admin, world, method) -> None:
    """C-07: `is_active` es solo lectura; no hay ninguna ruta que simule desactivar la política."""
    if method == "PUT":
        admin.post(url(world), json=BODY)
    body = {**BODY, "is_active": False, **({"version": 1} if method == "PUT" else {})}
    response = admin.request(method, url(world), json=body)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"
    for path in (f"{url(world)}/deactivate", f"{url(world)}/activate"):
        assert admin.post(path, json={}).status_code in (404, 405)
    assert admin.request("DELETE", url(world)).status_code == 405


def test_periodic_does_not_change_the_engine(admin, operator, world) -> None:
    """DS-02: `PERIODIC` se guarda; las salidas siguen descontando en el acto."""
    admin.post(url(world), json={**BODY, "inventory_system": "PERIODIC"})
    product = world.products[0]
    operator.post("/api/v1/inventory-entries", json=operation_body(world, line(product, "5", unit_cost="1")))
    sale = operator.post("/api/v1/inventory-outputs", json=operation_body(world, line(product, "2"), origin_type="SALE"))
    assert sale.json()["balances"][0]["quantity"] == "3.0000"


def test_permissions(as_user, as_token, service_token, world, fake_oc) -> None:
    for username in ("inventario.test", "compras.test", "consulta.test"):
        assert as_user(username).post(url(world), json=BODY).status_code == 403, username
    assert as_user("supervisor.test").post(url(world), json=BODY).status_code == 201

    service = as_token(service_token("perm:all:all:all"))
    assert service.request("PUT", url(world), json={**BODY, "version": 1}).status_code == 403

    assert as_user("inventario.test").get(url(world)).status_code == 200
    assert as_user("compras.test").get(url(world)).status_code == 403
    fake_oc.fail_if_called = True
    assert as_token(service_token(COMPANY_POLICIES_READ, PLATFORM_LOOKUP)).get(url(world)).status_code == 200


def test_writes_require_membership(as_user, world, fake_oc) -> None:
    other = f"/api/v1/companies/{world.other_company}/inventory-policy"
    assert as_user("admin.test").post(other, json=BODY).status_code == 404
