"""Vigencias de condiciones, listas y precios (T005; FR-034, FR-052, FR-054, FR-054a; R-06; I2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from commercial_relationship_service.domain.errors import (
    PriceChangeOutOfPeriodError,
    ValidityInvalidError,
)
from commercial_relationship_service.domain.validity import (
    contains,
    is_in_effect,
    validate_change_effective,
    validate_closing,
    validate_period,
)

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)


def test_period_requires_end_after_start():
    validate_period(NOW, NOW + DAY)
    validate_period(NOW, None)
    validate_period(None, NOW)

    with pytest.raises(ValidityInvalidError):
        validate_period(NOW, NOW)

    with pytest.raises(ValidityInvalidError):
        validate_period(NOW, NOW - DAY)


def test_contains_is_half_open_and_open_ended():
    assert contains(NOW, NOW + DAY, NOW)
    assert not contains(NOW, NOW + DAY, NOW + DAY)
    assert contains(NOW, None, NOW + 1000 * DAY)
    assert contains(None, None, NOW)
    assert not contains(NOW + DAY, None, NOW)


def test_in_effect_from_valid_from():
    assert is_in_effect(NOW, NOW)
    assert is_in_effect(NOW - DAY, NOW)
    assert not is_in_effect(NOW + DAY, NOW)


def test_closing_accepts_future_end_brought_forward_or_postponed():
    validate_closing(NOW - DAY, NOW + DAY, NOW)  # adelantar o fijar
    validate_closing(NOW - DAY, NOW + 30 * DAY, NOW)  # posponer (I2)
    validate_closing(NOW - DAY, None, NOW)  # sin fin

    with pytest.raises(ValidityInvalidError):
        validate_closing(NOW - DAY, NOW, NOW)

    with pytest.raises(ValidityInvalidError):
        validate_closing(NOW - DAY, NOW - DAY / 2, NOW)


def test_change_effective_limits():
    validate_change_effective(NOW, now=NOW, valid_from=NOW - DAY, valid_to=None)
    validate_change_effective(NOW + DAY, now=NOW, valid_from=NOW - DAY, valid_to=NOW + 2 * DAY)

    for effective, valid_from, valid_to in (
        (NOW - DAY / 2, NOW - DAY, None),  # en el pasado
        (NOW, NOW, None),  # no posterior al inicio
        (NOW + 2 * DAY, NOW - DAY, NOW + 2 * DAY),  # no anterior al fin
    ):
        with pytest.raises(PriceChangeOutOfPeriodError):
            validate_change_effective(effective, now=NOW, valid_from=valid_from, valid_to=valid_to)
