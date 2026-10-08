"""Existencias insuficientes al confirmar (FR-015, FR-020, RC-04; research.md R-05, R-08; T052).

La consulta previa anticipa el rechazo sin efectos; la barrera definitiva es Inventory.
"""

from __future__ import annotations

from decimal import Decimal

from tests.conftest import count_rows, fetch, line


def test_precheck_rejects_without_operation_or_output(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "20", "1000")
    draft = make_draft(line(world.product, "1", company_product_presentation_id=world.presentation), line(world.product, "9"))
    response = confirm(draft)  # 12 + 9 = 21 > 20
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "SALES.INSUFFICIENT_STOCK"
    assert body["shortages"] == [
        {"line_numbers": [1, 2], "company_product_id": str(world.product), "available": "20.0000", "requested": "21.0000"}
    ]
    assert [call[0] for call in fakes.inventory.availability.calls] == ["balances"]
    assert fakes.inventory.outputs() == [] and count_rows(test_engine, "sale_operations") == 0
    assert fetch(test_engine, "SELECT status, number FROM sales")[0] == {"status": "DRAFT", "number": None}
    assert fakes.inventory.balance(world.branch, world.product) == 20


def test_inventory_is_the_definitive_barrier(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """La consulta previa dice que alcanza; otra venta se lleva el saldo antes de la salida (RC-04)."""
    make_sequence()
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "5", "1000")
    fakes.inventory.stock(world.branch, world.product_2, "5", "6000")
    draft = make_draft(line(world.product_2, "1"), line(world.product, "5"))
    original = fakes.inventory.apply_output

    def stolen_then_apply(payload):
        fakes.inventory.layers[(str(world.branch), str(world.product))][0].quantity = Decimal("3")
        return original(payload)

    fakes.inventory.apply_output = stolen_then_apply
    response = confirm(draft)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "SALES.INSUFFICIENT_STOCK"
    assert body["shortages"] == [
        {"line_numbers": [2], "company_product_id": str(world.product), "available": "3.0000", "requested": "5.0000"}
    ]
    [operation] = fetch(test_engine, "SELECT status, error_code FROM sale_operations")
    assert operation == {"status": "FAILED", "error_code": "INSUFFICIENT_STOCK"}
    assert fetch(test_engine, "SELECT status, number FROM sales")[0] == {"status": "DRAFT", "number": None}
    assert count_rows(test_engine, "sale_sequence_counters") == 0
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox")]
    assert [(event["action"], event["result"]) for event in events if event["action"] == "CONFIRM_SALE"] == [
        ("CONFIRM_SALE", "FAILURE")
    ]


def test_same_key_after_insufficient_stock_repeats_the_error(world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    fakes.inventory.layers.clear()
    draft = make_draft(line(world.product, "1"))
    original = fakes.inventory.lookup_balances
    fakes.inventory.lookup_balances = lambda company, branch, ids: {
        product: original(company, branch, ids)[product].__class__(product, Decimal("99")) for product in ids
    }
    first = confirm(draft, "k-stock")
    fakes.inventory.lookup_balances = original
    repeated = confirm(draft, "k-stock")
    assert first.status_code == repeated.status_code == 409
    assert first.json()["code"] == repeated.json()["code"] == "SALES.INSUFFICIENT_STOCK"
