"""Fixtures compartidos para las pruebas de commercial-relationship-service.

- Base de pruebas aislada (`COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL`), migrada
  una vez por sesión con Alembic y vaciada antes de cada prueba.
- `sio-auth` real con un JWKS local: los tokens se firman en la prueba con una
  clave RSA temporal (sin Keycloak, Principio IV). Los usuarios llevan los roles
  de sus grupos en la plantilla del realm; la cuenta de servicio lleva
  `client_id` y `preferred_username = service-account-{client_id}` (R-11).
- Operational Context, Product Catalog, Party Identity y Payment Reference se
  sustituyen por dobles de sus puertos (`tests/fakes.py`) inyectados en
  `create_app` (FR-050; FR-070 de la 010).
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

# Valores de prueba (sin secretos reales): la suite nunca llama a Keycloak.
for _name, _value in {
    "KEYCLOAK_BASE_URL": "http://keycloak.test",
    "KEYCLOAK_REALM": "sio",
    "COMMERCIAL_RELATIONSHIP_CLIENT_ID": "commercial-relationship-service",
    "COMMERCIAL_RELATIONSHIP_CLIENT_SECRET": "test-only-secret",
}.items():
    os.environ.setdefault(_name, _value)

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
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from commercial_relationship_service.config import Settings  # noqa: E402
from commercial_relationship_service.main import create_app  # noqa: E402
from tests.fakes import (  # noqa: E402
    FakeOperationalContext,
    FakePartyIdentity,
    FakePaymentReference,
    FakeProductCatalog,
)

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

FUNCTIONAL_TABLES = (
    "audit_outbox",
    "price_list_items",
    "price_lists",
    "supplier_payment_conditions",
    "supplier_products",
    "company_product_presentations",
    "company_products",
    "company_customers",
    "company_suppliers",
)

LOOKUP = "perm:commercial-relationship:platform:lookup"
CR_READ = (
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_suppliers:read",
    # Fase B (R-12 de la 010): lectura de las cinco entidades nuevas.
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:supplier_products:read",
    "perm:commercial-relationship:supplier_payment_conditions:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:price_list_items:read",
)

# Roles de cada usuario de prueba según su grupo en la plantilla del realm.
USER_ROLES: dict[str, tuple[str, ...]] = {
    "admin.test": ("perm:all:all:all",),
    "supervisor.test": ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update"),
    "compras.test": ("perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "ventas.test": ("perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "reportes.test": CR_READ,
    "consulta.test": CR_READ,
    "inventario.test": ("perm:operational-context:all:read", "perm:product-catalog:all:read"),
}


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def get_test_database_url() -> str:
    value = os.getenv("COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL es obligatoria para "
            "ejecutar las pruebas."
        )

    url = value.strip()
    parsed = make_url(url)

    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError(
            "COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL debe apuntar a una base exclusiva "
            "de pruebas, nunca a la base de desarrollo."
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
            "`docker compose --file ../../infrastructure/services/commercial-relationship-service.yaml --env-file ../../infrastructure/.env --profile test up -d commercial-relationship-test-db`."
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


def truncate_all(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL lock_timeout = '15s'"))
        connection.execute(text(f"TRUNCATE TABLE {', '.join(FUNCTIONAL_TABLES)}"))


@pytest.fixture
def clean_database(test_engine: Engine) -> Generator[None, None, None]:
    truncate_all(test_engine)
    yield
    truncate_all(test_engine)


@pytest.fixture
def session_factory(test_engine: Engine, clean_database: None) -> sessionmaker:
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    with session_factory() as session:
        try:
            yield session
        finally:
            session.rollback()


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


@pytest.fixture(scope="session")
def user_token(make_token):
    """Token humano de un usuario de prueba del realm (sin `client_id`)."""

    def _make(username: str) -> str:
        return make_token(*USER_ROLES[username], sub=user_sub(username), preferred_username=username)

    return _make


@pytest.fixture(scope="session")
def service_token(make_token):
    """Token `client_credentials` de una cuenta de servicio (R-11)."""

    def _make(*roles: str, client_id: str = "inventory-service") -> str:
        return make_token(
            *roles,
            sub=f"sub-sa-{client_id}",
            preferred_username=f"service-account-{client_id}",
            client_id=client_id,
            sid=None,
        )

    return _make


# --------------------------------------------------------------------------
# Dependencias simuladas y aplicación
# --------------------------------------------------------------------------


@pytest.fixture
def fake_oc() -> FakeOperationalContext:
    return FakeOperationalContext()


@pytest.fixture
def fake_catalog() -> FakeProductCatalog:
    return FakeProductCatalog()


@pytest.fixture
def fake_party() -> FakePartyIdentity:
    return FakePartyIdentity()


@pytest.fixture
def fake_payment() -> FakePaymentReference:
    return FakePaymentReference()


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        operational_context_base_url="http://operational-context.test/api/v1",
        product_catalog_base_url="http://product-catalog.test/api/v1",
        party_identity_base_url="http://party-identity.test/api/v1",
        payment_reference_base_url="http://payment-reference.test",
        keycloak_base_url="http://keycloak.test",
        keycloak_client_id="commercial-relationship-service",
        keycloak_client_secret="test-only-secret",
        operational_context_timeout_seconds=1.0,
        product_catalog_timeout_seconds=1.0,
        party_identity_timeout_seconds=1.0,
        payment_reference_timeout_seconds=1.0,
        keycloak_timeout_seconds=1.0,
    )


@pytest.fixture
def app(test_settings, clean_database, test_auth, fake_oc, fake_catalog, fake_party, fake_payment):
    return create_app(
        test_settings,
        auth=test_auth,
        access_directory_factory=fake_oc.access_for,
        company_directory_factory=fake_oc.companies_for,
        product_directory_factory=lambda request: fake_catalog,
        party_directory_factory=lambda request: fake_party,
        payment_directory_factory=lambda request: fake_payment,
    )


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

    def put(self, url: str, **kwargs: Any):
        return self._client.put(url, **self._merge(kwargs))

    def request(self, method: str, url: str, **kwargs: Any):
        return self._client.request(method, url, **self._merge(kwargs))


@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def as_user(test_client, user_token):
    """Cliente autenticado como un usuario de prueba del realm."""

    def _make(username: str) -> ApiClient:
        return ApiClient(test_client, user_token(username))

    return _make


@pytest.fixture
def as_token(test_client):
    def _make(token: str | None) -> ApiClient:
        return ApiClient(test_client, token)

    return _make


@pytest.fixture
def company(fake_oc) -> UUID:
    """Empresa activa con su organización y con `admin.test`, `supervisor.test`,
    `compras.test`, `ventas.test`, `reportes.test`, `consulta.test` e `inventario.test`
    como miembros."""
    company_id = uuid4()
    fake_oc.organizations[company_id] = uuid4()

    for username in USER_ROLES:
        fake_oc.add_member(user_sub(username), company_id)

    return company_id


@pytest.fixture
def other_company(fake_oc) -> UUID:
    """Empresa activa sin ningún usuario de prueba como miembro."""
    company_id = uuid4()
    fake_oc.organizations[company_id] = uuid4()
    return company_id


# --------------------------------------------------------------------------
# Auditoría (feature 016)
# --------------------------------------------------------------------------


@pytest.fixture
def outbox(test_engine: Engine):
    """Eventos de la outbox en orden de registro (payload canónico de `sio-audit`)."""

    def _read() -> list[dict[str, Any]]:
        with test_engine.connect() as connection:
            rows = connection.execute(
                text("SELECT payload FROM audit_outbox ORDER BY created_at, payload->>'occurred_at'")
            ).scalars()
            return [dict(row) for row in rows]

    return _read


@pytest.fixture
def clear_outbox(test_engine: Engine):
    def _clear() -> None:
        with test_engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE audit_outbox"))

    return _clear
