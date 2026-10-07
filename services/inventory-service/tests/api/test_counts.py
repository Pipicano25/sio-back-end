"""Conteos físicos (Historia 2, escenarios 1–8; FR-040 a FR-045; DS-07 a DS-09; RC-13; R-10, R-11; T040)."""

from __future__ import annotations

import json
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body, user_sub

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
STATE = (
    "inventory_operations",
    "inventory_movements",
    "inventory_balances",
    "inventory_cost_layers",
    "inventory_cost_consumptions",
    "inventory_adjustments",
)


def base(world) -> str:
    return f"/api/v1/companies/{world.company}/inventory-counts"


def snapshot(test_engine) -> dict:
    with test_engine.connect() as connection:
        return {table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all() for table in STATE}


def events(test_engine) -> list[dict]:
    with test_engine.connect() as connection:
        rows = connection.execute(text("SELECT payload FROM audit_outbox ORDER BY created_at")).all()
    return [row.payload if isinstance(row.payload, dict) else json.loads(row.payload) for row in rows]


@pytest.fixture
def clerk(as_user):
    return as_user("inventario.test")


@pytest.fixture
def stocked(operator, world):
    """A = 10 a 100, B = 4 a 50, C = 6 a 20."""
    a, b, c = world.products
    body = operation_body(world, line(a, "10", unit_cost="100"), line(b, "4", unit_cost="50"), line(c, "6", unit_cost="20"))
    assert operator.post(ENTRIES, json=body).status_code == 201
    return a, b, c


def create(clerk, world, **extra):
    response = clerk.post(base(world), json={"branch_id": str(world.branch), "observations": "Conteo ficticio", **extra})
    assert response.status_code == 201, response.text
    return response.json()


def start(clerk, world, count):
    response = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": count["version"]})
    assert response.status_code == 200, response.text
    return response.json()


def register(clerk, world, count, product, counted, unit_cost=None):
    body = {"counted_quantity": counted}
    if unit_cost is not None:
        body["unit_cost"] = unit_cost
    return clerk.request("PUT", f"{base(world)}/{count['id']}/details/{product}", json=body)


def complete(clerk, world, count, key=None):
    return clerk.post(
        f"{base(world)}/{count['id']}/complete", json={"completion_key": str(key or uuid4()), "version": count["version"]}
    )


def test_lifecycle_and_completion_apply_one_operation(clerk, world, fake_oc, stocked, test_engine) -> None:
    """Historia 2 escenarios 1, 2 y 4."""
    a, b, c = stocked
    count = create(clerk, world)
    operator_user = str(world.operator_user(fake_oc, "inventario.test"))
    assert (count["status"], count["version"], count["started_by_user_id"]) == ("DRAFT", 1, operator_user)
    assert count["created_by"] == user_sub("inventario.test")

    count = start(clerk, world, count)
    assert (count["status"], count["version"]) == ("IN_PROGRESS", 2)
    assert count["started_at"] is not None

    detail = register(clerk, world, count, a, "8")
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert (data["system_quantity_snapshot"], data["counted_quantity"], data["difference_quantity"]) == ("10.0000", "8.0000", "-2.0000")
    assert data["counted_by_user_id"] == operator_user and data["counted_at"]
    assert register(clerk, world, count, b, "5").status_code == 200
    assert register(clerk, world, count, c, "6").status_code == 200

    response = complete(clerk, world, count)
    assert response.status_code == 200, response.text
    done = response.json()
    assert (done["status"], done["version"], done["completed_by_user_id"]) == ("COMPLETED", 3, operator_user)
    assert done["operation_id"] is not None and done["completed_at"] is not None
    adjustments = {item["company_product_id"]: item for item in done["adjustments"]}
    assert set(adjustments) == {str(a), str(b)}  # C sin diferencia: sin ajuste
    assert (adjustments[str(a)]["adjustment_type"], adjustments[str(a)]["quantity"], adjustments[str(a)]["unit_cost"]) == (
        "NEGATIVE",
        "2.0000",
        "100.0000",
    )
    assert (adjustments[str(b)]["adjustment_type"], adjustments[str(b)]["quantity"], adjustments[str(b)]["unit_cost"]) == (
        "POSITIVE",
        "1.0000",
        "50.0000",
    )
    assert all(item["inventory_count_id"] == count["id"] for item in done["adjustments"])
    details = {item["company_product_id"]: item for item in done["details"]}
    assert details[str(a)]["inventory_adjustment_id"] == adjustments[str(a)]["id"]
    assert details[str(c)]["inventory_adjustment_id"] is None

    with test_engine.connect() as connection:
        operation = connection.execute(text("SELECT * FROM inventory_operations WHERE id = :id"), {"id": done["operation_id"]}).one()
        balances = dict(connection.execute(text("SELECT company_product_id, quantity FROM inventory_balances")).all())
    assert (operation.operation_type, operation.origin_type, operation.origin_id, operation.line_count) == (
        "ADJUSTMENT",
        "COUNT",
        UUID(count["id"]),
        2,
    )
    assert balances == {a: D("8"), b: D("5"), c: D("6")}


