"""PostgreSQL no disponible → `503 {"detail": …}` y recuperación sin intervención (feature 009).

Cambio mínimo sobre la línea base AS-IS congelada (FR-005): el `503` usa el formato vigente de Geography
(`{"detail": …}`, sin `code` ni `trace_id`) y cualquier otro error de PostgreSQL conserva su `500`.

`create_app()` no admite inyección: la prueba fija `DATABASE_URL` hacia la base de pruebas y sustituye
`SIOAuth.from_env` por una fachada con JWKS local, sin cambiar código de producción. Se simula la caída
apuntando el motor y la fábrica de sesiones de la **misma** instancia `app.state.database` a un puerto
cerrado; al restaurarlos, el mismo proceso vuelve a responder sin reiniciarse.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import jwt
import psycopg.errors as pg
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sio_auth import AuthSettings, SIOAuth
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from geography_service import main
from geography_service.api.errors import DATABASE_UNAVAILABLE_DETAIL

UNREACHABLE = "postgresql+psycopg://nadie:nada@127.0.0.1:1/ninguna"
COUNTRIES = "/global-countries"
INTERNAL_MARKERS = ("psycopg", "127.0.0.1", "SELECT", "Traceback", "nadie")
TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
PERMISSIONS = (
    "perm:geography:global_countries:read",
    "perm:geography:global_countries:create",
    "perm:geography:global_administrative_divisions:read",
    "perm:geography:global_cities:read",
)


class LocalJWKSClient:
    """Sustituye al cliente JWKS de `sio-auth` con una clave pública local."""

    def __init__(self, public_key: Any) -> None:
        self._public_key = public_key

    def get_signing_key(self, kid: str) -> Any:
        return self._public_key

    def close(self) -> None:
        return None


@pytest.fixture(scope="module")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def app(monkeypatch, test_database_url: str, clean_database: None, rsa_private_key):
    test_auth = SIOAuth(
        AuthSettings(issuer=TEST_ISSUER, audience=TEST_AUDIENCE),
        jwks_client=LocalJWKSClient(rsa_private_key.public_key()),
    )
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setattr(main.SIOAuth, "from_env", lambda: test_auth)
    return main.create_app()


@pytest.fixture
def client(app, rsa_private_key) -> Generator[TestClient, None, None]:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-geography-test",
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": now,
            "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(PERMISSIONS)}},
        },
        rsa_private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    # El `lifespan` fija `app.state.database`; los errores no controlados se responden como `500`.
    with TestClient(app, raise_server_exceptions=False, headers={"Authorization": f"Bearer {token}"}) as test_client:
        yield test_client


@pytest.fixture
def country(client) -> dict:
    """País creado con la base disponible."""
    response = client.post(COUNTRIES, json={"iso2_code": "CO", "iso3_code": "COL", "name": "Colombia", "status": "ACTIVE"})
    assert response.status_code == 201, response.text
    return response.json()


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
    assert response.json() == {"detail": DATABASE_UNAVAILABLE_DETAIL}
    assert not any(marker in response.text for marker in INTERNAL_MARKERS)


def test_endpoints_respond_controlled_503_while_database_is_down(app, client, country) -> None:
    with database_down(app):
        results = [
            _timed(client.get, COUNTRIES),
            _timed(client.get, f"{COUNTRIES}/{country['id']}"),
            _timed(client.post, COUNTRIES, json={"iso2_code": "PE", "iso3_code": "PER", "name": "Perú", "status": "ACTIVE"}),
            _timed(client.get, "/global-administrative-divisions"),
            _timed(client.get, "/global-cities"),
        ]

    for response, elapsed in results:
        _assert_controlled_503(response)
        assert elapsed < 15  # tiempo acotado por respuesta (conexión con tiempo de espera)


def test_health_while_database_is_down(app, client) -> None:
    with database_down(app):
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503


def test_service_recovers_without_restart_and_leaves_no_partial_write(app, client, country) -> None:
    new_country = {"iso2_code": "PE", "iso3_code": "PER", "name": "Perú", "status": "ACTIVE"}

    with database_down(app):
        _assert_controlled_503(client.post(COUNTRIES, json=new_country))

    assert client.get("/health/ready").status_code == 200
    assert client.get(f"{COUNTRIES}/{country['id']}").status_code == 200
    assert client.get(COUNTRIES).json()["total_records"] == 1  # el alta interrumpida no quedó guardada
    assert client.post(COUNTRIES, json=new_country).status_code == 201
    assert client.get(COUNTRIES).json()["total_records"] == 2


@pytest.mark.parametrize(
    "orig",
    [pg.DeadlockDetected("deadlock detected"), pg.SerializationFailure("could not serialize access")],
    ids=["40P01", "40001"],
)
def test_other_postgresql_errors_keep_as_is_500(app, client, country, orig) -> None:
    with failing_statements(app, orig):
        response = client.get(f"{COUNTRIES}/{country['id']}")

    assert response.status_code == 500  # comportamiento AS-IS, no `503`
