"""Fixtures compartidos para las pruebas de operational-context-service.

- Base de pruebas aislada (`OPERATIONAL_CONTEXT_TEST_DATABASE_URL`), migrada una
  vez por sesión con Alembic y vaciada antes de cada prueba.
- `sio-auth` real con un JWKS local: los tokens se firman en la prueba con una
  clave RSA temporal (sin Keycloak, Principio IV).
- Party Identity y Geography se sustituyen por dobles de sus puertos que viven
  solo en `tests/` y se inyectan en `create_app` (R-12).
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

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
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from operational_context_service.config import Settings  # noqa: E402
from operational_context_service.main import create_app  # noqa: E402
from tests.fakes import (  # noqa: E402
    FakeGeographyDirectory,
    FakeOrganizationDirectory,
    GeographyFixture,
)

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

FUNCTIONAL_TABLES = ("branches", "companies")

ADMIN_PERMISSION = "perm:operational-context:all:all"


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def get_test_database_url() -> str:
    value = os.getenv("OPERATIONAL_CONTEXT_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable OPERATIONAL_CONTEXT_TEST_DATABASE_URL es obligatoria para "
            "ejecutar las pruebas."
        )

    url = value.strip()
    parsed = make_url(url)

    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError(
            "OPERATIONAL_CONTEXT_TEST_DATABASE_URL debe apuntar a una base exclusiva "
            "de pruebas, nunca a la base de desarrollo."
        )

    return url


def build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return config


def _check_database_connection(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "No fue posible conectar con PostgreSQL de pruebas. Inícielo con "
            "`docker compose --profile test up -d operational-context-test-db`."
        ) from exc
    finally:
        engine.dispose()


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
    _check_database_connection(test_database_url)
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
        connection.execute(text(f"TRUNCATE TABLE {', '.join(FUNCTIONAL_TABLES)} CASCADE"))


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
    def _make(*permissions: str, sub: str = "user-admin") -> str:
        now = int(time.time())
        payload = {
            "sub": sub,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": now,
            "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(permissions)}},
        }
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


# --------------------------------------------------------------------------
# Dependencias simuladas (solo pruebas)
# --------------------------------------------------------------------------


@pytest.fixture
def fake_organizations() -> FakeOrganizationDirectory:
    return FakeOrganizationDirectory()


@pytest.fixture
def fake_geography() -> FakeGeographyDirectory:
    return FakeGeographyDirectory()


@pytest.fixture
def geo(fake_geography: FakeGeographyDirectory) -> GeographyFixture:
    return GeographyFixture(fake_geography)


# --------------------------------------------------------------------------
# Aplicación y cliente
# --------------------------------------------------------------------------


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        party_identity_base_url="http://party-identity.test/api/v1",
        geography_base_url="http://geography.test",
        party_identity_timeout_seconds=1.0,
        geography_timeout_seconds=1.0,
    )


@pytest.fixture
def app(
    test_settings: Settings,
    clean_database: None,
    test_auth: SIOAuth,
    fake_organizations: FakeOrganizationDirectory,
    fake_geography: FakeGeographyDirectory,
):
    return create_app(
        test_settings,
        auth=test_auth,
        organization_directory_factory=lambda request: fake_organizations,
        geography_directory_factory=lambda request: fake_geography,
    )


class ApiClient:
    """Cliente de pruebas con un token y permisos fijos."""

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

    def delete(self, url: str, **kwargs: Any):
        return self._client.delete(url, **self._merge(kwargs))

    def request(self, method: str, url: str, **kwargs: Any):
        return self._client.request(method, url, **self._merge(kwargs))


@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def api(test_client: TestClient, make_token) -> ApiClient:
    """Cliente administrador con `perm:operational-context:all:all`."""
    return ApiClient(test_client, make_token(ADMIN_PERMISSION))


@pytest.fixture
def api_as(test_client: TestClient, make_token):
    """Fábrica de clientes con permisos y `sub` concretos."""

    def _make(*permissions: str, sub: str = "user-test") -> ApiClient:
        return ApiClient(test_client, make_token(*permissions, sub=sub))

    return _make


@pytest.fixture
def anonymous(test_client: TestClient) -> ApiClient:
    return ApiClient(test_client, None)


# --------------------------------------------------------------------------
# Datos de apoyo
# --------------------------------------------------------------------------


def company_payload(organization_id, **overrides: Any) -> dict[str, Any]:
    """Empresa con datos ficticios de sede operativa principal."""
    payload: dict[str, Any] = {
        "organization_identity_id": str(organization_id),
        "email": "contacto@empresa-ficticia.co",
        "phone": "+57 604 000 0000",
        "address_line": "Calle Ficticia 1 # 2-3",
    }
    payload.update(overrides)
    return payload


def branch_payload(**overrides: Any) -> dict[str, Any]:
    """Sucursal con datos ficticios."""
    payload: dict[str, Any] = {"code": "MED-01", "name": "Sucursal Ficticia Medellín"}
    payload.update(overrides)
    return payload


def update_body(resource: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """Cuerpo de `PUT` a partir de una respuesta (reemplazo completo)."""
    excluded = {
        "id",
        "status",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "company_id",
        "company_status",
        "effective_timezone",
    }
    body = {key: value for key, value in resource.items() if key not in excluded}
    body.update(changes)
    return body


def random_uuid() -> str:
    return str(uuid4())


@pytest.fixture
def create_company(api: ApiClient, fake_organizations: FakeOrganizationDirectory):
    """Crea una empresa `ACTIVE` y devuelve su respuesta JSON."""

    def _create(**overrides: Any) -> dict[str, Any]:
        organization_id = overrides.pop("organization_identity_id", None) or fake_organizations.add()
        response = api.post("/api/v1/companies", json=company_payload(organization_id, **overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def create_branch(api: ApiClient):
    """Crea una sucursal bajo la empresa indicada y devuelve su respuesta JSON."""

    def _create(company_id: str, **overrides: Any) -> dict[str, Any]:
        response = api.post(
            f"/api/v1/companies/{company_id}/branches",
            json=branch_payload(**overrides),
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create