def test_registering_a_product_again_replaces_the_detail(clerk, world, stocked) -> None:
    """Historia 2 escenario 3."""
    a = stocked[0]
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, a, "8")
    data = register(clerk, world, count, a, "9").json()
    assert (data["counted_quantity"], data["difference_quantity"]) == ("9.0000", "-1.0000")
    detail = clerk.get(f"{base(world)}/{count['id']}").json()["details"]
    assert len(detail) == 1


def test_completion_applies_the_recorded_difference_on_the_current_balance(clerk, operator, world, stocked) -> None:
    """Historia 2 escenario 5 (DS-09): una venta entre el registro y la finalización."""
    a = stocked[0]
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, a, "8")  # diferencia −2 sobre 10
    assert operator.post(OUTPUTS, json=operation_body(world, line(a, "3"), origin_type="SALE")).status_code == 201
    done = complete(clerk, world, count).json()
    adjustment = done["adjustments"][0]
    assert (adjustment["previous_balance"], adjustment["new_balance"]) == ("7.0000", "5.0000")


def test_completion_that_would_overdraw_applies_nothing(clerk, operator, world, stocked, test_engine) -> None:
    """Historia 2 escenario 6 y RC-13: todo o nada; el conteo sigue `IN_PROGRESS`."""
    a, b, _ = stocked
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, b, "6")  # +2
    register(clerk, world, count, a, "1")  # −9
    assert operator.post(OUTPUTS, json=operation_body(world, line(a, "5"), origin_type="SALE")).status_code == 201
    before = snapshot(test_engine)
    response = complete(clerk, world, count)
    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "INVENTORY.INSUFFICIENT_STOCK"
    assert [(item["company_product_id"], item["available"], item["requested"]) for item in data["shortages"]] == [
        (str(a), "5.0000", "9.0000")
    ]
    assert snapshot(test_engine) == before
    assert clerk.get(f"{base(world)}/{count['id']}").json()["status"] == "IN_PROGRESS"


@pytest.fixture
def fresh_product(fake_cr, world):
    return fake_cr.add_product(world.company)


def test_surplus_of_a_product_without_layers_requires_unit_cost(clerk, world, fresh_product, test_engine) -> None:
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, fresh_product, "3")
    before = snapshot(test_engine)
    response = complete(clerk, world, count)
    assert response.status_code == 422
    assert [(e["field"], e["code"]) for e in response.json()["errors"]] == [
        (f"details[{fresh_product}].unit_cost", "UNIT_COST_REQUIRED")
    ]
    assert snapshot(test_engine) == before

    register(clerk, world, count, fresh_product, "3", unit_cost="12")
    done = complete(clerk, world, count).json()
    assert done["status"] == "COMPLETED"
    assert done["adjustments"][0]["unit_cost"] == "12.0000"


