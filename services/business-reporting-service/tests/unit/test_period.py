"""Período de los reportes (DR-02, DR-09; FR-023-50)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from business_reporting_service.application.exceptions import ValidationFailedError
from business_reporting_service.domain.period import build_period, today_in


def test_inclusive_366_days_is_allowed_and_367_is_not() -> None:
    assert build_period(date(2025, 10, 18), date(2026, 10, 18), today=date(2026, 10, 18), max_days=366).days == 366
    with pytest.raises(ValidationFailedError) as error:
        build_period(date(2025, 10, 16), date(2026, 10, 17), today=date(2026, 10, 18), max_days=366)
    assert error.value.errors[0]["code"] == "PERIOD_TOO_LONG"


def test_reversed_and_future_dates() -> None:
    with pytest.raises(ValidationFailedError) as error:
        build_period(date(2026, 10, 10), date(2026, 10, 1), today=date(2026, 10, 18), max_days=366)
    assert error.value.errors[0]["code"] == "INVALID_DATE_RANGE"
    with pytest.raises(ValidationFailedError) as error:
        build_period(date(2026, 10, 1), date(2026, 10, 19), today=date(2026, 10, 18), max_days=366)
    assert error.value.errors[0]["code"] == "DATE_IN_FUTURE"


def test_branch_instants_use_its_timezone() -> None:
    period = build_period(date(2026, 10, 1), date(2026, 10, 31), today=date(2026, 11, 1), max_days=366)
    start, end = period.instants("America/Bogota")
    assert start.isoformat() == "2026-10-01T00:00:00-05:00" and end.isoformat() == "2026-11-01T00:00:00-05:00"


def test_today_depends_on_the_company_timezone() -> None:
    late_utc = datetime(2026, 10, 19, 3, 0, tzinfo=UTC)  # 22:00 del 18 en Bogotá
    assert today_in("America/Bogota", late_utc) == date(2026, 10, 18)


def test_unknown_timezone_is_422() -> None:
    period = build_period(date(2026, 10, 1), date(2026, 10, 2), today=date(2026, 10, 18), max_days=366)
    with pytest.raises(ValidationFailedError):
        period.instants("Marte/Olympus")
