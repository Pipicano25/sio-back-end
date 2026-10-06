"""Evento de auditoría en la outbox, en la misma transacción (FR-070 a FR-074; RC-08; T052)."""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from sqlalchemy import text

from tests.conftest import line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def outbox(test_engine) -> list[dict]:
    with test_engine.connect() as connection:
        rows = connection.execute(text("SELECT status, payload FROM audit_outbox ORDER BY created_at")).all()
    assert all(row.status == "PENDING" for row in rows)
    return [row.payload if isinstance(row.payload, dict) else json.loads(row.payload) for row in rows]


def test_one_pending_event_per_applied_operation(operator, world, fake_oc, test_engine) -> None:
    p1, p2 = world.products[:2]
    entry_body = operation_body(world, line(p1, "10", unit_cost="1500.25"), line(p2, "2"))
    entry = operator.post(ENTRIES, json=entry_body)
    output = operator.post(OUTPUTS, json=operation_body(world, line(p1, "3"), origin_type="SALE")).json()
    reversal = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world)).json()
    entry_reversal = operator.post(f"{ENTRIES}/{entry.json()['id']}/reversal", json=reversal_body(world))
    assert entry_reversal.status_code == 201

    events = outbox(test_engine)
    assert [event["action"] for event in events] == [
        "APPLY_INVENTORY_ENTRY", "APPLY_INVENTORY_OUTPUT", "REVERSE_INVENTORY_OUTPUT", "REVERSE_INVENTORY_ENTRY"
    ]

    first = events[0]
    data = entry.json()
    assert first["entity_type"] == "InventoryOperation"
    assert first["entity_id"] == data["id"]
    assert (first["company_id"], first["branch_id"], first["application_user_id"]) == (
        str(world.company), str(world.branch), str(world.user)
    )
    assert first["keycloak_user_id"] == str(fake_oc.users[world.user].keycloak_user_id)
    assert first["correlation_id"] == entry_body["correlation_id"]
    assert UUID(first["request_id"]).hex == entry.headers["x-trace-id"]
    assert first["result"] == "SUCCESS" and first["previous_values"] is None
    values = first["new_values"]
    assert values["operation_key"] == entry_body["operation_key"]
    assert (values["operation_type"], values["origin_type"], values["origin_id"]) == ("ENTRY", "PURCHASE", entry_body["origin_id"])
    assert values["reverses_operation_id"] is None
    assert values["lines"][0] == {
        "origin_detail_id": entry_body["lines"][0]["origin_detail_id"],
        "company_product_id": str(p1),
        "quantity": "10.0000",
        "unit_cost": "1500.2500",
        "movement_id": data["movements"][0]["id"],
        "previous_balance": "0.0000",
        "new_balance": "10.0000",
    }
    assert events[2]["new_values"]["reverses_operation_id"] == output["id"]
    assert events[2]["entity_id"] == reversal["id"]
    assert events[2]["reason"] == reversal_body(world)["reason"]


def test_replay_does_not_create_another_event(operator, world, test_engine) -> None:
    body = operation_body(world, line(world.products[0], "1"))
    assert operator.post(ENTRIES, json=body).status_code == 201
    assert operator.post(ENTRIES, json=body).status_code == 200
    assert len(outbox(test_engine)) == 1


@pytest.mark.parametrize("failure", ["validation", "insufficient", "unavailable", "conflict", "already_reversed"])
def test_rejections_leave_no_event(operator, world, fake_cr, test_engine, failure) -> None:
    product = world.products[0]
    if failure == "validation":
        operator.post(ENTRIES, json=operation_body(world, line(world.other_company_product, "1")))
    elif failure == "insufficient":
        operator.post(OUTPUTS, json=operation_body(world, line(product, "1"), origin_type="SALE"))
    elif failure == "unavailable":
        fake_cr.unavailable = True
        operator.post(ENTRIES, json=operation_body(world, line(product, "1")))
    else:
        body = operation_body(world, line(product, "1"))
        entry = operator.post(ENTRIES, json=body).json()
        if failure == "conflict":
            operator.post(ENTRIES, json={**body, "lines": [line(product, "2")]})
        else:
            operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
            operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
        expected = 1 if failure == "conflict" else 2
        assert len(outbox(test_engine)) == expected
        return
    assert outbox(test_engine) == []


def test_hundred_lines_fit_in_the_event(operator, world, test_engine) -> None:
    lines = [line(world.products[i % 3], "1.5", unit_cost="99999.9999") for i in range(100)]
    assert operator.post(ENTRIES, json=operation_body(world, *lines)).status_code == 201
    event = outbox(test_engine)[0]
    assert len(event["new_values"]["lines"]) == 100
    assert len(json.dumps(event["new_values"]).encode()) < 64 * 1024
