"""Inmutabilidad en la base (US5; RC-02, SC-003; T048)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.conftest import event_body


@pytest.fixture
def stored(emitter, test_engine) -> dict:
    response = emitter.post("/api/v1/audit-events", json=event_body())
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_events SET reason = 'cambiado' WHERE id = :id",
        "UPDATE audit_events SET new_values = '{}'::jsonb",
        "DELETE FROM audit_events WHERE id = :id",
        "DELETE FROM audit_events",
        "TRUNCATE TABLE audit_events",
    ],
)
def test_direct_changes_are_rejected(test_engine, stored, statement: str) -> None:
    with pytest.raises(DBAPIError) as error:
        with test_engine.begin() as connection:
            connection.execute(text(statement), {"id": stored["id"]})
    assert "inmutable" in str(error.value)

    with test_engine.connect() as connection:
        row = connection.execute(
            text("SELECT reason, new_values FROM audit_events WHERE id = :id"), {"id": stored["id"]}
        ).one()
    assert row == (None, {"unit_price": "2100.00"})
