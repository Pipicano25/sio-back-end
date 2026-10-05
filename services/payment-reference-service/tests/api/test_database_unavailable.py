"""PostgreSQL no disponible → `503` controlado y recuperación sin intervención (GAP-PR-19).

Se simula la caída apuntando el motor y las sesiones a un puerto cerrado; al restaurarlos, el mismo
proceso vuelve a responder sin reiniciarse.

Feature 009 (FR-014, alineación correctiva): solo la pérdida de conexión produce el `503`; un deadlock
o un fallo de serialización con la base disponible conservan su `500` no controlado.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

import psycopg.errors as pg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from payment_reference_service.api.errors import DATABASE_UNAVAILABLE_DETAIL
from payment_reference_service.infrastructure import database
from tests.conftest import CONDITION_TYPES, CT_READ

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"


@pytest.fixture
def database_down(monkeypatch):
    down = create_engine(UNREACHABLE, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    monkeypatch.setattr(database, "engine", down)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=down, class_=Session, expire_on_commit=False))
    yield
    down.dispose()


def test_endpoints_respond_controlled_503_while_database_is_down(as_roles, admin, condition_type, database_down):
    reader = as_roles(CT_READ)
    started = time.monotonic()

    responses = [
        reader.get(CONDITION_TYPES),
        reader.get(f"{CONDITION_TYPES}/{condition_type['id']}"),
        admin.post(CONDITION_TYPES, json={"code": "X", "name": "x"}),
        admin.put(f"{CONDITION_TYPES}/{condition_type['id']}", json={"version": 1, "code": "CREDIT", "name": "c"}),
        admin.post(f"{CONDITION_TYPES}/{condition_type['id']}/deactivate", json={"version": 1}),
        admin.get("/global-payment-methods"),
    ]

    assert [r.status_code for r in responses] == [503] * len(responses)
    assert all(r.json() == {"detail": DATABASE_UNAVAILABLE_DETAIL} for r in responses)
    assert all("psycopg" not in r.text and "127.0.0.1" not in r.text for r in responses)
    assert time.monotonic() - started < 30  # tiempo acotado: nunca espera indefinidamente


def test_health_while_database_is_down(as_token, database_down):
    client = as_token(None)

    assert client.get("/health/live").status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["status"] == "unavailable"


def test_service_recovers_without_restart_when_database_returns(as_roles, as_token, condition_type, monkeypatch):
    down = create_engine(UNREACHABLE, pool_pre_ping=True, connect_args={"connect_timeout": 2})
    original_engine, original_sessions = database.engine, database.SessionLocal
    monkeypatch.setattr(database, "engine", down)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=down, class_=Session, expire_on_commit=False))
    reader = as_roles(CT_READ)
    assert reader.get(CONDITION_TYPES).status_code == 503

    # La base "vuelve": el mismo proceso, con su pool, atiende de nuevo.
    monkeypatch.setattr(database, "engine", original_engine)
    monkeypatch.setattr(database, "SessionLocal", original_sessions)
    down.dispose()

    assert as_token(None).get("/health/ready").status_code == 200
    response = reader.get(f"{CONDITION_TYPES}/{condition_type['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == condition_type["id"]


@contextmanager
def failing_statements(orig: Exception):
    """Cada sentencia SQL falla con un `OperationalError` cuyo origen es `orig` (base disponible)."""

    def fail(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, orig)

    event.listen(database.engine, "before_cursor_execute", fail)
    try:
        yield
    finally:
        event.remove(database.engine, "before_cursor_execute", fail)


@pytest.fixture
def raw_reader(app, make_token):
    """Cliente que recibe el `500` no controlado como respuesta en lugar de propagar la excepción."""
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers["Authorization"] = f"Bearer {make_token(CT_READ)}"
        yield client


@pytest.mark.parametrize(
    "orig",
    [pg.DeadlockDetected("deadlock detected"), pg.SerializationFailure("could not serialize access")],
    ids=["40P01", "40001"],
)
def test_other_postgresql_errors_do_not_return_503(raw_reader, condition_type, orig):
    with failing_statements(orig):
        response = raw_reader.get(f"{CONDITION_TYPES}/{condition_type['id']}")

    assert response.status_code == 500  # comportamiento anterior a la feature 008, no `503`
    assert response.status_code != 503


def test_connection_loss_sqlstate_returns_controlled_503(raw_reader, condition_type):
    with failing_statements(pg.AdminShutdown("terminating connection due to administrator command")):
        response = raw_reader.get(f"{CONDITION_TYPES}/{condition_type['id']}")

    assert response.status_code == 503
    assert response.json() == {"detail": DATABASE_UNAVAILABLE_DETAIL}
