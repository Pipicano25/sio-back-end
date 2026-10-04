"""Lista cerrada de monedas y decimales (FR-014, FR-014a, R-09, R-10, RC-07)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from commercial_relationship_service.domain.currency import (
    CURRENCY_DECIMALS,
    validate_currency,
    validate_price_scale,
)
from commercial_relationship_service.domain.errors import (
    CurrencyNotSupportedError,
    PriceScaleNotAllowedError,
)

EXPECTED = {
    "USD", "EUR", "GBP", "JPY", "CNY", "CHF", "CAD", "AUD", "NZD", "HKD", "SGD", "SEK", "NOK",
    "DKK", "KRW", "INR", "ARS", "BOB", "BRL", "CLP", "COP", "CRC", "CUP", "DOP", "GTQ", "HNL",
    "HTG", "MXN", "NIO", "PAB", "PEN", "PYG", "UYU", "VES", "VED", "BZD", "GYD", "SRD",
}
ZERO_DECIMALS = {"CLP", "PYG", "JPY", "KRW"}


def test_list_is_exactly_fr_014a():
    assert set(CURRENCY_DECIMALS) == EXPECTED
    assert len(CURRENCY_DECIMALS) == 38


def test_minor_units():
    for code, decimals in CURRENCY_DECIMALS.items():
        assert decimals == (0 if code in ZERO_DECIMALS else 2), code


def test_list_is_immutable():
    with pytest.raises(TypeError):
        CURRENCY_DECIMALS["ZAR"] = 2  # type: ignore[index]


def test_normalizes_to_uppercase():
    assert validate_currency("cop") == "COP"
    assert validate_currency(" usd ") == "USD"


@pytest.mark.parametrize("code", ["XYZ", "ZAR", "", "CO", "COPX"])
def test_rejects_codes_outside_the_list(code):
    with pytest.raises(CurrencyNotSupportedError) as error:
        validate_currency(code)
    assert error.value.field == "currency_code"


@pytest.mark.parametrize(
    ("price", "currency"),
    [("1500", "CLP"), ("1500.00", "CLP"), ("10.55", "COP"), ("10.5", "COP"), ("0", "JPY")],
)
def test_accepts_price_scale(price, currency):
    validate_price_scale(Decimal(price), currency)


@pytest.mark.parametrize(
    ("price", "currency"),
    [("1500.50", "CLP"), ("10.555", "COP"), ("1.1", "KRW"), ("3.001", "USD")],
)
def test_rejects_price_scale(price, currency):
    with pytest.raises(PriceScaleNotAllowedError) as error:
        validate_price_scale(Decimal(price), currency)
    assert error.value.field == "sale_price"
