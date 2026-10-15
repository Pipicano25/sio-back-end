"""Conversión a unidad base y costo para Inventory (DS-04; research.md R-07; T007)."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from purchase_service.domain.conversion import base_quantity, check_base_unit_cost, inventory_unit_cost
from purchase_service.domain.money import DomainRuleError, line_amounts


def test_base_quantity_with_presentation_factor() -> None:
    assert base_quantity(D("2"), D("12")) == D("24.0000")
    assert base_quantity(D("1.5"), D("0.5")) == D("0.7500")


def test_base_quantity_exact_with_more_than_four_decimals_is_rejected() -> None:
    with pytest.raises(DomainRuleError) as error:
        base_quantity(D("1.0001"), D("0.5"), field="lines[2].quantity")
    assert error.value.code == "BASE_QUANTITY_PRECISION"
    assert error.value.field == "lines[2].quantity"


def test_base_quantity_trailing_zeros_count_as_exact() -> None:
    assert base_quantity(D("1.2500"), D("1.00000000")) == D("1.2500")


def test_inventory_unit_cost_excludes_taxes() -> None:
    # Caja x12 a 120 000 con IVA 45 600: el costo por unidad base ignora el impuesto.
    amounts = line_amounts(D("2"), D("120000"), D("0"), D("45600"))
    assert inventory_unit_cost(amounts.subtotal, amounts.discount_amount, base_quantity(D("2"), D("12"))) == D(
        "10000.0000"
    )


def test_inventory_unit_cost_subtracts_discount_and_rounds_half_up() -> None:
    # (100.00 − 0.01) / 3 = 33.33 → 33.3300
    assert inventory_unit_cost(D("100.00"), D("0.01"), D("3")) == D("33.3300")
    # 10.00 / 3 = 3.33333… → 3.3333
    assert inventory_unit_cost(D("10.00"), D("0"), D("3")) == D("3.3333")
    # 0.20 / 3 = 0.066666… → 0.0667
    assert inventory_unit_cost(D("0.20"), D("0"), D("3")) == D("0.0667")


def test_base_unit_cost_must_be_positive_after_rounding() -> None:
    """Spec 020 (FR-020-12, RC-MVP-5): 0,01 entre 1 000 unidades base redondea a 0,0000 → rechazado."""
    with pytest.raises(DomainRuleError) as error:
        check_base_unit_cost(D("0.01"), D("0"), D("1000"), field="lines[0].unit_cost")
    assert (error.value.code, error.value.field) == ("BASE_UNIT_COST_NOT_POSITIVE", "lines[0].unit_cost")


def test_base_unit_cost_is_the_inventory_cost_when_positive() -> None:
    # 3 cajas x 10 a 12 000: (36 000 − 0) / 30 = 1 200 por unidad base.
    assert check_base_unit_cost(D("36000.00"), D("0"), D("30")) == D("1200.0000")
    # El menor costo representable: 0,0001 por unidad base.
    assert check_base_unit_cost(D("0.01"), D("0"), D("100")) == D("0.0001")
