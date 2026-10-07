"""Reversos con `company_id` obligatorio (Historia 4; FR-030 a FR-034; RC-04, RC-10; T041)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from inventory_service.application.ports import BranchInfo, CompanyProductInfo
from tests.conftest import count_rows, line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def stock(test_engine, product) -> str:
    with test_engine.connect() as connection:
        value = connection.execute(
            text("SELECT quantity FROM inventory_balances WHERE company_product_id = :p"), {"p": product}
        ).scalar_one_or_none()
    return f"{value if value is not None else 0:.4f}"


@pytest.fixture
def entry(operator, world):
    response = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "15.5", unit_cost="1500.25")))
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def output(operator, world, entry):
    response = operator.post(OUTPUTS, json=operation_body(world, line(world.products[0], "5"), origin_type="SALE"))
    assert response.status_code == 201
    return response.json()


def test_reverse_output_restores_the_balance(operator, world, output, test_engine) -> None:
    response = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["operation_type"] == "OUTPUT_REVERSAL"
    assert data["reverses_operation_id"] == output["id"]
    assert data["origin_type"] == "SALE" and data["origin_id"] == output["origin_id"]
    movement = data["movements"][0]
    assert movement["movement_type"] == "OUTPUT_REVERSAL"
    assert movement["reversed_movement_id"] == output["movements"][0]["id"]
    assert movement["origin_detail_id"] == output["movements"][0]["origin_detail_id"]
    assert (movement["quantity"], movement["previous_balance"], movement["new_balance"]) == ("5.0000", "10.5000", "15.5000")
    assert stock(test_engine, world.products[0]) == "15.5000"

    original = operator.get(f"/api/v1/companies/{world.company}/inventory-operations/{output['id']}")
    if original.status_code == 200:  # la consulta de operaciones pertenece a la US5
        assert original.json()["reversed_by_operation_id"] == data["id"]


def test_entry_reversal_copies_the_unit_cost(operator, world, entry) -> None:
    response = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 201
    movement = response.json()["movements"][0]
    assert (movement["movement_type"], movement["unit_cost"], movement["new_balance"]) == ("ENTRY_REVERSAL", "1500.2500", "0.0000")


def test_entry_reversal_without_stock_is_rejected(operator, world, entry, test_engine) -> None:
    operator.post(OUTPUTS, json=operation_body(world, line(world.products[0], "12.5"), origin_type="SALE"))
    before = count_rows(test_engine, "inventory_movements")
    response = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 409
    # 013 (FR-053, Historia 3 escenario 6): con valoración, una entrada sin saldo para retirarse es una
    # entrada cuya capa ya se consumió; se rechaza con esa causa precisa en lugar de INSUFFICIENT_STOCK.
    assert response.json()["code"] == "INVENTORY.ENTRY_LAYER_CONSUMED"
    assert count_rows(test_engine, "inventory_movements") == before
    assert stock(test_engine, world.products[0]) == "3.0000"


def test_already_reversed_and_idempotent_reversal(operator, world, output) -> None:
    body = reversal_body(world)
    first = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=body)
    assert first.status_code == 201
    again = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=body)
    assert again.status_code == 200 and again.json() == first.json()
    other_key = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world))
    assert other_key.status_code == 409
    assert other_key.json()["code"] == "INVENTORY.ALREADY_REVERSED"


def test_a_reversal_cannot_be_reversed(operator, world, output) -> None:
    reversal = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world)).json()
    response = operator.post(f"{OUTPUTS}/{reversal['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.REVERSAL_NOT_ALLOWED"


def test_not_found_is_identical_for_missing_other_company_and_other_type(operator, world, output, entry) -> None:
    responses = [
        operator.post(f"{OUTPUTS}/{uuid4()}/reversal", json=reversal_body(world)),
        operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world, company_id=str(world.other_company), application_user_id=str(world.other_company_user))),
        operator.post(f"{OUTPUTS}/{entry['id']}/reversal", json=reversal_body(world)),
    ]
    bodies = []
    for response in responses:
        assert response.status_code == 404
        body = response.json()
        body.pop("trace_id")
        body.pop("instance")
        bodies.append(body)
    assert bodies[0] == bodies[1] == bodies[2]
    assert output["id"] not in str(bodies)


def test_company_id_is_required(operator, world, output) -> None:
    body = reversal_body(world)
    body.pop("company_id")
    response = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=body)
    assert response.status_code == 422
    assert {"field": "company_id", "code": "REQUIRED"}.items() <= response.json()["errors"][0].items()


def test_reason_is_required(operator, world, output) -> None:
    response = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world, reason=None))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "REASON_REQUIRED"


def test_inactive_product_and_branch_do_not_block_and_are_not_validated(operator, world, output, fake_oc, fake_cr) -> None:
    product = world.products[0]
    fake_cr.products[product] = CompanyProductInfo(product, world.company, "INACTIVE", False)
    fake_oc.branches[world.branch] = BranchInfo(world.branch, world.company, "INACTIVE", "INACTIVE")
    fake_cr.fail_if_called = True
    fake_oc.technical_calls.clear()

    response = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world))

    assert response.status_code == 201
    assert [call[0] for call in fake_oc.technical_calls] == ["application_user"]


def test_reversal_user_inactive_is_accepted_but_other_company_is_not(operator, world, output, entry, fake_oc) -> None:
    inactive = fake_oc.add_user(world.company, status="INACTIVE")
    response = operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world, application_user_id=str(inactive)))
    assert response.status_code == 201

    rejected = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world, application_user_id=str(world.other_company_user)))
    assert rejected.status_code == 422
    assert rejected.json()["errors"][0]["code"] == "APPLICATION_USER_NOT_FOUND"
    missing = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world, application_user_id=str(uuid4())))
    assert missing.json()["errors"][0]["code"] == "APPLICATION_USER_NOT_FOUND"


def test_reversal_with_multiple_lines(operator, world, test_engine) -> None:
    p1, p2 = world.products[:2]
    entry = operator.post(ENTRIES, json=operation_body(world, line(p1, "3"), line(p2, "4"))).json()
    response = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world))
    assert response.status_code == 201
    assert [m["reversed_movement_id"] for m in response.json()["movements"]] == [m["id"] for m in entry["movements"]]
    assert stock(test_engine, p1) == "0.0000" and stock(test_engine, p2) == "0.0000"