def test_count_without_details(clerk, world, stocked) -> None:
    count = start(clerk, world, create(clerk, world))
    response = complete(clerk, world, count)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "COUNT_WITHOUT_DETAILS"


def test_details_limit(clerk, world, fake_cr, test_engine) -> None:
    count = start(clerk, world, create(clerk, world))
    with test_engine.begin() as connection:
        for _ in range(1000):
            connection.execute(
                text(
                    "INSERT INTO inventory_count_details (inventory_count_id, company_product_id, system_quantity_snapshot, "
                    "counted_quantity, difference_quantity, counted_by_user_id, counted_at, created_by, updated_by) "
                    "VALUES (:c, gen_random_uuid(), 0, 0, 0, gen_random_uuid(), now(), 's', 's')"
                ),
                {"c": count["id"]},
            )
    response = register(clerk, world, count, fake_cr.add_product(world.company), "1")
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "COUNT_DETAILS_LIMIT"


def test_zero_difference_count_completes_without_adjustments(clerk, world, stocked) -> None:
    c = stocked[2]
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, c, "6")
    done = complete(clerk, world, count).json()
    assert (done["status"], done["operation_id"], done["adjustments"]) == ("COMPLETED", None, [])


def test_cancel(clerk, world, stocked, test_engine) -> None:
    """Historia 2 escenario 7."""
    count = create(clerk, world)
    missing = clerk.post(f"{base(world)}/{count['id']}/cancel", json={"version": 1})
    assert missing.status_code == 422
    assert any(e["code"] == "REASON_REQUIRED" for e in missing.json()["errors"])

    started = start(clerk, world, count)
    register(clerk, world, started, stocked[0], "3")
    cancelled = clerk.post(f"{base(world)}/{count['id']}/cancel", json={"reason": "Conteo duplicado", "version": 2})
    assert cancelled.status_code == 200, cancelled.text
    data = cancelled.json()
    assert (data["status"], data["cancel_reason"], data["version"]) == ("CANCELLED", "Conteo duplicado", 3)
    assert data["cancelled_by_user_id"] and data["cancelled_at"]
    assert count_rows(test_engine, "inventory_adjustments") == 0
    draft = create(clerk, world)
    assert clerk.post(f"{base(world)}/{draft['id']}/cancel", json={"reason": "Ya no se necesita", "version": 1}).status_code == 200


def test_transitions_versions_and_states(clerk, world, stocked) -> None:
    a = stocked[0]
    count = create(clerk, world)
    assert register(clerk, world, count, a, "1").json()["code"] == "INVENTORY.COUNT_NOT_IN_PROGRESS"
    assert complete(clerk, world, count).json()["code"] == "INVENTORY.COUNT_NOT_IN_PROGRESS"

    stale = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": 9})
    assert (stale.status_code, stale.json()["code"]) == (409, "INVENTORY.VERSION_CONFLICT")

    started = start(clerk, world, count)
    again = clerk.post(f"{base(world)}/{count['id']}/start", json={"version": started["version"]})
    assert (again.status_code, again.json()["code"]) == (409, "INVENTORY.INVALID_COUNT_TRANSITION")

    register(clerk, world, started, a, "10")
    done = complete(clerk, world, started).json()
    cancel = clerk.post(f"{base(world)}/{count['id']}/cancel", json={"reason": "Tarde", "version": done["version"]})
    assert (cancel.status_code, cancel.json()["code"]) == (409, "INVENTORY.INVALID_COUNT_TRANSITION")
    assert register(clerk, world, started, a, "9").json()["code"] == "INVENTORY.COUNT_NOT_IN_PROGRESS"


