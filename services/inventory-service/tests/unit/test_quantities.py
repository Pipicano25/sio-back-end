"""Cantidades y costos decimales (R-10, FR-018; T007)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from inventory_service.domain.quantities import (
    QuantityError,
    format_decimal,
    normalize_decimal,
    parse_quantity,
    parse_unit_cost,
)


@pytest.mark.parametrize("value", ["10", "10.0", 10, "10.0000", "0010.00"])
def test_equivalent_representations_normalize_equal(value) -> None:
    assert parse_quantity(value) == Decimal("10")
    assert normalize_decimal(parse_quantity(value)) == "10"


def test_four_decimals_accepted_and_formatted() -> None:
    assert parse_quantity("5.5") == Decimal("5.5")
    assert format_decimal(Decimal("5.5")) == "5.5000"
    assert parse_quantity("0.0001") == Decimal("0.0001")


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("0", "QUANTITY_NOT_POSITIVE"),
        ("-1", "QUANTITY_NOT_POSITIVE"),
        ("1.00001", "TOO_MANY_DECIMALS"),
        ("100000000000000", "QUANTITY_OUT_OF_RANGE"),
        ("abc", "INVALID_FORMAT"),
        ("NaN", "INVALID_FORMAT"),
        ("Infinity", "INVALID_FORMAT"),
        (True, "INVALID_FORMAT"),
        (None, "INVALID_FORMAT"),
        ("", "INVALID_FORMAT"),
    ],
)
def test_invalid_quantities(value, code) -> None:
    with pytest.raises(QuantityError) as error:
        parse_quantity(value)
    assert error.value.code == code


def test_largest_quantity_in_numeric_18_4() -> None:
    assert parse_quantity("99999999999999.9999") == Decimal("99999999999999.9999")


def test_unit_cost_accepts_zero_and_rejects_negative() -> None:
    assert parse_unit_cost("0") == Decimal("0")
    assert parse_unit_cost("1500.25") == Decimal("1500.25")
    with pytest.raises(QuantityError) as error:
        parse_unit_cost("-0.01")
    assert error.value.code == "UNIT_COST_NEGATIVE"
    with pytest.raises(QuantityError) as error:
        parse_unit_cost("1.12345")
    assert error.value.code == "TOO_MANY_DECIMALS"
