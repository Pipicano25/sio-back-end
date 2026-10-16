"""Montos de línea y de cabecera (FR-007; research.md R-17; T007)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from sales_service.domain.money import DomainRuleError, check_line_inputs, header_totals, line_amounts


def test_line_subtotal_and_total() -> None:
    """Spec 021 (B-4): sin impuesto adicional, el total es el subtotal del precio de lista."""
    amounts = line_amounts(D("2"), D("15000"), D("0"), D("0"))
    assert amounts.subtotal == D("30000.00")
    assert amounts.total == D("30000.00")
    assert amounts.unit_price == D("15000.0000")


def test_subtotal_rounds_half_up_to_cents() -> None:
    assert line_amounts(D("3"), D("0.3335"), D("0"), D("0")).subtotal == D("1.00")  # 1.0005 → 1.00
    assert line_amounts(D("1"), D("0.0050"), D("0"), D("0")).subtotal == D("0.01")
    assert line_amounts(D("1"), D("0.0049"), D("0"), D("0")).subtotal == D("0.00")


def test_cp63_any_tax_is_rejected_and_zero_is_accepted() -> None:
    """Spec 021 (B-4, FR-021-30): el precio de la lista es final; `tax_amount` solo admite 0 (no es solución fiscal)."""
    for tax in ("19.99", "0.01", "5700"):
        with pytest.raises(DomainRuleError) as error:
            line_amounts(D("10"), D("100"), D("0"), D(tax), prefix="lines[0].")
        assert (error.value.code, error.value.field) == ("TAX_NOT_ALLOWED", "lines[0].tax_amount")
    amounts = line_amounts(D("10"), D("100"), D("0"), D("0"))
    assert (amounts.subtotal, amounts.tax_amount, amounts.total) == (D("1000.00"), D("0.00"), D("1000.00"))


@pytest.mark.parametrize(
    ("quantity", "unit_price", "discount", "tax", "code", "field"),
    [
        (D("0"), D("1"), D("0"), D("0"), "QUANTITY_NOT_POSITIVE", "quantity"),
        (D("-1"), D("1"), D("0"), D("0"), "QUANTITY_NOT_POSITIVE", "quantity"),
        (D("1.00001"), D("1"), D("0"), D("0"), "TOO_MANY_DECIMALS", "quantity"),
        (D("100000000000000"), D("1"), D("0"), D("0"), "AMOUNT_OUT_OF_RANGE", "quantity"),
        (D("1"), D("10"), D("-1"), D("0"), "AMOUNT_OUT_OF_RANGE", "discount_amount"),
        (D("1"), D("10"), D("0.001"), D("0"), "TOO_MANY_DECIMALS", "discount_amount"),
        (D("1"), D("10"), D("10.01"), D("0"), "DISCOUNT_NOT_ALLOWED", "discount_amount"),  # spec 020
        (D("1"), D("10"), D("0.01"), D("0"), "DISCOUNT_NOT_ALLOWED", "discount_amount"),
        (D("1"), D("10"), D("0"), D("-1"), "AMOUNT_OUT_OF_RANGE", "tax_amount"),
        (D("1"), D("10"), D("0"), D("1"), "TAX_NOT_ALLOWED", "tax_amount"),  # spec 021
        (D("99999999999999"), D("99999"), D("0"), D("0"), "AMOUNT_OUT_OF_RANGE", "quantity"),
    ],
)
def test_line_rejections(quantity, unit_price, discount, tax, code, field) -> None:
    with pytest.raises(DomainRuleError) as error:
        line_amounts(quantity, unit_price, discount, tax, prefix="lines[0].")
    assert error.value.code == code
    assert error.value.field == f"lines[0].{field}"


@pytest.mark.parametrize(
    ("quantity", "discount", "tax", "code", "field"),
    [
        (D("0"), D("0"), D("0"), "QUANTITY_NOT_POSITIVE", "quantity"),
        (D("1"), D("-1"), D("0"), "AMOUNT_OUT_OF_RANGE", "discount_amount"),
        (D("1"), D("0"), D("0.001"), "TOO_MANY_DECIMALS", "tax_amount"),
    ],
)
def test_inputs_are_checked_before_the_price_is_known(quantity, discount, tax, code, field) -> None:
    """Formato de cantidad, descuento e impuesto antes de consultar el precio (R-07)."""
    with pytest.raises(DomainRuleError) as error:
        check_line_inputs(quantity, discount, tax, prefix="lines[1].")
    assert (error.value.code, error.value.field) == (code, f"lines[1].{field}")


def test_any_discount_is_rejected_and_zero_is_accepted() -> None:
    """Spec 020 (FR-020-13, RC-MVP-6): `discount_amount` solo admite 0."""
    for discount in ("10", "0.01", "5"):
        with pytest.raises(DomainRuleError) as error:
            line_amounts(D("1"), D("10"), D(discount), D("0"))
        assert error.value.code == "DISCOUNT_NOT_ALLOWED"
    assert line_amounts(D("1"), D("10"), D("0.00"), D("0")).total == D("10.00")


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
