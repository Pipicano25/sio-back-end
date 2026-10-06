"""PostgreSQL no disponible → `503` controlado y recuperación sin reinicio (Principio X; T014).

Se simula la caída apuntando el motor y la fábrica de sesiones de la misma instancia
`app.state.database` a un puerto cerrado; al restaurarlos, el mismo proceso vuelve a
responder sin reiniciarse.
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from audit_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.conftest import PLATFORM_READ, READ, event_body

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")


@contextmanager
def database_down(app):
    database = app.state.database
    original_engine, original_sessions = database.engine, database.session_factory
    down = create_engine(UNREACHABLE, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    database.engine = down
    database.session_factory = sessionmaker(bind=down, class_=Session, autoflush=False, expire_on_commit=False)
    try:
        yield
    finally:
        database.engine, database.session_factory = original_engine, original_sessions
        down.dispose()


def _assert_controlled_503(response) -> None:
    assert response.status_code == 503, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "AUDIT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


@pytest.fixture
def reader(as_token, make_token, company):
    from tests.conftest import user_sub

    return as_token(make_token(READ, PLATFORM_READ, sub=user_sub("admin.test"), preferred_username="admin.test"))


def test_every_database_route_returns_503_and_recovers(app, emitter, reader, company, as_token) -> None:
    created = emitter.post("/api/v1/audit-events", json=event_body(company_id=str(company)))
    assert created.status_code == 201

    calls = [
        lambda: emitter.post("/api/v1/audit-events", json=event_body()),
        lambda: emitter.post("/api/v1/audit-events/batch", json={"events": [event_body()]}),
        lambda: reader.get(f"/api/v1/companies/{company}/audit-events"),
        lambda: reader.get(f"/api/v1/companies/{company}/audit-events/{created.json()['id']}"),
        lambda: reader.get(f"/api/v1/companies/{company}/entity-history/PriceListItem/{uuid4()}"),
        lambda: reader.get("/api/v1/platform-audit-events"),
        lambda: reader.get(f"/api/v1/platform-audit-events/{uuid4()}"),
        lambda: reader.get(f"/api/v1/platform-entity-history/GlobalProduct/{uuid4()}"),
    ]

    with database_down(app):
        for call in calls:
            _assert_controlled_503(call())

        assert as_token(None).get("/health/live").status_code == 200
        ready = as_token(None).get("/health/ready")
        assert ready.status_code == 503
        assert ready.json() == {"status": "not_ready"}

    assert as_token(None).get("/health/ready").status_code == 200
    assert reader.get(f"/api/v1/companies/{company}/audit-events").status_code == 200
    assert emitter.post("/api/v1/audit-events", json=event_body()).status_code == 201
