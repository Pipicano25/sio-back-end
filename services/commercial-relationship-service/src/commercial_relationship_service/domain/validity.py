"""Vigencias `[valid_from, valid_to)` de condiciones, listas y precios (FR-034, FR-052, FR-054, R-06).

"En vigencia" se evalúa siempre con un instante de referencia que la capa de
aplicación toma de la base de datos (`now()` de la transacción), nunca del
cliente. `valid_to` nulo significa sin fin; en listas, `valid_from` nulo
significa sin inicio.
"""

from __future__ import annotations

from datetime import datetime

from commercial_relationship_service.domain.errors import (
    PriceChangeOutOfPeriodError,
    ValidityInvalidError,
)


def validate_period(valid_from: datetime | None, valid_to: datetime | None) -> None:
    """Exige `valid_to > valid_from` cuando ambos existen.

    Raises:
        ValidityInvalidError: Con el campo `valid_to`.
    """
    if valid_from is not None and valid_to is not None and valid_to <= valid_from:
        raise ValidityInvalidError(field="valid_to")


def contains(valid_from: datetime | None, valid_to: datetime | None, at: datetime) -> bool:
    """Indica si el instante `at` está dentro de `[valid_from, valid_to)`."""
    return (valid_from is None or valid_from <= at) and (valid_to is None or at < valid_to)


def is_in_effect(valid_from: datetime, now: datetime) -> bool:
    """Un precio está en vigencia (no modificable) desde que `valid_from <= now`."""
    return valid_from <= now


def validate_closing(valid_from: datetime, valid_to: datetime | None, now: datetime) -> None:
    """`valid_to` de un precio en vigencia: futuro y posterior a `valid_from` (FR-054).

    Puede adelantarse o posponerse (I2); `None` (sin fin) también es un
    aplazamiento. El solapamiento lo rechaza la base (`PRICE_PERIOD_OVERLAP`).

    Raises:
        ValidityInvalidError: Si `valid_to` no es futuro o no supera a `valid_from`.
    """
    if valid_to is None:
        return

    if valid_to <= now or valid_to <= valid_from:
        raise ValidityInvalidError(
            "Para cerrar un precio en vigencia, el fin de la vigencia debe ser futuro.",
            field="valid_to",
        )


def validate_change_effective(
    effective_from: datetime,
    *,
    now: datetime,
    valid_from: datetime,
    valid_to: datetime | None,
) -> None:
    """Instante de efecto de `change-price` (FR-054a, R-06).

    Debe ser `>= now`, `> valid_from` y `< valid_to` (si existe).

    Raises:
        PriceChangeOutOfPeriodError: Si queda fuera de esos límites.
    """
    if effective_from < now or effective_from <= valid_from:
        raise PriceChangeOutOfPeriodError(field="effective_from")

    if valid_to is not None and effective_from >= valid_to:
        raise PriceChangeOutOfPeriodError(field="effective_from")
