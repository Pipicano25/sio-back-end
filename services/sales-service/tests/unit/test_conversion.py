"""Conversión a unidad base y del precio a la unidad de venta (DS-03, DS-04, P-04; research.md R-07; T007)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from sales_service.domain.conversion import BASE_UNIT, PRESENTATION, base_quantity, sale_unit_price
from sales_service.domain.money import DomainRuleError


def test_base_quantity_with_presentation_factor() -> None:
    assert base_quantity(D("2"), D("12")) == D("24.0000")
    assert base_quantity(D("1.5"), D("0.5")) == D("0.7500")


def test_base_quantity_exact_with_more_than_four_decimals_is_rejected() -> None:
    with pytest.raises(DomainRuleError) as error:
        base_quantity(D("1.0001"), D("0.5"), field="lines[2].quantity")
    assert error.value.code == "BASE_QUANTITY_PRECISION"
    assert error.value.field == "lines[2].quantity"


def test_presentation_price_is_used_as_is() -> None:
    assert sale_unit_price(D("16000.00"), PRESENTATION, D("12")) == D("16000.0000")


def test_base_unit_price_with_presentation_is_multiplied_by_the_factor() -> None:
    assert sale_unit_price(D("1500.00"), BASE_UNIT, D("12")) == D("18000.0000")


def test_converted_price_keeps_four_decimals_never_two() -> None:
    """P-04: ROUND_HALF_UP a 4 decimales, consistente con NUMERIC(18,4)."""
    assert sale_unit_price(D("0.33335"), BASE_UNIT, D("3")) == D("1.0001")  # 1.00005 → 1.0001
    assert sale_unit_price(D("1234.5678"), BASE_UNIT, D("0.125")) == D("154.3210")  # 154.320975 → 154.3210
    assert sale_unit_price(D("0.01"), BASE_UNIT, D("0.33333333")) == D("0.0033")


def test_without_presentation_the_factor_is_one() -> None:
    assert sale_unit_price(D("12500.00"), BASE_UNIT, D("1")) == D("12500.0000")


def test_unknown_basis_is_rejected() -> None:
    with pytest.raises(ValueError):
        sale_unit_price(D("1"), "OTHER", D("1"))
