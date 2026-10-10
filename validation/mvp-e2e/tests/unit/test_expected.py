"""T023 — Valores esperados del inventario FIFO (data-model §3.2–§3.4), calculados por la suite."""

from decimal import Decimal

import pytest

from sio_mvp import expected

pytestmark = pytest.mark.unit

D = Decimal


@pytest.fixture(scope="module")
def plan():
    return expected.mvp_plan()


def test_balances_after_purchases(plan):
    after = plan.snapshot("compras")
    assert after.quantity("A") == D("55") and after.value("A") == D("61700")
    assert after.quantity("B") == D("10") and after.value("B") == D("50000")
    assert [(layer.name, layer.remaining, layer.unit_cost) for layer in after.layers("A")] == [
        ("L1", D("24"), D("1000")),
        ("L2", D("26"), D("1200")),
        ("L3", D("5"), D("1300")),
    ]
    assert [(layer.name, layer.remaining, layer.unit_cost) for layer in after.layers("B")] == [("LB", D("10"), D("5000"))]


def test_box_entry_is_converted_to_base_unit(plan):
    entry = plan.entry("P1", "A")
    assert entry.quantity == D("24") and entry.unit_cost == D("1000")


def test_balances_after_sales(plan):
    after = plan.snapshot("ventas")
    assert after.quantity("A") == D("23") and after.value("A") == D("28100")
    assert after.quantity("B") == D("6") and after.value("B") == D("30000")
    assert [(layer.name, layer.remaining) for layer in after.layers("A") if layer.remaining] == [("L2", D("18")), ("L3", D("5"))]


@pytest.mark.parametrize(
    ("sale", "consumptions", "cost", "revenue", "margin", "percent"),
    [
        ("V1", [("L1", "12", "1000")], "12000", "16000", "4000", "25.00"),
        ("V2", [("L1", "12", "1000"), ("L2", "8", "1200")], "21600", "30000", "8400", "28.00"),
        ("V3", [("LB", "4", "5000")], "20000", "28000", "8000", "28.57"),
    ],
)
def test_fifo_consumption_cost_and_margin(plan, sale, consumptions, cost, revenue, margin, percent):
    output = plan.output(sale)
    assert [(item.layer, item.quantity, item.unit_cost) for item in output.consumptions] == [
        (layer, D(quantity), D(unit)) for layer, quantity, unit in consumptions
    ]
    assert output.cost == D(cost)
    assert output.revenue == D(revenue)
    assert output.margin == D(margin)
    assert output.margin_percent == D(percent)


def test_final_values_after_cancellations(plan):
    final = plan.snapshot("final")
    assert final.quantity("A") == D("18") and final.value("A") == D("21600")
    assert final.quantity("B") == D("10") and final.value("B") == D("50000")
    assert [(layer.name, layer.remaining, layer.unit_cost) for layer in final.layers("A") if layer.remaining] == [("L2", D("18"), D("1200"))]
    assert [(layer.name, layer.remaining, layer.unit_cost) for layer in final.layers("B") if layer.remaining] == [("LB", D("10"), D("5000"))]


def test_p1_cannot_be_reversed_because_its_layer_was_consumed(plan):
    assert plan.can_reverse_entry("P1") is False
    assert plan.can_reverse_entry("P2") is False  # L2 consumida por V2
    assert plan.entry_reversed("P3") is True


def test_expected_kardex(plan):
    assert plan.kardex("A") == [
        ("PURCHASE_ENTRY", D("24"), "P1"),
        ("PURCHASE_ENTRY", D("26"), "P2"),
        ("PURCHASE_ENTRY", D("5"), "P3"),
        ("SALE_OUTPUT", D("-12"), "V1"),
        ("SALE_OUTPUT", D("-20"), "V2"),
        ("ENTRY_REVERSAL", D("-5"), "P3"),
    ]
    assert plan.kardex("B") == [
        ("PURCHASE_ENTRY", D("10"), "P1"),
        ("SALE_OUTPUT", D("-4"), "V3"),
        ("OUTPUT_REVERSAL", D("4"), "V3"),
    ]


def test_running_balances_have_no_gaps(plan):
    assert plan.running_balances("A") == [D("24"), D("50"), D("55"), D("43"), D("23"), D("18")]
    assert plan.running_balances("B") == [D("10"), D("6"), D("10")]
