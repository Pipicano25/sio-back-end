"""Fixtures compartidos para las pruebas de party-identity-service.

- Base de pruebas aislada (`PARTY_IDENTITY_TEST_DATABASE_URL`), migrada una vez
  por sesión con Alembic y vaciada antes de cada prueba.
- `sio-auth` real con un JWKS local: los tokens se firman en la prueba con una
  clave RSA temporal (sin Keycloak, Principio IV).
- Geography se sustituye por `FakeCountryDirectory`, un doble del puerto
  `CountryDirectory` que vive solo aquí y se inyecta en `create_app` (FR-044).
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

from party_identity_service.application.exceptions import (  # noqa: E402
    COUNTRY_VALIDATION_DENIED,
    GEOGRAPHY_UNAVAILABLE,
    CountryNotFoundError,
    DependencyUnavailableError,
)
from party_identity_service.config import Settings  # noqa: E402
from party_identity_service.main import create_app  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

COLOMBIA_ID = UUID("0c3f1a86-3f7b-4c55-9b1e-6f0e8a1d2c01")
"""País ficticio que el doble de Geography reconoce como Colombia (`COL`)."""

FUNCTIONAL_TABLES = (
    "identification_type_rules",
    "person_identities",
    "organization_identities",
)

ADMIN_PERMISSION = "perm:party-identity:all:all"


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def _get_test_database_url() -> str:
    value = os.getenv("PARTY_IDENTITY_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable PARTY_IDENTITY_TEST_DATABASE_URL es obligatoria "
            "para ejecutar las pruebas."
        )

    url = value.strip()
    database_name = make_url(url).database

    if database_name is None or "test" not in database_name.lower():
        raise RuntimeError(
            "PARTY_IDENTITY_TEST_DATABASE_URL debe apuntar a una base "
            "exclusiva de pruebas."
        )

    return url


def build_alembic_config() -> AlembicConfig:
    """Configuración de Alembic apuntando al proyecto del servicio."""
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
            "No fue posible conectar con PostgreSQL de pruebas. Verifique "
            "que party-identity-test-db esté iniciado "
            "(docker compose --profile test up -d party-identity-test-db)."
        ) from exc
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _get_test_database_url()


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> Generator[None, None, None]:
    _check_database_connection(test_database_url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url

    try:
        command.upgrade(build_alembic_config(), "head")
        yield
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def test_engine(
    test_database_url: str,
    migrated_database: None,
) -> Generator[Engine, None, None]:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def truncate_all(engine: Engine) -> None:
    """Vacía las tablas funcionales (incluidas las reglas de las migraciones)."""
    with engine.begin() as connection:
        connection.execute(text("SET LOCAL lock_timeout = '15s'"))
        connection.execute(
            text(f"TRUNCATE TABLE {', '.join(FUNCTIONAL_TABLES)} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def clean_database(test_engine: Engine) -> Generator[None, None, None]:
    truncate_all(test_engine)
    yield
    truncate_all(test_engine)


@pytest.fixture
def db_session(test_engine: Engine, clean_database: None) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        try:
            yield session
        finally:
            session.rollback()


@pytest.fixture
def session_factory(test_engine: Engine, clean_database: None) -> sessionmaker:
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


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
# Geography simulado (solo pruebas)
# --------------------------------------------------------------------------


class FakeCountryDirectory:
    """Doble del puerto `CountryDirectory` con modos configurables.

    Modos: `ok` (responde según `countries`), `unavailable` (Geography caído)
    y `denied` (Geography respondió 401/403). Registra las llamadas para
    comprobar cuándo no se consulta Geography (DS-06).
    """

    def __init__(self) -> None:
        self.countries: dict[UUID, str] = {COLOMBIA_ID: "COL"}
        self.mode = "ok"
        self.calls: list[tuple[str, Any]] = []

    def exists(self, country_id: UUID) -> bool:
        self.calls.append(("exists", country_id))
        self._check_mode()
        return country_id in self.countries

    def find_id_by_iso3(self, iso3_code: str) -> UUID:
        self.calls.append(("find_id_by_iso3", iso3_code))
        self._check_mode()
        matches = [
            country_id
            for country_id, code in self.countries.items()
            if code == iso3_code.upper()
        ]
        if len(matches) != 1:
            raise CountryNotFoundError(
                f"Se encontraron {len(matches)} países con el código {iso3_code}."
            )
        return matches[0]

    def _check_mode(self) -> None:
        if self.mode == "unavailable":
            raise DependencyUnavailableError(cause=GEOGRAPHY_UNAVAILABLE)
        if self.mode == "denied":
            raise DependencyUnavailableError(cause=COUNTRY_VALIDATION_DENIED)

    @property
    def exists_calls(self) -> int:
        return sum(1 for name, _ in self.calls if name == "exists")


@pytest.fixture
def fake_countries() -> FakeCountryDirectory:
    return FakeCountryDirectory()


# --------------------------------------------------------------------------
# Aplicación y cliente
# --------------------------------------------------------------------------


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        geography_service_base_url="http://geography.test",
        geography_timeout_seconds=1.0,
    )


@pytest.fixture
def app(
    test_settings: Settings,
    clean_database: None,
    test_auth: SIOAuth,
    fake_countries: FakeCountryDirectory,
):
    return create_app(
        test_settings,
        auth=test_auth,
        country_directory_factory=lambda request: fake_countries,
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
    """Cliente administrador con `perm:party-identity:all:all`."""
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


def rule_payload(**overrides: Any) -> dict[str, Any]:
    """Regla `CC` moderna de Colombia (18+), usada como base en las pruebas."""
    payload = {
        "party_kind": "PERSON",
        "country_id": str(COLOMBIA_ID),
        "identification_type": "CITIZEN_ID_MODERN",
        "sigla": "CC",
        "number_pattern": "^[0-9]{10}$",
        "number_pattern_description": "La cédula moderna tiene 10 dígitos.",
        "example_value": "1000000000",
        "min_age_years": 18,
    }
    payload.update(overrides)
    return payload


def person_payload(**overrides: Any) -> dict[str, Any]:
    """Persona ficticia adulta con CC (datos de prueba, no reales)."""
    payload = {
        "identification_country_id": str(COLOMBIA_ID),
        "identification_type": "CC",
        "identification_number": "1000000001",
        "first_name": "ANA",
        "last_name": "PRUEBA",
        "birth_date": "1990-05-10",
    }
    payload.update(overrides)
    return payload


def organization_payload(**overrides: Any) -> dict[str, Any]:
    """Organización ficticia con NIT (datos de prueba, no reales)."""
    payload = {
        "country_id": str(COLOMBIA_ID),
        "identification_type": "NIT",
        "identification_number": "900000001-1",
        "legal_name": "ORGANIZACION FICTICIA S.A.S.",
    }
    payload.update(overrides)
    return payload


def random_uuid() -> str:
    return str(uuid4())