def test_only_one_count_in_progress_per_branch(clerk, world) -> None:
    """Historia 2 escenario 8 (DS-07)."""
    first = start(clerk, world, create(clerk, world))
    second = create(clerk, world)
    response = clerk.post(f"{base(world)}/{second['id']}/start", json={"version": second["version"]})
    assert (response.status_code, response.json()["code"]) == (409, "INVENTORY.COUNT_ALREADY_IN_PROGRESS")
    clerk.post(f"{base(world)}/{first['id']}/cancel", json={"reason": "Reinicio", "version": first["version"]})
    assert clerk.post(f"{base(world)}/{second['id']}/start", json={"version": second["version"]}).status_code == 200


def test_invalid_products_in_details(clerk, world, fake_cr) -> None:
    count = start(clerk, world, create(clerk, world))
    inactive = fake_cr.add_product(world.company, status="INACTIVE")
    response = register(clerk, world, count, inactive, "1")
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "COMPANY_PRODUCT_INACTIVE"
    assert register(clerk, world, count, world.other_company_product, "1").json()["errors"][0]["code"] == "COMPANY_PRODUCT_NOT_FOUND"


def test_completion_key_is_idempotent(clerk, world, fake_oc, stocked, test_engine) -> None:
    a = stocked[0]
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, a, "7")
    key = uuid4()
    first = complete(clerk, world, count, key)
    assert first.status_code == 200
    fake_oc.fail_if_called = True
    again = complete(clerk, world, count, key)
    assert again.status_code == 200
    assert again.json() == first.json()
    assert count_rows(test_engine, "inventory_adjustments") == 1


def test_count_events(clerk, world, stocked, test_engine) -> None:
    """R-11: inicio, cancelación y finalización auditados; la finalización como resumen."""
    a, b, _ = stocked
    count = start(clerk, world, create(clerk, world))
    register(clerk, world, count, a, "8")
    register(clerk, world, count, b, "5")
    done = complete(clerk, world, count).json()
    other = create(clerk, world)
    clerk.post(f"{base(world)}/{other['id']}/cancel", json={"reason": "Sin uso", "version": 1})

    actions = [(event["action"], event["entity_type"]) for event in events(test_engine)]
    assert ("START_INVENTORY_COUNT", "InventoryCount") in actions
    assert ("CANCEL_INVENTORY_COUNT", "InventoryCount") in actions
    complete_event = next(event for event in events(test_engine) if event["action"] == "COMPLETE_INVENTORY_COUNT")
    values = complete_event["new_values"]
    assert (values["count_id"], values["operation_id"], values["adjustments"]) == (count["id"], done["operation_id"], 2)
    assert (values["positive_quantity"], values["negative_quantity"]) == ("1.0000", "2.0000")
    assert (values["positive_value"], values["negative_value"]) == ("50.00", "200.00")
    assert not any(event["action"] == "CREATE_INVENTORY_ADJUSTMENT" for event in events(test_engine))


def test_thousand_details_summary_fits_in_the_event(clerk, operator, world, fake_cr, test_engine) -> None:
    count = start(clerk, world, create(clerk, world))
    products = [fake_cr.add_product(world.company) for _ in range(1000)]
    with test_engine.begin() as connection:
        for product in products:
            connection.execute(
                text(
                    "INSERT INTO inventory_count_details (inventory_count_id, company_product_id, system_quantity_snapshot, "
                    "counted_quantity, difference_quantity, unit_cost, counted_by_user_id, counted_at, created_by, updated_by) "
                    "VALUES (:c, :p, 0, 1, 1, 3, gen_random_uuid(), now(), 's', 's')"
                ),
                {"c": count["id"], "p": product},
            )
    response = complete(clerk, world, count)
    assert response.status_code == 200, response.text[:300]
    event = next(event for event in events(test_engine) if event["action"] == "COMPLETE_INVENTORY_COUNT")
    assert event["new_values"]["adjustments"] == 1000
    assert len(json.dumps(event).encode()) < 64 * 1024
