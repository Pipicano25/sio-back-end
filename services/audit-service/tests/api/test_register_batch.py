"""Lotes atómicos de 1 a 100 eventos (US2; DS-02, RC-06; T033)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import event_body

URL = "/api/v1/audit-events/batch"


def _count(test_engine) -> int:
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one()


def test_hundred_valid_events(emitter, test_engine) -> None:
    events = [event_body() for _ in range(100)]
    response = emitter.post(URL, json={"events": events})

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["index"] for item in items] == list(range(100))
    assert [item["event_id"] for item in items] == [event["event_id"] for event in events]
    assert {item["outcome"] for item in items} == {"CREATED"}
    assert _count(test_engine) == 100

    again = emitter.post(URL, json={"events": events})
    assert {item["outcome"] for item in again.json()["items"]} == {"ALREADY_EXISTS"}
    assert [item["id"] for item in again.json()["items"]] == [item["id"] for item in items]
    assert _count(test_engine) == 100


def test_mix_of_new_and_existing(emitter, test_engine) -> None:
    existing = event_body()
    emitter.post("/api/v1/audit-events", json=existing)

    response = emitter.post(URL, json={"events": [existing, event_body()]})

    assert [item["outcome"] for item in response.json()["items"]] == ["ALREADY_EXISTS", "CREATED"]
    assert _count(test_engine) == 2


@pytest.mark.parametrize("size", [0, 101])
def test_size_limits(emitter, test_engine, size: int) -> None:
    response = emitter.post(URL, json={"events": [event_body() for _ in range(size)]})

    assert response.status_code == 422
    assert {error["field"] for error in response.json()["errors"]} == {"events"}
    assert _count(test_engine) == 0


def test_repeated_event_id_in_batch(emitter, test_engine) -> None:
    event = event_body()
    response = emitter.post(URL, json={"events": [event, event_body(), dict(event)]})

    assert response.status_code == 422
    assert {error["field"] for error in response.json()["errors"]} == {"events[2].event_id"}
    assert _count(test_engine) == 0


def test_one_invalid_event_saves_nothing(emitter, test_engine) -> None:
    events = [event_body(), event_body(action="no valido"), event_body()]
    response = emitter.post(URL, json={"events": events})

    assert response.status_code == 422
    assert "events[1].action" in {error["field"] for error in response.json()["errors"]}
    assert _count(test_engine) == 0


def test_one_conflict_saves_nothing(emitter, test_engine) -> None:
    existing = event_body()
    emitter.post("/api/v1/audit-events", json=existing)

    conflicting = {**existing, "new_values": {"unit_price": "1.00"}}
    events = [event_body(), conflicting, event_body()]
    response = emitter.post(URL, json={"events": events})

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "AUDIT.EVENT_ID_CONFLICT"
    assert body["conflicts"] == [{"index": 1, "event_id": existing["event_id"]}]
    assert _count(test_engine) == 1


def test_unknown_field_in_batch_item(emitter) -> None:
    response = emitter.post(URL, json={"events": [event_body(source_service="x")]})
    assert response.status_code == 422
    assert {error["field"] for error in response.json()["errors"]} == {"events[0].source_service"}


def test_unknown_top_level_field(emitter) -> None:
    response = emitter.post(URL, json={"events": [event_body()], "extra": str(uuid4())})
    assert response.status_code == 422
