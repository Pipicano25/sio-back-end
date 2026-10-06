"""Fixtures compartidos de audit-service.

- Base de pruebas aislada (`AUDIT_TEST_DATABASE_URL`), migrada una vez por sesión
  y vaciada antes de cada prueba. Como `audit_events` rechaza `TRUNCATE` (RC-02),
  la limpieza desactiva el trigger solo dentro de la transacción del fixture.
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak).
  Los usuarios llevan los roles de sus grupos en la plantilla del realm; las
  cuentas de servicio llevan `client_id` y `preferred_username =
  service-account-{client_id}`.
- Operational Context se sustituye por `tests/fakes.py` inyectado en `create_app`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

import jwt  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sio_auth import AuthSettings, SIOAuth  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.engine.url import make_url  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from audit_service.config import Settings  # noqa: E402
from audit_service.main import create_app  # noqa: E402
from tests.fakes import FakeOperationalContext  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

CREATE = "perm:audit:audit-events:create"
READ = "perm:audit:audit-events:read"
PLATFORM_READ = "perm:audit:platform-events:read"
EMITTER = "audit-test-emitter"

# Roles de cada usuario de prueba según su grupo en la plantilla del realm (DS-18:
# ningún grupo recibe permisos de auditoría explícitos; solo los comodines).
USER_ROLES: dict[str, tuple[str, ...]] = {
    "admin.test": ("perm:all:all:all",),
    "supervisor.test": ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update"),
    "compras.test": ("perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "ventas.test": ("perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "reportes.test": ("perm:operational-context:application_users:read",),
    "consulta.test": ("perm:operational-context:application_users:read",),
    "inventario.test": ("perm:operational-context:all:read", "perm:product-catalog:all:read"),
    # Grupo hipotético al que se concedió solo la lectura de auditoría en Keycloak,
    # sin el permiso que exige Operational Context (FR-037).
    "auditor.sin-oc": (READ,),
}


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def get_test_database_url() -> str:
    value = os.getenv("AUDIT_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError("La variable AUDIT_TEST_DATABASE_URL es obligatoria para ejecutar las pruebas.")

    url = value.strip()
    parsed = make_url(url)

    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError(
            "AUDIT_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas, nunca a la de desarrollo."
        )

    return url


def build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return config


def run_alembic(database_url: str, action: str, revision: str) -> None:
    """Ejecuta `alembic upgrade|downgrade` contra la base indicada."""
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url

    try:
        getattr(command, action)(build_alembic_config(), revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_test_database_url()


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> None:
    engine = create_engine(test_database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "No fue posible conectar con PostgreSQL de pruebas. Inícielo con "
            "`docker compose --file ../../infrastructure/services/audit-service.yaml "
            "--env-file ../../infrastructure/.env --profile test up -d audit-test-db`."
        ) from exc
    finally:
        engine.dispose()

    run_alembic(test_database_url, "upgrade", "head")


@pytest.fixture(scope="session")
def test_engine(test_database_url: str, migrated_database: None) -> Generator[Engine, None, None]:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def truncate_audit_events(engine: Engine) -> None:
    """Vacía la tabla desactivando el trigger de `TRUNCATE` solo en esta transacción."""
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL lock_timeout = '15s'"))
        connection.execute(text("ALTER TABLE audit_events DISABLE TRIGGER tr_audit_events_no_truncate"))
        connection.execute(text("TRUNCATE TABLE audit_events"))
        connection.execute(text("ALTER TABLE audit_events ENABLE TRIGGER tr_audit_events_no_truncate"))


@pytest.fixture
def clean_database(test_engine: Engine) -> Generator[None, None, None]:
    truncate_audit_events(test_engine)
    yield
    truncate_audit_events(test_engine)


# --------------------------------------------------------------------------
# Autenticación con JWKS local
# --------------------------------------------------------------------------


class LocalJWKSClient:
    """Sustituye al cliente JWKS de `sio-auth` con una clave pública local."""

    def __init__(self, public_key: Any) -> None:
        self._public_key = public_key

    def get_signing_key(self, kid: str) -> Any:
        return self._public_key

    def close(self) -> None:
        return None


@pytest.fixture(scope="session")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def test_auth(rsa_private_key: rsa.RSAPrivateKey) -> SIOAuth:
    return SIOAuth(
        AuthSettings(issuer=TEST_ISSUER, audience=TEST_AUDIENCE),
        jwks_client=LocalJWKSClient(rsa_private_key.public_key()),
    )


@pytest.fixture(scope="session")
def make_token(rsa_private_key: rsa.RSAPrivateKey):
    def _make(
        *roles: str,
        sub: str = "user-admin",
        preferred_username: str | None = None,
        client_id: str | None = None,
        sid: str | None = "session-1",
    ) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": sub,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": now,
            "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(roles)}},
        }
        if preferred_username is not None:
            payload["preferred_username"] = preferred_username
        if client_id is not None:
            payload["client_id"] = client_id
        if sid is not None:
            payload["sid"] = sid
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


def user_sub(username: str) -> str:
    """`sub` estable y determinista de un usuario de prueba."""
    return f"sub-{username}"


def service_sub(client_id: str) -> str:
    return f"sub-sa-{client_id}"


@pytest.fixture(scope="session")
def user_token(make_token):
    """Token humano de un usuario de prueba del realm (sin `client_id`)."""

    def _make(username: str) -> str:
        return make_token(*USER_ROLES[username], sub=user_sub(username), preferred_username=username)

    return _make


@pytest.fixture(scope="session")
def service_token(make_token):
    """Token `client_credentials` de una cuenta de servicio."""

    def _make(*roles: str, client_id: str = EMITTER) -> str:
        return make_token(
            *roles,
            sub=service_sub(client_id),
            preferred_username=f"service-account-{client_id}",
            client_id=client_id,
            sid=None,
        )

    return _make


# --------------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------------


@pytest.fixture
def fake_oc() -> FakeOperationalContext:
    return FakeOperationalContext()


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        operational_context_base_url="http://operational-context.test/api/v1",
        operational_context_timeout_seconds=1.0,
        max_clock_skew_seconds=300,
    )


@pytest.fixture
def app(test_settings, clean_database, test_auth, fake_oc):
    return create_app(test_settings, auth=test_auth, access_directory_factory=fake_oc.access_for)


class ApiClient:
    """Cliente de pruebas con un token fijo."""

    def __init__(self, client: TestClient, token: str | None) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def _merge(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return {**kwargs, "headers": headers}

    def get(self, url: str, **kwargs: Any):
        return self._client.get(url, **self._merge(kwargs))

    def post(self, url: str, **kwargs: Any):
        return self._client.post(url, **self._merge(kwargs))

    def request(self, method: str, url: str, **kwargs: Any):
        return self._client.request(method, url, **self._merge(kwargs))


@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def as_user(test_client, user_token):
    def _make(username: str) -> ApiClient:
        return ApiClient(test_client, user_token(username))

    return _make


@pytest.fixture
def as_token(test_client):
    def _make(token: str | None) -> ApiClient:
        return ApiClient(test_client, token)

    return _make


@pytest.fixture
def emitter(test_client, service_token) -> ApiClient:
    """Cuenta de servicio `audit-test-emitter` con permiso de registro."""
    return ApiClient(test_client, service_token(CREATE))


@pytest.fixture
def company(fake_oc) -> UUID:
    """Empresa con todos los usuarios de prueba como miembros `ACTIVE`."""
    company_id = uuid4()
    for username in USER_ROLES:
        fake_oc.add_member(user_sub(username), company_id)
    return company_id


@pytest.fixture
def other_company() -> UUID:
    """Empresa sin ningún usuario de prueba como miembro."""
    return uuid4()


def event_body(**changes: Any) -> dict[str, Any]:
    """Evento válido del contrato v1 (datos ficticios)."""
    body: dict[str, Any] = {
        "event_id": str(uuid4()),
        "company_id": str(uuid4()),
        "action": "CHANGE_PRICE",
        "entity_type": "PriceListItem",
        "entity_id": str(uuid4()),
        "previous_values": {"unit_price": "2000.00"},
        "new_values": {"unit_price": "2100.00"},
        "result": "SUCCESS",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    body.update(changes)
    return {key: value for key, value in body.items() if value is not ...}
