"""Idempotencia por clave ligada al cliente y huella `request_hash` (Historia 3; R-03; RC-05; T038)."""

from __future__ import annotations

import copy
import json

import pytest
from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def stock(test_engine, product) -> str:
    with test_engine.connect() as connection:
        value = connection.execute(
            text("SELECT quantity FROM inventory_balances WHERE company_product_id = :p"), {"p": product}
        ).scalar_one_or_none()
    return f"{value if value is not None else 0:.4f}"


def test_same_request_returns_original_without_calling_dependencies(operator, world, fake_oc, fake_cr, test_engine) -> None:
    p1, p2 = world.products[:2]
    body = operation_body(world, line(p1, "10", unit_cost="1500.25"), line(p2, "5.5"))
    first = operator.post(ENTRIES, json=body)
    assert first.status_code == 201

    # Un segundo movimiento hace que el saldo vigente sea distinto del de aquel momento.
    operator.post(ENTRIES, json=operation_body(world, line(p1, "1")))

    fake_oc.fail_if_called = True
    fake_cr.fail_if_called = True
    again = operator.post(ENTRIES, json=body)

    assert again.status_code == 200
    assert again.json() == first.json()
    assert stock(test_engine, p1) == "11.0000"
    assert count_rows(test_engine, "inventory_operations") == 2


def test_same_request_in_another_representation_is_the_same(operator, world) -> None:
    product = world.products[0]
    body = operation_body(world, line(product, "10", unit_cost="1500.25"))
    first = operator.post(ENTRIES, json=body)

    other = copy.deepcopy(body)
    other["lines"][0]["quantity"] = 10
    other["lines"][0]["unit_cost"] = "1500.2500"
    other["company_id"] = other["company_id"].upper()
    reordered = json.loads(json.dumps(dict(reversed(list(other.items())))))
    again = operator.post(ENTRIES, json=reordered)

    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]


@pytest.mark.parametrize(
    "change",
    [
        lambda b, w: b["lines"][0].update(quantity="11"),
        lambda b, w: b["lines"][0].update(unit_cost="1500.26"),
        lambda b, w: b["lines"].append(line(w.products[1], "1", unit_cost="1")),  # 013: entrada con costo
        lambda b, w: b["lines"].reverse(),
        lambda b, w: b.update(application_user_id=str(w.other_company_user)),
        lambda b, w: b.update(reason="Otro motivo"),
    ],
)
def test_same_key_with_a_different_request_is_a_conflict(operator, world, test_engine, change) -> None:
    body = operation_body(world, line(world.products[0], "10", unit_cost="1500.25"), line(world.products[2], "1"))
    original = operator.post(ENTRIES, json=body)
    assert original.status_code == 201

    changed = copy.deepcopy(body)
    change(changed, world)
    response = operator.post(ENTRIES, json=changed)

    assert response.status_code == 409
    data = response.json()
    assert data["code"] == "INVENTORY.OPERATION_KEY_CONFLICT"
    assert original.json()["id"] not in response.text
    assert "movements" not in data
    assert count_rows(test_engine, "inventory_operations") == 1


def test_same_key_from_another_client_is_a_conflict(operator, purchase, world) -> None:
    body = operation_body(world, line(world.products[0], "1"))
    assert operator.post(ENTRIES, json=body).status_code == 201
    response = purchase.post(ENTRIES, json=body)
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.OPERATION_KEY_CONFLICT"


def test_same_key_on_the_other_type_is_a_conflict(operator, world) -> None:
    product = world.products[0]
    entry = operation_body(world, line(product, "5"))
    assert operator.post(ENTRIES, json=entry).status_code == 201
    # 013: una salida no admite costo; la misma clave con el cuerpo sin costo sigue siendo un conflicto.
    output = {**entry, "origin_type": "SALE", "lines": [{k: v for k, v in entry["lines"][0].items() if k != "unit_cost"}]}
    assert operator.post(OUTPUTS, json=output).status_code == 409


@pytest.mark.parametrize("failure", ["insufficient", "validation", "unavailable"])
def test_rejected_key_is_evaluated_again(operator, world, fake_cr, test_engine, failure) -> None:
    product = world.products[0]
    if failure == "insufficient":
        body = operation_body(world, line(product, "3"), origin_type="SALE")
        assert operator.post(OUTPUTS, json=body).status_code == 409
        operator.post(ENTRIES, json=operation_body(world, line(product, "5")))
        assert operator.post(OUTPUTS, json=body).status_code == 201
        assert stock(test_engine, product) == "2.0000"
        return

    body = operation_body(world, line(product, "3"))
    if failure == "validation":
        fake_cr.products[product] = fake_cr.products[product].__class__(product, world.company, "INACTIVE", True)
        assert operator.post(ENTRIES, json=body).status_code == 422
        fake_cr.products[product] = fake_cr.products[product].__class__(product, world.company, "ACTIVE", True)
    else:
        fake_cr.unavailable = True
        assert operator.post(ENTRIES, json=body).status_code == 503
        fake_cr.unavailable = False

    assert operator.post(ENTRIES, json=body).status_code == 201


def test_thousand_sequential_repeats_change_the_balance_once(operator, world, test_engine) -> None:
    product = world.products[0]
    body = operation_body(world, line(product, "2"))
    statuses = [operator.post(ENTRIES, json=body).status_code for _ in range(1000)]
    assert statuses[0] == 201
    assert set(statuses[1:]) == {200}
    assert stock(test_engine, product) == "2.0000"
    assert count_rows(test_engine, "inventory_movements") == 1
