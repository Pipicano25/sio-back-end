"""Conversión a unidad base y precio de la unidad de venta (DS-03, DS-04, P-04; spec 019; T007)."""

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


def test_presentation_price_keeps_four_decimals() -> None:
    assert sale_unit_price(D("0.33335"), PRESENTATION, D("3")) == D("0.3334")  # ROUND_HALF_UP, sin multiplicar


def test_base_unit_price_is_never_converted_spec_019() -> None:
    """Spec 019: sin precios por unidad base ni conversión por factor; `BASE_UNIT` se rechaza."""
    for factor in (D("12"), D("1")):
        with pytest.raises(ValueError):
            sale_unit_price(D("1500.00"), BASE_UNIT, factor)


def test_unknown_basis_is_rejected() -> None:
    with pytest.raises(ValueError):
        sale_unit_price(D("1"), "OTHER", D("1"))
