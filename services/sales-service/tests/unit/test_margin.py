"""Margen bruto y su porcentaje (DS-06, P-01, C-03; research.md R-10; T008)."""

from __future__ import annotations

from decimal import Decimal as D

from sales_service.domain.margin import (
    COMPUTED,
    COST_UNKNOWN,
    NET_ZERO,
    OUT_OF_RANGE,
    compute_margin,
)


def test_margin_on_net_value() -> None:
    result = compute_margin(subtotal=D("30000.00"), discount_amount=D("0.00"), cost_total=D("24000.00"), cost_known=True)
    assert result.amount == D("6000.00")
    assert result.percentage == D("20.0000")
    assert result.outcome == COMPUTED


def test_discount_reduces_the_net_value_and_taxes_are_excluded() -> None:
    # neto = 1000 − 100 = 900; margen = 900 − 600 = 300; 300 / 900 = 33.3333 %
    result = compute_margin(subtotal=D("1000.00"), discount_amount=D("100.00"), cost_total=D("600.00"), cost_known=True)
    assert (result.amount, result.percentage, result.outcome) == (D("300.00"), D("33.3333"), COMPUTED)


def test_percentage_rounds_half_up() -> None:
    # 1 / 3 × 100 = 33.33333… → 33.3333; 2 / 3 × 100 = 66.6666… → 66.6667
    assert compute_margin(D("3.00"), D("0"), D("2.00"), True).percentage == D("33.3333")
    assert compute_margin(D("3.00"), D("0"), D("1.00"), True).percentage == D("66.6667")


def test_selling_below_cost_gives_negative_margin() -> None:
    result = compute_margin(D("100.00"), D("0"), D("150.00"), True)
    assert (result.amount, result.percentage, result.outcome) == (D("-50.00"), D("-50.0000"), COMPUTED)


def test_net_zero_keeps_amount_and_leaves_percentage_null() -> None:
    result = compute_margin(D("500.00"), D("500.00"), D("320.00"), True)
    assert result.amount == D("-320.00")
    assert result.percentage is None
    assert result.outcome == NET_ZERO


def test_largest_representable_negative_percentage() -> None:
    # neto 1, costo 10.999999 → margen −9.999999…; con montos de 2 decimales: neto 1.00, costo 10.99 → −999.0000
    result = compute_margin(D("1.00"), D("0"), D("10.99"), True)
    assert (result.percentage, result.outcome) == (D("-999.0000"), COMPUTED)
    # −999.99995 % redondea a −1000.0000: ya no cabe en NUMERIC(7,4)
    edge = compute_margin(D("100000.00"), D("0"), D("1099999.95"), True)
    assert edge.percentage is None and edge.outcome == OUT_OF_RANGE


def test_out_of_range_percentage_is_null_never_saturated_or_truncated() -> None:
    result = compute_margin(D("0.01"), D("0"), D("5000.00"), True)
    assert result.amount == D("-4999.99")
    assert result.percentage is None
    assert result.outcome == OUT_OF_RANGE


def test_boundary_just_inside_the_column() -> None:
    # margen / neto × 100 = −999.9999 exactamente
    result = compute_margin(D("10000.00"), D("0"), D("109999.99"), True)
    assert (result.percentage, result.outcome) == (D("-999.9999"), COMPUTED)


def test_unknown_cost_leaves_both_null() -> None:
    result = compute_margin(D("30000.00"), D("0"), D("0.00"), False)
    assert (result.amount, result.percentage, result.outcome) == (None, None, COST_UNKNOWN)
