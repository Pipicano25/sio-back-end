"""PostgreSQL no disponible → `503` controlado y recuperación sin intervención (feature 009).

Se simula la caída apuntando el motor y la fábrica de sesiones de la **misma** instancia
`app.state.database` (la que usan las sesiones por solicitud y `/health/ready`) a un puerto cerrado; al
restaurarlos, el mismo proceso vuelve a responder sin reiniciarse.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

import psycopg.errors as pg
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from operational_context_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.conftest import company_payload, random_uuid

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
COMPANIES = "/api/v1/companies"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")


@pytest.fixture
def company(create_company) -> dict:
    """Empresa activa creada con la base disponible."""
    return create_company()


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


@contextmanager
def failing_statements(app, orig: Exception):
    """Cada sentencia SQL falla con un `OperationalError` cuyo origen es `orig` (base disponible)."""

    def fail(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, orig)

    engine = app.state.database.engine
    event.listen(engine, "before_cursor_execute", fail)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", fail)


def _timed(request, *args, **kwargs):
    """Ejecuta una llamada y devuelve la respuesta con su duración (SC-002 es por respuesta)."""
    started = time.monotonic()
    response = request(*args, **kwargs)
    return response, time.monotonic() - started


def _assert_controlled_503(response) -> None:
    assert response.status_code == 503, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert body["status"] == 503 and body["trace_id"]
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_endpoints_respond_controlled_503_while_database_is_down(app, api, company, fake_organizations) -> None:
    new_company = company_payload(fake_organizations.add())

    with database_down(app):
        results = [
            _timed(api.get, COMPANIES),
            _timed(api.get, f"{COMPANIES}/{company['id']}"),
            _timed(api.post, COMPANIES, json=new_company),
            _timed(api.post, f"{COMPANIES}/{company['id']}/deactivate", json={"version": company["version"]}),
            _timed(api.get, f"{COMPANIES}/{company['id']}/branches"),
            _timed(api.get, f"/api/v1/branches/{random_uuid()}"),
            _timed(api.get, f"/api/v1/application-users/{random_uuid()}"),
        ]

    for response, elapsed in results:
        _assert_controlled_503(response)
        assert elapsed < 15  # tiempo acotado por respuesta (conexión con tiempo de espera)


def test_health_while_database_is_down(app, anonymous) -> None:
    with database_down(app):
        assert anonymous.get("/health/live").status_code == 200
        assert anonymous.get("/health/ready").status_code == 503


def test_service_recovers_without_restart_and_leaves_no_partial_write(
    app, api, anonymous, company, fake_organizations
) -> None:
    new_company = company_payload(fake_organizations.add())

    with database_down(app):
        _assert_controlled_503(api.post(COMPANIES, json=new_company))

    assert anonymous.get("/health/ready").status_code == 200
    assert api.get(f"{COMPANIES}/{company['id']}").status_code == 200
    assert api.get(COMPANIES).json()["total_records"] == 1  # el alta interrumpida no quedó guardada
    assert api.post(COMPANIES, json=new_company).status_code == 201
    assert api.get(COMPANIES).json()["total_records"] == 2


@pytest.mark.parametrize(
    "orig",
    [pg.DeadlockDetected("deadlock detected"), pg.SerializationFailure("could not serialize access")],
    ids=["40P01", "40001"],
)
def test_other_postgresql_errors_keep_internal_error(app, api, company, orig) -> None:
    with failing_statements(app, orig):
        response = api.get(f"{COMPANIES}/{company['id']}")

    assert response.status_code == 500
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.INTERNAL_ERROR"
