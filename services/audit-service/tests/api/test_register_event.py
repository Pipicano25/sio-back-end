"""Registro de un evento (US1; FR-010 a FR-021; RC-03, RC-05; T024)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import CREATE, EMITTER, event_body, service_sub

URL = "/api/v1/audit-events"


def _count(test_engine) -> int:
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one()


def test_created_with_identity_from_token(emitter, test_engine) -> None:
    body = event_body(username_snapshot="admin.test", reason=None)
    response = emitter.post(URL, json=body)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["event_id"] == body["event_id"]
    assert data["source_service"] == EMITTER
    assert data["created_by"] == service_sub(EMITTER)
    assert data["recorded_at"]
    assert data["redacted_paths"] == []
    assert "content_hash" not in data
    assert _count(test_engine) == 1


def test_identical_resend_is_idempotent(emitter, test_engine) -> None:
    body = event_body(new_values={"b": 1, "a": {"y": 2, "x": 1}})
    first = emitter.post(URL, json=body)

    reordered = {**body, "new_values": {"a": {"x": 1, "y": 2}, "b": 1}, "event_id": body["event_id"].upper()}
    second = emitter.post(URL, json=reordered)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert _count(test_engine) == 1


def test_same_event_id_other_content_conflicts(emitter, test_engine) -> None:
    body = event_body()
    original = emitter.post(URL, json=body).json()

    response = emitter.post(URL, json={**body, "new_values": {"unit_price": "9999.00"}})

    assert response.status_code == 409
    assert response.json()["code"] == "AUDIT.EVENT_ID_CONFLICT"
    assert "9999" not in response.text and "2100" not in response.text
    with test_engine.connect() as connection:
        stored = connection.execute(
            text("SELECT new_values FROM audit_events WHERE id = :id"), {"id": original["id"]}
        ).scalar_one()
    assert stored == {"unit_price": "2100.00"}


def test_same_event_id_from_other_emitter_conflicts(emitter, as_token, service_token) -> None:
    body = event_body()
    assert emitter.post(URL, json=body).status_code == 201

    other = as_token(service_token(CREATE, client_id="otro-emisor"))
    assert other.post(URL, json=body).status_code == 409


@pytest.mark.parametrize("field", ["id", "source_service", "recorded_at", "created_by", "desconocido"])
def test_fields_set_by_audit_are_rejected(emitter, field: str) -> None:
    response = emitter.post(URL, json=event_body(**{field: "x"}))
    assert response.status_code == 422
    assert {error["field"] for error in response.json()["errors"]} == {field}


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"action": "change_price"}, "action"),
        ({"action": "A" * 51}, "action"),
        ({"entity_type": "price_list_item"}, "entity_type"),
        ({"result": "OK"}, "result"),
        ({"username_snapshot": "u" * 161}, "username_snapshot"),
        ({"username_snapshot": "   "}, "username_snapshot"),
        ({"reason": "r" * 2001}, "reason"),
        ({"company_id": None, "branch_id": str(uuid4())}, "branch_id"),
        ({"occurred_at": "2026-10-05T10:00:00"}, "occurred_at"),
        ({"new_values": ["x"]}, "new_values"),
        ({"new_values": {"k": "x" * (64 * 1024)}}, "new_values"),
        ({"redacted_paths": ["a", "a"]}, "redacted_paths"),
        ({"event_id": "no-es-uuid"}, "event_id"),
        ({"action": ...}, "action"),
        ({"occurred_at": ...}, "occurred_at"),
    ],
)
def test_validation_errors(emitter, test_engine, changes, field: str) -> None:
    response = emitter.post(URL, json=event_body(**changes))

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "AUDIT.VALIDATION_ERROR"
    assert field in {error["field"] for error in body["errors"]}
    assert _count(test_engine) == 0


def test_occurred_at_future_tolerance(emitter) -> None:
    now = datetime.now(UTC)
    ok = emitter.post(URL, json=event_body(occurred_at=(now + timedelta(seconds=240)).isoformat()))
    late = emitter.post(URL, json=event_body(occurred_at=(now + timedelta(seconds=400)).isoformat()))
    old = emitter.post(URL, json=event_body(occurred_at=(now - timedelta(days=500)).isoformat()))

    assert ok.status_code == 201
    assert late.status_code == 422
    assert old.status_code == 201


def test_platform_event_without_company(emitter) -> None:
    response = emitter.post(URL, json=event_body(company_id=None, entity_type="GlobalProduct"))
    assert response.status_code == 201
    assert response.json()["company_id"] is None


def test_failure_without_reason_is_accepted(emitter, test_engine) -> None:
    """FR-015: `reason` es opcional también con `FAILURE`."""
    response = emitter.post(URL, json=event_body(result="FAILURE", reason=None, new_values=None))

    assert response.status_code == 201, response.text
    with test_engine.connect() as connection:
        row = connection.execute(
            text("SELECT result, reason FROM audit_events WHERE id = :id"), {"id": response.json()["id"]}
        ).one()
    assert row == ("FAILURE", None)


def test_texts_are_trimmed(emitter) -> None:
    response = emitter.post(URL, json=event_body(username_snapshot="  admin.test ", reason=" motivo  "))
    assert response.json()["username_snapshot"] == "admin.test"
    assert response.json()["reason"] == "motivo"


def test_malformed_json_is_400(emitter) -> None:
    response = emitter.post(URL, content=b"{no es json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["code"] == "AUDIT.MALFORMED_BODY"


def test_validation_errors_never_echo_values(emitter) -> None:
    response = emitter.post(URL, json=event_body(action="secreto-visible", new_values=["valor-sensible"]))
    assert response.status_code == 422
    assert "valor-sensible" not in response.text
    assert "secreto-visible" not in response.text
