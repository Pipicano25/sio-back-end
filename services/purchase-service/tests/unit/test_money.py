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
    # Spec 020: un subtotal que redondea a 0,00 deja el costo neto en 0 → rechazado.
    with pytest.raises(DomainRuleError) as error:
        line_amounts(D("1"), D("0.0049"), D("0"), D("0"))
    assert error.value.code == "NET_COST_NOT_POSITIVE"


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
        (D("1"), D("-0.01"), D("0"), D("0"), "UNIT_COST_NOT_POSITIVE", "unit_cost"),
        (D("1"), D("0"), D("0"), D("0"), "UNIT_COST_NOT_POSITIVE", "unit_cost"),
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


def test_discount_equal_to_subtotal_is_rejected() -> None:
    """Spec 020 (FR-020-12): el costo neto debe ser mayor que cero."""
    with pytest.raises(DomainRuleError) as error:
        line_amounts(D("1"), D("10"), D("10"), D("0"))
    assert (error.value.code, error.value.field) == ("NET_COST_NOT_POSITIVE", "discount_amount")


def test_discount_just_below_subtotal_is_allowed() -> None:
    assert line_amounts(D("1"), D("10"), D("9.99"), D("0")).total == D("0.01")


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


# ---------------------------------------------------------------- spec 021: impuesto por tasa (FR-021-09)


def test_tax_from_rate_is_rounded_half_up_over_the_net_cost() -> None:
    from purchase_service.domain.money import with_tax

    base = line_amounts(D("2"), D("120000"), D("24000"), D("0"))
    taxed = with_tax(base, D("19"))
    assert taxed.tax_amount == D("41040.00") and taxed.total == D("257040.00")  # (240.000 − 24.000) × 19 %
    assert with_tax(line_amounts(D("1"), D("0.05"), D("0"), D("0")), D("10")).tax_amount == D("0.01")  # 0,005 → 0,01
    assert with_tax(base, None).tax_amount == D("0.00")  # sin configurar: 0 hasta que haya tasa
    assert with_tax(base, D("0")).total == D("216000.00")


@pytest.mark.parametrize("value", ["0", "19", "100", "12.3456"])
def test_tax_percentage_accepted(value: str) -> None:
    from purchase_service.domain.money import check_tax_percentage

    assert check_tax_percentage(value) == D(value)


@pytest.mark.parametrize("value", ["-0.0001", "100.0001", "1.23456", "abc", True])
def test_tax_percentage_rejected(value) -> None:
    from purchase_service.domain.money import check_tax_percentage

    with pytest.raises(DomainRuleError) as error:
        check_tax_percentage(value)
    assert error.value.code == "TAX_PERCENTAGE_OUT_OF_RANGE"
