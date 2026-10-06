"""Ayudas para preparar eventos de consulta en las pruebas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from tests.conftest import event_body

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def register(emitter, **changes: Any) -> dict[str, Any]:
    response = emitter.post("/api/v1/audit-events", json=event_body(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def at(minutes: int) -> str:
    return (BASE_TIME + timedelta(minutes=minutes)).isoformat()


def company_events(emitter, company: UUID, count: int, **changes: Any) -> list[dict[str, Any]]:
    return [
        register(emitter, company_id=str(company), occurred_at=at(index), **changes)
        for index in range(count)
    ]
