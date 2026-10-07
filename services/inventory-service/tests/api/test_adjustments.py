"""Ajustes manuales (Historia 1, escenarios 1–5 y 8; FR-030 a FR-035, FR-052, FR-063; DS-06; T034)."""

from __future__ import annotations

import json
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body, user_sub
from tests.contract.db_rows import insert_layer

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
STATE = (
    "inventory_operations",
    "inventory_movements",
    "inventory_balances",
    "inventory_cost_layers",
    "inventory_cost_consumptions",
    "inventory_adjustments",
    "audit_outbox",
)


def url(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-adjustments"


def adjustment(world, product, kind, quantity, *, unit_cost=None, reason="Producto dañado en bodega", **overrides):
    body = {
        "adjustment_key": str(uuid4()),
        "branch_id": str(world.branch),
        "company_product_id": str(product),
        "adjustment_type": kind,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "reason": reason,
    }
    body.update(overrides)
    return body


def snapshot(test_engine) -> dict:
    with test_engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all() for table in STATE}


@pytest.fixture
def stocked(operator, world):
    """Producto 0 con 10 a 1 000; producto 1 sin movimientos."""
    product = world.products[0]
    assert operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost="1000"))).status_code == 201
    return product


@pytest.fixture
def clerk(as_user):
    return as_user("inventario.test")


def test_negative_adjustment_consumes_fifo_and_is_recorded(clerk, world, fake_oc, stocked, test_engine) -> None:
    """Historia 1 escenario 1."""
    response = clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "3"))
    assert response.status_code == 201, response.text
    data = response.json()
    assert (data["adjustment_type"], data["quantity"], data["previous_balance"], data["new_balance"]) == (
        "NEGATIVE",
        "3.0000",
        "10.0000",
        "7.0000",
    )
    assert (data["unit_cost"], data["adjustment_value"]) == ("1000.0000", "3000.00")
    assert data["application_user_id"] == str(world.operator_user(fake_oc, "inventario.test"))
    assert data["created_by"] == user_sub("inventario.test")
    assert data["reason"] == "Producto dañado en bodega"
    assert data["inventory_count_id"] is None
    movement = data["movement"]
    assert (movement["movement_type"], movement["balance_sequence"], movement["movement_value"]) == (
        "NEGATIVE_ADJUSTMENT",
        2,
        "3000.00",
    )
    with test_engine.connect() as connection:
        operation = connection.execute(text("SELECT * FROM inventory_operations WHERE id = :id"), {"id": data["operation_id"]}).one()
        consumption = connection.execute(
            text("SELECT consumption_type, quantity FROM inventory_cost_consumptions WHERE movement_id = :m"),
            {"m": movement["id"]},
        ).one()
    assert (operation.operation_type, operation.origin_type, operation.requested_by_client) == (
        "ADJUSTMENT",
        "ADJUSTMENT",
        user_sub("inventario.test"),
    )
    assert tuple(consumption) == ("CONSUME", D("3"))


def test_positive_adjustment_uses_the_most_recent_layer_cost(clerk, operator, world, stocked, test_engine) -> None:
    """Historia 1 escenario 2 y FR-052: la capa más reciente, aunque esté cerrada."""
    assert operator.post(ENTRIES, json=operation_body(world, line(stocked, "2", unit_cost="1200"))).status_code == 201
    assert operator.post(OUTPUTS, json=operation_body(world, line(stocked, "12"), origin_type="SALE")).status_code == 201

    response = clerk.post(url(world), json=adjustment(world, stocked, "POSITIVE", "2", reason="Sobrante encontrado"))
    assert response.status_code == 201, response.text
    data = response.json()
    assert (data["unit_cost"], data["adjustment_value"], data["new_balance"]) == ("1200.0000", "2400.00", "2.0000")
    with test_engine.connect() as connection:
        kinds = connection.execute(
            text("SELECT layer_kind, unit_cost, currency_code FROM inventory_cost_layers WHERE status = 'OPEN'")
        ).all()
    assert [tuple(row) for row in kinds] == [("ADJUSTMENT", D("1200"), "COP")]


def test_positive_adjustment_with_informed_cost_uses_it(clerk, world, stocked) -> None:
    response = clerk.post(url(world), json=adjustment(world, stocked, "POSITIVE", "1", unit_cost="950.5"))
    assert response.status_code == 201
    assert response.json()["unit_cost"] == "950.5000"


def test_positive_adjustment_without_layers_requires_unit_cost(clerk, world, test_engine) -> None:
    product = world.products[1]
    before = snapshot(test_engine)
    response = clerk.post(url(world), json=adjustment(world, product, "POSITIVE", "4"))
    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [("unit_cost", "UNIT_COST_REQUIRED")]
    assert snapshot(test_engine) == before

    created = clerk.post(url(world), json=adjustment(world, product, "POSITIVE", "4", unit_cost="80"))
    assert created.status_code == 201
    assert created.json()["adjustment_value"] == "320.00"


