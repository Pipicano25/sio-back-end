"""Contrato del evento: validación, preparación y forma canónica (R-04, R-08)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from sio_audit.event import (
    AuditEvent,
    InvalidAuditEventError,
    canonical_json,
    content_hash,
    from_canonical_dict,
    prepare_event,
    to_canonical_dict,
    validate_event,
)

NOW = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)


def make_event(**changes) -> AuditEvent:
    base = AuditEvent(
        event_id=UUID("5d2c0000-0000-4000-8000-000000000001"),
        company_id=UUID("7c1e0000-0000-4000-8000-000000000002"),
        action="CHANGE_PRICE",
        entity_type="PriceListItem",
        entity_id=UUID("e9a00000-0000-4000-8000-000000000003"),
        result="SUCCESS",
        occurred_at=NOW,
        previous_values={"unit_price": "2000.00"},
        new_values={"unit_price": "2100.00"},
    )
    return replace(base, **changes)


def fields_of(error: InvalidAuditEventError) -> set[str]:
    return {item.field for item in error.errors}


def test_valid_event_passes() -> None:
    assert validate_event(make_event(), now=NOW) == []


@pytest.mark.parametrize("action", ["CREATE", "CHANGE_PRICE", "A", "A" + "B" * 49, "X1_2"])
def test_valid_actions(action: str) -> None:
    assert validate_event(make_event(action=action)) == []


@pytest.mark.parametrize("action", ["create", "Create", "1CREATE", "_X", "A" + "B" * 50, "CHANGE-PRICE", ""])
def test_invalid_actions(action: str) -> None:
    assert {e.field for e in validate_event(make_event(action=action))} == {"action"}


@pytest.mark.parametrize("entity_type", ["PriceListItem", "A", "A" + "b" * 59])
def test_valid_entity_types(entity_type: str) -> None:
    assert validate_event(make_event(entity_type=entity_type)) == []


@pytest.mark.parametrize("entity_type", ["priceListItem", "Price_List", "price_list_items", "A" + "b" * 60, ""])
def test_invalid_entity_types(entity_type: str) -> None:
    assert {e.field for e in validate_event(make_event(entity_type=entity_type))} == {"entity_type"}


@pytest.mark.parametrize("result", ["success", "OK", "", "FAILED"])
def test_invalid_result(result: str) -> None:
    assert {e.field for e in validate_event(make_event(result=result))} == {"result"}


def test_failure_without_reason_is_valid() -> None:
    assert validate_event(make_event(result="FAILURE", reason=None)) == []


def test_texts_are_trimmed_and_limited() -> None:
    prepared = prepare_event(make_event(username_snapshot="  admin.test  ", reason="  motivo "))
    assert prepared.username_snapshot == "admin.test"
    assert prepared.reason == "motivo"

    with pytest.raises(InvalidAuditEventError) as blank:
        prepare_event(make_event(username_snapshot="   "))
    assert fields_of(blank.value) == {"username_snapshot"}

    with pytest.raises(InvalidAuditEventError) as long_name:
        prepare_event(make_event(username_snapshot="u" * 161))
    assert fields_of(long_name.value) == {"username_snapshot"}

    with pytest.raises(InvalidAuditEventError) as long_reason:
        prepare_event(make_event(reason="r" * 2001))
    assert fields_of(long_reason.value) == {"reason"}

    assert prepare_event(make_event(username_snapshot="u" * 160, reason="r" * 2000))


def test_branch_requires_company() -> None:
    errors = validate_event(make_event(company_id=None, branch_id=uuid4()))
    assert {e.field for e in errors} == {"branch_id"}


def test_occurred_at_requires_timezone() -> None:
    errors = validate_event(make_event(occurred_at=datetime(2026, 10, 5, 15, 0)))
    assert {e.field for e in errors} == {"occurred_at"}


def test_occurred_at_future_tolerance() -> None:
    assert validate_event(make_event(occurred_at=NOW + timedelta(seconds=300)), now=NOW) == []
    errors = validate_event(make_event(occurred_at=NOW + timedelta(seconds=301)), now=NOW)
    assert {e.field for e in errors} == {"occurred_at"}
    assert validate_event(make_event(occurred_at=NOW - timedelta(days=400)), now=NOW) == []
    # Sin hora de referencia (emisor) no se aplica el límite.
    assert validate_event(make_event(occurred_at=NOW + timedelta(days=1))) == []


def test_values_must_be_objects() -> None:
    errors = validate_event(make_event(new_values=["a"], previous_values="x"))  # type: ignore[arg-type]
    assert {e.field for e in errors} == {"new_values", "previous_values"}


def test_values_size_limit_is_64_kb() -> None:
    # {"k":"..."} serializado: 8 bytes de estructura + el texto.
    fits = {"k": "x" * (64 * 1024 - 8)}
    too_big = {"k": "x" * (64 * 1024 - 7)}

    assert validate_event(make_event(new_values=fits)) == []
    assert {e.field for e in validate_event(make_event(new_values=too_big))} == {"new_values"}


def test_values_depth_limit_is_ten_levels() -> None:
    ten: dict = {"leaf": 1}
    for _ in range(9):
        ten = {"n": ten}
    eleven = {"n": ten}

    assert validate_event(make_event(new_values=ten)) == []
    assert {e.field for e in validate_event(make_event(new_values=eleven))} == {"new_values"}


def test_size_is_measured_after_redaction() -> None:
    # El secreto grande desaparece al redactar: el evento entra en el límite.
    event = make_event(new_values={"password": "x" * (70 * 1024)})
    prepared = prepare_event(event)
    assert prepared.new_values == {"password": "***"}


def test_duplicate_redacted_paths_rejected() -> None:
    with pytest.raises(InvalidAuditEventError) as error:
        prepare_event(make_event(redacted_paths=("new_values.a", "new_values.a")))
    assert fields_of(error.value) == {"redacted_paths"}


def test_prepare_redacts_and_merges_paths() -> None:
    prepared = prepare_event(
        make_event(new_values={"api_key": "k", "unit_price": "1"}, redacted_paths=("previous_values.x",))
    )
    assert prepared.new_values == {"api_key": "***", "unit_price": "1"}
    assert prepared.redacted_paths == ("new_values.api_key", "previous_values.x")


def test_canonical_form_is_stable() -> None:
    a = make_event(new_values={"b": 1, "a": {"y": 2, "x": 1}})
    b = make_event(
        new_values={"a": {"x": 1, "y": 2}, "b": 1},
        event_id=UUID(str(a.event_id).upper()),
        occurred_at=NOW.astimezone(timezone(timedelta(hours=-5))),
    )

    assert canonical_json(a) == canonical_json(b)
    assert content_hash(a, "svc") == content_hash(b, "svc")


def test_canonical_form_details() -> None:
    data = to_canonical_dict(make_event(redacted_paths=("b", "a")))
    assert data["occurred_at"] == "2026-10-05T15:00:00.000000Z"
    assert data["event_id"] == "5d2c0000-0000-4000-8000-000000000001"
    assert data["redacted_paths"] == ["a", "b"]
    assert data["branch_id"] is None


def test_hash_changes_with_content_or_emitter() -> None:
    event = make_event()
    base = content_hash(event, "svc-a")

    assert len(base) == 64
    assert content_hash(event, "svc-b") != base
    assert content_hash(make_event(new_values={"unit_price": "2200.00"}), "svc-a") != base


def test_round_trip_from_canonical_dict() -> None:
    event = prepare_event(make_event(redacted_paths=("x",), username_snapshot="u"))
    assert from_canonical_dict(to_canonical_dict(event)) == event
