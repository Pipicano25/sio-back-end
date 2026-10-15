"""Configuración común de las pruebas de payment-reference-service (feature 008).

- La base es la de pruebas aislada (`PAYMENT_REFERENCE_TEST_DATABASE_URL`, perfil `test` de
  `docker-compose.yml`); se fija como `DATABASE_URL` **antes** de importar el servicio, porque el motor
  de base se crea al importar.
- Los tokens se firman con una clave RSA temporal: las pruebas no necesitan Keycloak. El doble de
  autenticación se inyecta explícitamente en `create_app(auth=...)` (FR-043); sin él, la aplicación
  usa la autenticación real.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

SERVICE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SERVICE_ROOT / ".env", override=False)

TEST_ISSUER = "http://issuer.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"


def _test_database_url() -> str:
    value = os.environ.get("PAYMENT_REFERENCE_TEST_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "Defina PAYMENT_REFERENCE_TEST_DATABASE_URL (ver .env.example) y levante la base con "
            "`docker compose --file ../../infrastructure/services/payment-reference-service.yaml --env-file ../../infrastructure/.env --profile test up -d payment-reference-test-db`."
        )
    database = make_url(value).database or ""
    if "test" not in database.lower():
        raise RuntimeError("PAYMENT_REFERENCE_TEST_DATABASE_URL debe apuntar a una base de pruebas.")
    return value


# Debe ocurrir antes de cualquier import del servicio.
os.environ["DATABASE_URL"] = _test_database_url()
os.environ["SIO_AUTH_ISSUER"] = TEST_ISSUER
os.environ["SIO_AUTH_JWKS_URL"] = "http://issuer.test/realms/sio/protocol/openid-connect/certs"
os.environ["SIO_AUTH_AUDIENCE"] = TEST_AUDIENCE
os.environ.setdefault("SIO_DOCS_ENABLED", "false")

import jwt  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sio_auth import AuthSettings, SIOAuth  # noqa: E402
from sqlalchemy import text  # noqa: E402

from payment_reference_service.infrastructure.database import engine  # noqa: E402
from payment_reference_service.main import create_app  # noqa: E402

FUNCTIONAL_TABLES = ("global_payment_condition_types", "global_payment_methods")
CONDITION_TYPES = "/global-payment-condition-types"
METHODS = "/global-payment-methods"

CT_READ = "perm:payment-reference:global_payment_condition_types:read"
CT_CREATE = "perm:payment-reference:global_payment_condition_types:create"
CT_UPDATE = "perm:payment-reference:global_payment_condition_types:update"
CT_DELETE = "perm:payment-reference:global_payment_condition_types:delete"
ADMIN = "perm:all:all:all"


def alembic_config() -> Config:
    config = Config(str(SERVICE_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(SERVICE_ROOT / "alembic"))
    return config


NO_DELETE_TRIGGERS = (
    ("global_payment_methods", "tr_global_payment_methods_no_delete"),
    ("global_payment_methods", "tr_global_payment_methods_no_truncate"),
)


def truncate_all() -> None:
    """Limpia entre pruebas; desactiva en la misma transacción los triggers sin borrado (spec 020)."""
    with engine.begin() as connection:
        for table, trigger in NO_DELETE_TRIGGERS:
            connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
        connection.execute(text(f"TRUNCATE TABLE {', '.join(FUNCTIONAL_TABLES)}"))
        for table, trigger in NO_DELETE_TRIGGERS:
            connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))


class LocalJWKSClient:
    """Sustituye al cliente JWKS de `sio-auth` con una clave pública local."""

    def __init__(self, public_key: Any) -> None:
        self._public_key = public_key

    def get_signing_key(self, kid: str) -> Any:
        return self._public_key

    def close(self) -> None:
        return None


class ApiClient:
    """Cliente de pruebas con un token fijo."""

    def __init__(self, client: TestClient, token: str | None) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def request(self, method: str, url: str, **kwargs: Any):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.request(method, url, headers=headers, **kwargs)

    def get(self, url: str, **kwargs: Any):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Generator[None, None, None]:
    """Aplica las migraciones desde cero una vez por sesión."""
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_database(migrated_database) -> Generator[None, None, None]:
    truncate_all()
    yield
    truncate_all()


@pytest.fixture(scope="session")
def rsa_private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def test_auth(rsa_private_key) -> SIOAuth:
    """Doble de autenticación: valida tokens firmados con la clave temporal."""
    return SIOAuth(
        AuthSettings(issuer=TEST_ISSUER, audience=TEST_AUDIENCE),
        jwks_client=LocalJWKSClient(rsa_private_key.public_key()),
    )


@pytest.fixture(scope="session")
def make_token(rsa_private_key) -> Callable[..., str]:
    def _make(*roles: str, sub: str = "sub-admin") -> str:
        now = int(time.time())
        payload = {
            "sub": sub,
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": now,
            "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(roles)}},
        }
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


@pytest.fixture(scope="session")
def app(test_auth):
    return create_app(auth=test_auth)


@pytest.fixture(scope="session")
def test_client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def as_token(test_client) -> Callable[[str | None], ApiClient]:
    def _make(token: str | None) -> ApiClient:
        return ApiClient(test_client, token)

    return _make


@pytest.fixture
def as_roles(as_token, make_token) -> Callable[..., ApiClient]:
    def _make(*roles: str, sub: str = "sub-admin") -> ApiClient:
        return as_token(make_token(*roles, sub=sub))

    return _make


@pytest.fixture
def admin(as_roles) -> ApiClient:
    return as_roles(ADMIN, sub="sub-admin")


@pytest.fixture
def condition_type(admin) -> dict[str, Any]:
    """Tipo `ACTIVE`, versión 1, creado por la API."""
    response = admin.post(CONDITION_TYPES, json={"code": "CREDIT", "name": "Crédito"})
    assert response.status_code == 201, response.text
    return response.json()
