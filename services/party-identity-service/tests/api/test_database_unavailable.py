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

from party_identity_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from tests.conftest import organization_payload, person_payload, rule_payload

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
PERSONS = "/api/v1/person-identities"
ORGANIZATIONS = "/api/v1/organization-identities"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")


@pytest.fixture
def seeded(api) -> dict[str, str]:
    """Reglas CC y NIT, una persona y una organización creadas con la base disponible."""
    assert api.post("/api/v1/identification-type-rules", json=rule_payload()).status_code == 201
    nit = rule_payload(
        party_kind="ORGANIZATION",
        identification_type="TAX_ID",
        sigla="NIT",
        number_pattern="^[A-Z0-9]{4,11}-[0-9]$",
        number_pattern_description="El NIT lleva guion y dígito de verificación.",
        example_value="900123456-7",
        min_age_years=None,
    )
    assert api.post("/api/v1/identification-type-rules", json=nit).status_code == 201
    person = api.post(PERSONS, json=person_payload())
    organization = api.post(ORGANIZATIONS, json=organization_payload())
    assert person.status_code == 201, person.text
    assert organization.status_code == 201, organization.text
    return {"person": person.json()["id"], "organization": organization.json()["id"]}


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
    assert body["code"] == "PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"
    assert body["detail"] == DATABASE_UNAVAILABLE_DETAIL
    assert body["status"] == 503 and body["trace_id"]
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_endpoints_respond_controlled_503_while_database_is_down(app, api, seeded) -> None:
    with database_down(app):
        results = [
            _timed(api.get, PERSONS),
            _timed(api.get, f"{PERSONS}/{seeded['person']}"),
            _timed(api.post, PERSONS, json=person_payload(identification_number="1000000002")),
            _timed(api.post, f"{ORGANIZATIONS}/{seeded['organization']}/deactivate", json={"version": 1}),
            _timed(api.get, "/api/v1/identification-type-rules"),
            _timed(api.get, "/api/v1/global-business-sectors"),
        ]

    for response, elapsed in results:
        _assert_controlled_503(response)
        assert elapsed < 15  # tiempo acotado por respuesta (conexión con tiempo de espera)


def test_health_while_database_is_down(app, anonymous) -> None:
    with database_down(app):
        assert anonymous.get("/health/live").status_code == 200
        assert anonymous.get("/health/ready").status_code == 503


def test_service_recovers_without_restart_and_leaves_no_partial_write(app, api, anonymous, seeded) -> None:
    new_person = person_payload(identification_number="1000000003")

    with database_down(app):
        _assert_controlled_503(api.post(PERSONS, json=new_person))

    assert anonymous.get("/health/ready").status_code == 200
    assert api.get(f"{PERSONS}/{seeded['person']}").status_code == 200
    assert api.get(PERSONS).json()["total_records"] == 1  # el alta interrumpida no quedó guardada
    assert api.post(PERSONS, json=new_person).status_code == 201
    assert api.get(PERSONS).json()["total_records"] == 2


@pytest.mark.parametrize(
    "orig",
    [pg.DeadlockDetected("deadlock detected"), pg.SerializationFailure("could not serialize access")],
    ids=["40P01", "40001"],
)
def test_other_postgresql_errors_keep_internal_error(app, api, seeded, orig) -> None:
    with failing_statements(app, orig):
        response = api.get(f"{PERSONS}/{seeded['person']}")

    assert response.status_code == 500
    assert response.json()["code"] == "PARTY_IDENTITY.INTERNAL_ERROR"
