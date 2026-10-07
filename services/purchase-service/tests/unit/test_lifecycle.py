"""Hitos logísticos (FR-035 a FR-038, DS-08; research.md R-10; T009)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from uuid import uuid4

import pytest

from purchase_service.domain.lifecycle import (
    EventInFutureError,
    EventNotAllowedError,
    EventOrderError,
    EventRecord,
    check_new_event,
    current_events,
    intervals,
)

NOW = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)


def event(event_type: str, hours_ago: float, created_minutes_ago: float = 0) -> EventRecord:
    return EventRecord(
        id=uuid4(),
        event_type=event_type,
        occurred_at=NOW - timedelta(hours=hours_ago),
        created_at=NOW - timedelta(minutes=created_minutes_ago),
    )


def test_events_in_order_are_accepted() -> None:
    existing = [event("ORDERED", 48), event("ARRIVED", 10)]
    check_new_event("CONFIRMED", "RECEIVED", NOW - timedelta(hours=5), existing, NOW)
    check_new_event("DRAFT", "SUPPLIER_DISPATCHED", NOW - timedelta(hours=20), existing, NOW)


def test_event_before_a_previous_milestone_is_rejected() -> None:
    ordered = event("ORDERED", 10)
    with pytest.raises(EventOrderError) as error:
        check_new_event("DRAFT", "ARRIVED", NOW - timedelta(hours=11), [ordered], NOW)
    assert error.value.conflicting_type == "ORDERED"
    assert error.value.conflicting_id == ordered.id


def test_event_after_a_following_milestone_is_rejected() -> None:
    arrived = event("ARRIVED", 10)
    with pytest.raises(EventOrderError) as error:
        check_new_event("DRAFT", "ORDERED", NOW - timedelta(hours=9), [arrived], NOW)
    assert error.value.conflicting_type == "ARRIVED"


def test_equal_times_are_allowed() -> None:
    check_new_event("CONFIRMED", "RECEIVED", NOW - timedelta(hours=10), [event("ARRIVED", 10)], NOW)


def test_future_tolerance_of_five_minutes() -> None:
    check_new_event("DRAFT", "ORDERED", NOW + timedelta(minutes=5), [], NOW)
    with pytest.raises(EventInFutureError):
        check_new_event("DRAFT", "ORDERED", NOW + timedelta(minutes=5, seconds=1), [], NOW)


@pytest.mark.parametrize("event_type", ["RECEIVED", "AVAILABLE_FOR_SALE"])
def test_reception_milestones_need_confirmed(event_type: str) -> None:
    with pytest.raises(EventNotAllowedError):
        check_new_event("DRAFT", event_type, NOW, [], NOW)


@pytest.mark.parametrize("event_type", ["ORDERED", "SUPPLIER_DISPATCHED", "ARRIVED", "RECEIVED"])
def test_cancelled_admits_no_milestone(event_type: str) -> None:
    with pytest.raises(EventNotAllowedError):
        check_new_event("CANCELLED", event_type, NOW, [], NOW)


def test_correction_of_the_same_type_replaces_the_current_one() -> None:
    wrong = event("ORDERED", 2, created_minutes_ago=30)
    arrived = event("ARRIVED", 1, created_minutes_ago=20)
    # Corregir ORDERED a una hora anterior a ARRIVED es válido aunque el ORDERED erróneo sea posterior.
    check_new_event("DRAFT", "ORDERED", NOW - timedelta(hours=3), [wrong, arrived], NOW)
    corrected = event("ORDERED", 3, created_minutes_ago=0)
    current = current_events([wrong, arrived, corrected])
    assert current["ORDERED"] is corrected


def test_validation_uses_current_events_only() -> None:
    old_arrived = event("ARRIVED", 20, created_minutes_ago=60)
    new_arrived = event("ARRIVED", 5, created_minutes_ago=10)
    # RECEIVED a las −10 h es anterior al ARRIVED vigente (−5 h): se rechaza aunque el antiguo era −20 h.
    with pytest.raises(EventOrderError):
        check_new_event("CONFIRMED", "RECEIVED", NOW - timedelta(hours=10), [old_arrived, new_arrived], NOW)


def test_intervals_and_total_lead_time() -> None:
    events = [event("ORDERED", 50), event("ARRIVED", 10), event("RECEIVED", 8.5), event("AVAILABLE_FOR_SALE", 2)]
    result, total = intervals(events)
    assert [(item.from_type, item.to_type, item.hours) for item in result] == [
        ("ORDERED", "ARRIVED", D("40.00")),
        ("ARRIVED", "RECEIVED", D("1.50")),
        ("RECEIVED", "AVAILABLE_FOR_SALE", D("6.50")),
    ]
    assert total == D("48.00")


def test_total_lead_time_needs_both_ends() -> None:
    assert intervals([event("ORDERED", 5)]) == ([], None)