def test_positive_adjustment_over_an_unknown_cost_opening_requires_unit_cost(clerk, world, test_engine) -> None:
    """FR-052 + FR-063: la capa más reciente es una apertura sin costo → `unit_cost` obligatorio."""
    product = world.products[2]
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                "inventory_value, average_unit_cost, has_unknown_cost, created_by, updated_by) "
                "VALUES (:c, :b, :p, 5, 0, 0, 0, true, 's', 's')"
            ),
            {"c": world.company, "b": world.branch, "p": product},
        )
        insert_layer(
            connection, company_id=world.company, branch_id=world.branch, company_product_id=product,
            original_quantity=5, remaining_quantity=5, unit_cost=0, cost_known=False, currency_code=None,
        )
    response = clerk.post(url(world), json=adjustment(world, product, "POSITIVE", "1"))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNIT_COST_REQUIRED"
    assert clerk.post(url(world), json=adjustment(world, product, "POSITIVE", "1", unit_cost="15")).status_code == 201


def test_negative_adjustment_rejects_unit_cost(clerk, world, stocked) -> None:
    response = clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "1", unit_cost="10"))
    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [("unit_cost", "UNIT_COST_NOT_ALLOWED")]


@pytest.mark.parametrize("reason", [None, "", "   ", "x" * 2001])
def test_reason_is_required(clerk, world, stocked, reason) -> None:
    """Historia 1 escenario 4."""
    response = clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "1", reason=reason))
    assert response.status_code == 422
    assert any(e["field"] == "reason" and e["code"] == "REASON_REQUIRED" for e in response.json()["errors"])


def test_negative_greater_than_balance_is_insufficient_stock(clerk, world, stocked, test_engine) -> None:
    """Historia 1 escenario 3."""
    before = snapshot(test_engine)
    response = clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "11"))
    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "INVENTORY.INSUFFICIENT_STOCK"
    assert data["shortages"] == [{"index": 0, "company_product_id": str(stocked), "available": "10.0000", "requested": "11.0000"}]
    assert snapshot(test_engine) == before


@pytest.mark.parametrize("case", ["inactive", "no_control", "other_company", "unknown"])
def test_invalid_products_are_rejected(clerk, world, fake_cr, test_engine, case) -> None:
    """Historia 1 escenario 5."""
    product = {
        "inactive": lambda: fake_cr.add_product(world.company, status="INACTIVE"),
        "no_control": lambda: fake_cr.add_product(world.company, inventory_control_enabled=False),
        "other_company": lambda: world.other_company_product,
        "unknown": uuid4,
    }[case]()
    expected = {
        "inactive": "COMPANY_PRODUCT_INACTIVE",
        "no_control": "INVENTORY_CONTROL_DISABLED",
        "other_company": "COMPANY_PRODUCT_NOT_FOUND",
        "unknown": "COMPANY_PRODUCT_NOT_FOUND",
    }[case]
    response = clerk.post(url(world), json=adjustment(world, product, "POSITIVE", "1", unit_cost="5"))
    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [("company_product_id", expected)]
    assert count_rows(test_engine, "inventory_adjustments") == 0


def test_operator_cannot_be_chosen_in_the_body(clerk, world, stocked) -> None:
    body = adjustment(world, stocked, "NEGATIVE", "1", application_user_id=str(world.user))
    response = clerk.post(url(world), json=body)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"


def test_idempotency_by_adjustment_key(clerk, as_user, world, fake_oc, fake_cr, stocked, test_engine) -> None:
    """Historia 1 escenario 8."""
    body = adjustment(world, stocked, "NEGATIVE", "2")
    first = clerk.post(url(world), json=body)
    assert first.status_code == 201

    fake_oc.fail_if_called = True
    fake_cr.fail_if_called = True
    again = clerk.post(url(world), json=body)
    assert again.status_code == 200
    assert again.json() == first.json()
    assert count_rows(test_engine, "inventory_adjustments") == 1

    changed = clerk.post(url(world), json={**body, "quantity": "3"})
    assert changed.status_code == 409
    assert changed.json()["code"] == "INVENTORY.OPERATION_KEY_CONFLICT"

    # La clave queda ligada al usuario (`sub`): otro usuario autorizado con la misma solicitud → 409.
    fake_oc.fail_if_called = False
    fake_cr.fail_if_called = False
    other_user = as_user("supervisor.test").post(url(world), json=body)
    assert other_user.status_code == 409
    assert count_rows(test_engine, "inventory_adjustments") == 1


def test_one_audit_event_per_applied_adjustment(clerk, world, fake_oc, stocked, test_engine) -> None:
    """FR-070: un evento `CREATE_INVENTORY_ADJUSTMENT` por ajuste; ninguno en los rechazos."""
    before = count_rows(test_engine, "audit_outbox")
    response = clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "1"))
    clerk.post(url(world), json=adjustment(world, stocked, "NEGATIVE", "100"))  # rechazado
    with test_engine.connect() as connection:
        rows = connection.execute(text("SELECT payload FROM audit_outbox ORDER BY created_at")).all()
    payloads = [row.payload if isinstance(row.payload, dict) else json.loads(row.payload) for row in rows][before:]
    assert [event["action"] for event in payloads] == ["CREATE_INVENTORY_ADJUSTMENT"]
    event = payloads[0]
    assert (event["entity_type"], event["entity_id"]) == ("InventoryAdjustment", response.json()["id"])
    assert (event["company_id"], event["branch_id"]) == (str(world.company), str(world.branch))
    assert event["application_user_id"] == str(world.operator_user(fake_oc, "inventario.test"))
    assert event["reason"] == "Producto dañado en bodega"
    values = event["new_values"]
    assert (values["adjustment_type"], values["quantity"], values["unit_cost"], values["adjustment_value"]) == (
        "NEGATIVE",
        "1.0000",
        "1000.0000",
        "1000.00",
    )
