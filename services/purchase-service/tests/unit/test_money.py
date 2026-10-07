"""Montos de línea y de cabecera (FR-006, FR-007; research.md R-11; T007)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from purchase_service.domain.money import DomainRuleError, header_totals, line_amounts


def test_line_subtotal_and_total() -> None:
    amounts = line_amounts(D("2"), D("120000"), D("0"), D("45600"))
    assert amounts.subtotal == D("240000.00")
    assert amounts.total == D("285600.00")


def test_subtotal_rounds_half_up_to_cents() -> None:
    assert line_amounts(D("3"), D("0.3335"), D("0"), D("0")).subtotal == D("1.00")  # 1.0005 → 1.00
    assert line_amounts(D("1"), D("0.0050"), D("0"), D("0")).subtotal == D("0.01")
    assert line_amounts(D("1"), D("0.0049"), D("0"), D("0")).subtotal == D("0.00")


def test_total_subtracts_discount_and_adds_tax() -> None:
    amounts = line_amounts(D("10"), D("100"), D("150.50"), D("19.99"))
    assert amounts.total == D("1000.00") - D("150.50") + D("19.99")


@pytest.mark.parametrize(
    ("quantity", "unit_cost", "discount", "tax", "code", "field"),
    [
        (D("0"), D("1"), D("0"), D("0"), "QUANTITY_NOT_POSITIVE", "quantity"),
        (D("-1"), D("1"), D("0"), D("0"), "QUANTITY_NOT_POSITIVE", "quantity"),
        (D("1.00001"), D("1"), D("0"), D("0"), "TOO_MANY_DECIMALS", "quantity"),
        (D("100000000000000"), D("1"), D("0"), D("0"), "AMOUNT_OUT_OF_RANGE", "quantity"),
        (D("1"), D("-0.01"), D("0"), D("0"), "AMOUNT_OUT_OF_RANGE", "unit_cost"),
        (D("1"), D("1.00001"), D("0"), D("0"), "TOO_MANY_DECIMALS", "unit_cost"),
        (D("1"), D("10"), D("-1"), D("0"), "AMOUNT_OUT_OF_RANGE", "discount_amount"),
        (D("1"), D("10"), D("0.001"), D("0"), "TOO_MANY_DECIMALS", "discount_amount"),
        (D("1"), D("10"), D("10.01"), D("0"), "DISCOUNT_EXCEEDS_SUBTOTAL", "discount_amount"),
        (D("1"), D("10"), D("0"), D("-1"), "AMOUNT_OUT_OF_RANGE", "tax_amount"),
        (D("99999999999999"), D("99999"), D("0"), D("0"), "AMOUNT_OUT_OF_RANGE", "quantity"),
    ],
)
def test_line_rejections(quantity, unit_cost, discount, tax, code, field) -> None:
    with pytest.raises(DomainRuleError) as error:
        line_amounts(quantity, unit_cost, discount, tax, prefix="lines[0].")
    assert error.value.code == code
    assert error.value.field == f"lines[0].{field}"


def test_discount_equal_to_subtotal_is_allowed() -> None:
    assert line_amounts(D("1"), D("10"), D("10"), D("0")).total == D("0.00")


def test_header_totals() -> None:
    totals = header_totals([(D("100.00"), D("10.00"), D("19.00")), (D("50.50"), D("0.00"), D("0.00"))])
    assert (totals.subtotal, totals.discount_total, totals.tax_total, totals.total) == (
        D("150.50"),
        D("10.00"),
        D("19.00"),
        D("159.50"),
    )


def test_header_totals_out_of_range() -> None:
    with pytest.raises(DomainRuleError) as error:
        header_totals([(D("9999999999999999.00"), D("0"), D("0"))] * 2)
    assert error.value.code == "AMOUNT_OUT_OF_RANGE"
