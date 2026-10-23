"""Fixtures compartidos para las pruebas de product-catalog-service.

- Base de pruebas aislada (`PRODUCT_CATALOG_TEST_DATABASE_URL`), migrada una vez
  por sesión con Alembic y vaciada antes de cada prueba.
- `sio-auth` real con un JWKS local: los tokens se firman en la prueba con una
  clave RSA temporal (sin Keycloak, Principio IV).
- Party Identity sustituido por un doble configurable (Principio XV).
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from uuid import UUID

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
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from product_catalog_service.application.exceptions import (  # noqa: E402
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
)
from product_catalog_service.config import Settings  # noqa: E402
from product_catalog_service.main import create_app  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

FUNCTIONAL_TABLES = (
    "audit_outbox",
    "global_product_attribute_values",
    "global_category_attributes",
    "product_attribute_options",
    "product_attribute_definitions",
    "global_product_identifiers",
    "global_product_presentations",
    "global_product_group_assignments",
    "global_product_groups",
    "global_product_group_types",
    "product_assets",
    "global_product_categories",
    "global_products",
    "global_categories",
    "global_brands",
    "global_packaging_types",
    "global_units_of_measure",
)


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def _get_test_database_url() -> str:
    value = os.getenv("PRODUCT_CATALOG_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable PRODUCT_CATALOG_TEST_DATABASE_URL es obligatoria para ejecutar las pruebas."
        )

    url = value.strip()
    database_name = make_url(url).database

    if database_name is None or "test" not in database_name.lower():
        raise RuntimeError(
            "PRODUCT_CATALOG_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas."
        )

    return url


def build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return config


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _get_test_database_url()


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str) -> Generator[None, None, None]:
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
def test_engine(test_database_url: str, migrated_database: None) -> Generator[Engine, None, None]:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def truncate_all(engine: Engine) -> None:
    with engine.begin() as connection:
        # Falla rápido si una prueba dejó una transacción abierta.
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
# Party Identity simulado
# --------------------------------------------------------------------------


class FakeManufacturerDirectory:
    """Doble de `ManufacturerDirectory` con modos configurables."""

    def __init__(self) -> None:
        self.existing: set[UUID] = set()
        self.mode = "ok"  # ok | unavailable | denied
        self.calls: list[UUID] = []

    def exists(self, organization_id: UUID) -> bool:
        self.calls.append(organization_id)

        if self.mode == "unavailable":
            raise ManufacturerDirectoryUnavailableError("Party Identity no disponible.")

        if self.mode == "denied":
            raise ManufacturerDirectoryAccessDeniedError("Party Identity denegó el acceso.")

        return organization_id in self.existing


@pytest.fixture
def fake_manufacturer_directory() -> FakeManufacturerDirectory:
    return FakeManufacturerDirectory()


# --------------------------------------------------------------------------
# Aplicación y cliente
# --------------------------------------------------------------------------


@pytest.fixture
def app(
    test_database_url: str,
    clean_database: None,
    test_auth: SIOAuth,
    fake_manufacturer_directory: FakeManufacturerDirectory,
):
    settings = Settings(
        docs_enabled=True,
        database_url=test_database_url,
        party_identity_service_base_url="http://party-identity.test",
        party_identity_timeout_seconds=1.0,
    )
    from tests.storage_fakes import FakeAssetStorage

    return create_app(
        settings,
        auth=test_auth,
        manufacturer_directory_factory=lambda request: fake_manufacturer_directory,
        asset_storage=FakeAssetStorage(),  # spec 024: la carga de imágenes de los ejemplos escribe aquí
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
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api(test_client: TestClient, make_token):
    """Cliente administrador con `perm:product-catalog:all:all`."""
    return ApiClient(test_client, make_token("perm:product-catalog:all:all"))


@pytest.fixture
def api_as(test_client: TestClient, make_token):
    """Fábrica de clientes con permisos concretos: `api_as("units-of-measure:read")`."""

    def _build(*permissions: str, sub: str = "user-limited") -> ApiClient:
        roles = [
            permission if permission.startswith("perm:") else f"perm:product-catalog:{permission}"
            for permission in permissions
        ]
        return ApiClient(test_client, make_token(*roles, sub=sub))

    return _build


@pytest.fixture
def anonymous(test_client: TestClient) -> ApiClient:
    return ApiClient(test_client, None)


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
