"""Lista cerrada de monedas admitidas y sus decimales ISO 4217 (FR-014a, DS-09, R-09).

Es una constante del dominio: no depende del entorno (no es variable de
entorno) ni es un catálogo administrable (no es tabla; ningún servicio de SIO es
propietario de las monedas). Se cambia solo con un cambio de código revisado y
la prueba `tests/unit/test_currency.py` fija su contenido exacto.
"""

from __future__ import annotations

from decimal import Decimal
from types import MappingProxyType

from commercial_relationship_service.domain.errors import (
    CurrencyNotSupportedError,
    PriceScaleNotAllowedError,
)

_INTERNATIONAL = {
    "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "CNY": 2, "CHF": 2, "CAD": 2, "AUD": 2,
    "NZD": 2, "HKD": 2, "SGD": 2, "SEK": 2, "NOK": 2, "DKK": 2, "KRW": 0, "INR": 2,
}

# Ecuador, El Salvador y Puerto Rico usan USD (incluido arriba).
_LATIN_AMERICA = {
    "ARS": 2, "BOB": 2, "BRL": 2, "CLP": 0, "COP": 2, "CRC": 2, "CUP": 2, "DOP": 2,
    "GTQ": 2, "HNL": 2, "HTG": 2, "MXN": 2, "NIO": 2, "PAB": 2, "PEN": 2, "PYG": 0,
    "UYU": 2, "VES": 2, "VED": 2, "BZD": 2, "GYD": 2, "SRD": 2,
}

CURRENCY_DECIMALS = MappingProxyType({**_INTERNATIONAL, **_LATIN_AMERICA})
"""Código ISO 4217 → decimales oficiales (unidad menor)."""


def validate_currency(code: str, *, field: str = "currency_code") -> str:
    """Normaliza a mayúsculas y exige que la moneda esté en la lista cerrada.

    Raises:
        CurrencyNotSupportedError: Si el código no está en `CURRENCY_DECIMALS`.
    """
    normalized = (code or "").strip().upper()

    if normalized not in CURRENCY_DECIMALS:
        raise CurrencyNotSupportedError(field=field)

    return normalized


def validate_price_scale(price: Decimal, currency_code: str, *, field: str = "unit_price") -> None:
    """Exige que el precio no tenga más decimales que los de su moneda (sin redondear).

    Raises:
        PriceScaleNotAllowedError: Si el precio excede los decimales de la moneda.
    """
    allowed = CURRENCY_DECIMALS[currency_code]
    exponent = price.normalize().as_tuple().exponent

    if isinstance(exponent, int) and -exponent > allowed:
        raise PriceScaleNotAllowedError(
            f"El precio admite como máximo {allowed} decimales en {currency_code}.",
            field=field,
        )


def currency_places(currency_code: str) -> int:
    """Decimales oficiales de la moneda (para validar y presentar importes, R-11)."""
    return CURRENCY_DECIMALS[currency_code]


def validate_amount_scale(amount: Decimal, currency_code: str, *, field: str) -> None:
    """`unit_price` y `credit_limit`: a lo sumo los decimales de su moneda (DS-10).

    Regla FR-014a de la 007 (hoy aplicada a los importes, sin redondeo silencioso).

    Raises:
        PriceScaleNotAllowedError: Si el importe excede los decimales de la moneda.
    """
    validate_price_scale(amount, currency_code, field=field)


def format_amount(amount: Decimal, places: int) -> str:
    """Importe como cadena decimal con la escala indicada (R-11; nunca número JSON)."""
    quantum = Decimal(1).scaleb(-places)
    return format(Decimal(amount).quantize(quantum), "f")
