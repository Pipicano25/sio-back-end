"""Período y formato del número oficial (FR-032, FR-033; research.md R-03; T008)."""

from __future__ import annotations

from datetime import date

import pytest

from purchase_service.domain.numbering import (
    exceeds_maximum,
    format_number,
    max_number_text_length,
    next_value,
    period_key,
)


@pytest.mark.parametrize(
    ("policy", "expected"),
    [("NEVER", ""), ("YEARLY", "2026"), ("MONTHLY", "202610")],
)
def test_period_key_from_operation_date(policy: str, expected: str) -> None:
    assert period_key(policy, date(2026, 10, 6)) == expected


def test_monthly_period_of_january_is_zero_padded() -> None:
    assert period_key("MONTHLY", date(2027, 1, 31)) == "202701"


def test_unknown_policy() -> None:
    with pytest.raises(ValueError):
        period_key("WEEKLY", date(2026, 1, 1))


@pytest.mark.parametrize(
    ("period", "value", "expected"),
    [("", 1, "CP-000001"), ("2026", 1, "CP-2026-000001"), ("202610", 3, "CP-202610-000003")],
)
def test_format_number(period: str, value: int, expected: str) -> None:
    assert format_number("CP", "-", period, value, 6) == expected


def test_format_number_with_empty_separator_and_longer_value() -> None:
    assert format_number("CP", "", "202610", 1234567, 6) == "CP2026101234567"


def test_next_value_starts_at_initial_number() -> None:
    assert next_value(None, 100) == 100
    assert next_value(100, 1) == 101


def test_exceeds_maximum() -> None:
    assert exceeds_maximum(11, 10, 6)
    assert not exceeds_maximum(10, 10, 6)
    assert not exceeds_maximum(10**6 - 1, None, 6)
    assert exceeds_maximum(10**6, None, 6)  # ya no cabe en 6 dígitos


def test_max_number_text_length() -> None:
    assert max_number_text_length("CP", "-", 6) == 2 + 2 + 6 + 6
    assert max_number_text_length("A" * 20, "-", 18) <= 80
