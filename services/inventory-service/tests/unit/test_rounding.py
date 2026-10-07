"""Redondeo y valores de inventario (research.md R-04, FR-055; T004)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from inventory_service.domain.rounding import (
    average_unit_cost,
    inventory_value,
    line_value,
    money,
    output_unit_cost,
    unit,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.005", "0.01"),  # ROUND_HALF_UP: hacia arriba, no al par
        ("0.015", "0.02"),
        ("0.025", "0.03"),  # el redondeo bancario daría 0.02
        ("2.675", "2.68"),
        ("1.004", "1.00"),
        ("-0.005", "-0.01"),
    ],
)
def test_money_rounds_half_up_to_two_decimals(value: str, expected: str) -> None:
    assert money(D(value)) == D(expected)
    assert money(D(value)).as_tuple().exponent == -2


def test_unit_rounds_half_up_to_four_decimals() -> None:
    assert unit(D("1.00005")) == D("1.0001")
    assert unit(D("1.00004")) == D("1.0000")
    assert unit(D("1050")).as_tuple().exponent == -4


def test_line_value_is_quantity_by_cost_rounded() -> None:
    assert line_value(D("10"), D("1000")) == D("10000.00")
    assert line_value(D("3"), D("0.3333")) == D("1.00")  # 0.9999 → 1.00
    assert line_value(D("1.5"), D("0.0033")) == D("0.00")  # 0.00495 → 0.00
    assert line_value(D("1.5"), D("0.0034")) == D("0.01")  # 0.0051 → 0.01


def test_line_value_keeps_precision_for_large_numbers() -> None:
    # 14 dígitos enteros × 14 dígitos enteros no se trunca por la precisión del contexto.
    assert line_value(D("99999999999999.9999"), D("1")) == D("99999999999999.9999").quantize(D("0.01"))


def test_output_unit_cost_is_value_over_quantity_with_four_decimals() -> None:
    assert output_unit_cost(D("12600.00"), D("12")) == D("1050.0000")
    assert output_unit_cost(D("10.00"), D("3")) == D("3.3333")
    assert output_unit_cost(D("20.00"), D("3")) == D("6.6667")


def test_average_unit_cost_is_null_without_stock() -> None:
    assert average_unit_cost(D("3900.00"), D("3")) == D("1300.0000")
    assert average_unit_cost(D("0.00"), D("0")) is None


def test_inventory_value_is_recomputed_from_layers_without_accumulated_residue() -> None:
    layers = [(D("1"), D("0.3333"))] * 3
    # Cada capa se redondea por separado: 3 × 0.33 = 0.99 (no 1.00, ni un acumulado que derive).
    assert inventory_value(layers) == D("0.99")
    # Capas agotadas no suman.
    assert inventory_value([(D("0"), D("5")), (D("2"), D("1.005"))]) == D("2.01")
    assert inventory_value([]) == D("0.00")


def test_recomputation_after_many_periodic_costs_has_no_drift() -> None:
    """Consumir de a 1 unidad a costo 1/3 nunca deja un residuo distinto del cálculo directo."""
    remaining = D("300")
    cost = D("0.3333")
    for _ in range(299):
        remaining -= 1
        assert inventory_value([(remaining, cost)]) == money(remaining * cost)
    assert inventory_value([(remaining, cost)]) == D("0.33")
