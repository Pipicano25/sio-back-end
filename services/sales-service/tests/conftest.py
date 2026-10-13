"""Fixtures compartidos de sales-service.

- Base de pruebas aislada (`SALES_TEST_DATABASE_URL`), migrada una vez por sesión y
  vaciada antes de cada prueba (los triggers de protección se desactivan solo en la
  transacción del fixture).
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak). Los
  usuarios llevan los roles de sus grupos en la plantilla del realm; las cuentas de
  servicio llevan `client_id` y `preferred_username = service-account-{client_id}`.
- Las cinco dependencias se sustituyen por `tests/fakes.py` inyectados en `create_app`.
- `ventas.test` y `supervisor.test` son miembros de la empresa ficticia y están asignados a la
  sucursal A.
- Los roles reproducen la matriz del realm tras C-08: `ventas` con CRUD explícito de sales (sin
  rentabilidad); `supervisores` con `perm:sales:sales:read-profitability`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
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

from sales_service.config import Settings  # noqa: E402
from sales_service.main import create_app  # noqa: E402
from tests.fakes import UNIT_PRESENTATION_OF, Fakes, build_fakes  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

# Roles de cada usuario de prueba según su grupo en la plantilla del realm.
SALES_READS = (
    "perm:sales:sale_details:read",
    "perm:sales:sale_operations:read",
    "perm:sales:sale_sequences:read",
    "perm:sales:sales:read",
)
USER_ROLES: dict[str, tuple[str, ...]] = {
    "admin.test": ("perm:all:all:all",),
    "supervisor.test": (
        "perm:all:all:read",
        "perm:all:all:create",
        "perm:all:all:update",
        "perm:sales:sales:read-profitability",
    ),
    "ventas.test": (
        "perm:sales:all:create",
        "perm:sales:all:read",
        "perm:sales:all:update",
        "perm:sales:all:delete",
        "perm:commercial-relationship:all:read",
        "perm:operational-context:all:read",
    ),
    "compras.test": ("perm:purchase:all:all", "perm:commercial-relationship:all:read"),
    "inventario.test": (
        "perm:operational-context:all:read",
        "perm:product-catalog:all:read",
        "perm:inventory:balances:read",
        "perm:inventory:movements:read",
    ),
    "reportes.test": (*SALES_READS, "perm:operational-context:application_users:read"),
    "consulta.test": (*SALES_READS, "perm:operational-context:application_users:read"),
}

TABLES = (
    "sale_operations",
    "sale_details",
    "sales",
    "sale_sequence_counters",
    "sale_sequences",
    "audit_outbox",
)
TRIGGERS = {
    "sales": ("tr_sales_no_truncate", "tr_sales_no_delete", "tr_sales_frozen"),
    "sale_details": ("tr_sale_details_draft_only",),
    "sale_sequences": ("tr_sale_sequences_no_delete",),
    "sale_sequence_counters": ("tr_sale_sequence_counters_no_delete",),
    "sale_operations": ("tr_sale_operations_no_delete",),
}


def get_test_database_url() -> str:
    value = os.getenv("SALES_TEST_DATABASE_URL")
    if value is None or not value.strip():
        raise RuntimeError("La variable SALES_TEST_DATABASE_URL es obligatoria para ejecutar las pruebas.")
    url = value.strip()
    parsed = make_url(url)
    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError("SALES_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas.")
    return url


def build_alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return config


def run_alembic(database_url: str, action: str, revision: str) -> None:
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
            "No fue posible conectar con PostgreSQL de pruebas. Inícielo con `docker compose --file "
            "../../infrastructure/services/sales-service.yaml --env-file ../../infrastructure/.env "
            "--profile test up -d sales-test-db`."
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
        for table, triggers in TRIGGERS.items():
            for trigger in triggers:
                connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
        connection.execute(text(f"TRUNCATE TABLE {', '.join(TABLES)}"))
        for table, triggers in TRIGGERS.items():
            for trigger in triggers:
                connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))


@pytest.fixture
def clean_database(test_engine: Engine) -> Generator[None, None, None]:
    truncate_all(test_engine)
    yield
    truncate_all(test_engine)


def count_rows(engine: Engine, table: str, where: str = "true", **params: Any) -> int:
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), params).scalar_one()


def fetch(engine: Engine, sql: str, **params: Any) -> list[Any]:
    with engine.connect() as connection:
        return list(connection.execute(text(sql), params).mappings())


# --------------------------------------------------------------------------
# Autenticación con JWKS local
# --------------------------------------------------------------------------


class LocalJWKSClient:
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
    def _make(*roles: str, sub: str = "user-admin", preferred_username: str | None = None, client_id: str | None = None) -> str:
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
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


def user_sub(username: str) -> str:
    return f"sub-{username}"


@pytest.fixture(scope="session")
def user_token(make_token):
    def _make(username: str) -> str:
        return make_token(*USER_ROLES[username], sub=user_sub(username), preferred_username=username)

    return _make


@pytest.fixture(scope="session")
def service_token(make_token):
    def _make(*roles: str, client_id: str = "sales-service") -> str:
        return make_token(
            *roles, sub=f"sub-sa-{client_id}", preferred_username=f"service-account-{client_id}", client_id=client_id
        )

    return _make


# --------------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------------


@pytest.fixture
def fakes() -> Fakes:
    built = build_fakes()
    world = built.world
    built.oc.add_member(user_sub("ventas.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("admin.test"), world.company, branches=(world.branch, world.branch_b))
    built.oc.add_member(user_sub("supervisor.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("reportes.test"), world.company)
    built.oc.add_member(user_sub("consulta.test"), world.company)
    built.oc.add_member(user_sub("inventario.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("compras.test"), world.company, branches=(world.branch,))
    return built


@pytest.fixture
def world(fakes: Fakes):
    return fakes.world


class Clock:
    """Reloj de la aplicación; `fixed` lo fija y `ticking` lo hace avanzar 1 ms por lectura."""

    def __init__(self) -> None:
        self.fixed: datetime | None = None
        self.ticking = False
        self._ticks = 0

    def __call__(self) -> datetime:
        if self.fixed is None:
            return datetime.now(UTC)
        if self.ticking:
            self._ticks += 1
            return self.fixed + timedelta(milliseconds=self._ticks)
        return self.fixed


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        operational_context_base_url="http://operational-context.test/api/v1",
        commercial_relationship_base_url="http://commercial-relationship.test/api/v1",
        product_catalog_base_url="http://product-catalog.test/api/v1",
        party_identity_base_url="http://party-identity.test/api/v1",
        inventory_base_url="http://inventory.test/api/v1",
        keycloak_token_url="http://keycloak.test/realms/sio/protocol/openid-connect/token",
        client_id="sales-service",
        client_secret="secreto-de-prueba",
        operational_context_timeout_seconds=1.0,
        commercial_relationship_timeout_seconds=1.0,
        product_catalog_timeout_seconds=1.0,
        party_identity_timeout_seconds=1.0,
        inventory_timeout_seconds=1.0,
        lookup_concurrency=4,
        lock_timeout_seconds=5.0,
        reconciler_interval_seconds=1.0,
        reconciler_threshold_seconds=10.0,
    )


@pytest.fixture
def app(test_settings, clean_database, test_auth, fakes: Fakes, clock: Clock):
    return create_app(
        test_settings,
        auth=test_auth,
        token_provider=object(),
        directories_factory=fakes.directories,
        inventory_factory=lambda: fakes.inventory,
        access_factory=fakes.oc.access_for,
        clock=clock,
    )


class ApiClient:
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
def seller(as_user) -> ApiClient:
    return as_user("ventas.test")


@pytest.fixture
def supervisor(as_user) -> ApiClient:
    return as_user("supervisor.test")


# --------------------------------------------------------------------------
# Datos y atajos
# --------------------------------------------------------------------------


def base(world) -> str:
    return f"/api/v1/companies/{world.company}"


def sale_body(world, *lines: dict[str, Any], **header: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "branch_id": str(world.branch),
        "company_customer_id": str(world.customer),
        "lines": list(lines),
    }
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in header.items()})
    return body


def line(product, quantity: str = "2", **extra: Any) -> dict[str, Any]:
    """Línea de venta; sin presentación indicada usa la de factor 1 del producto (spec 019).

    `company_product_presentation_id=None` la omite (para probar el rechazo).
    """
    body: dict[str, Any] = {"company_product_id": str(product), "quantity": quantity}
    presentation = extra.pop("company_product_presentation_id", UNIT_PRESENTATION_OF.get(UUID(str(product)), uuid4()))
    if presentation is not None:
        body["company_product_presentation_id"] = str(presentation)
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in extra.items()})
    return body


def sequence_body(**overrides: Any) -> dict[str, Any]:
    body = {"series_code": "PRINCIPAL", "prefix": "FV", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "NEVER"}
    body.update(overrides)
    return body


def new_key() -> str:
    return f"key-{uuid4()}"


@pytest.fixture
def make_sequence(seller, world):
    def _make(**overrides: Any) -> dict[str, Any]:
        response = seller.post(f"{base(world)}/sale-sequences", json=sequence_body(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def make_draft(seller, world):
    def _make(*lines: dict[str, Any], **header: Any) -> dict[str, Any]:
        lines = lines or (line(world.product),)
        response = seller.post(f"{base(world)}/sales", json=sale_body(world, *lines, **header))
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def confirm(seller, world):
    def _confirm(sale: dict[str, Any], key: str | None = None, client=None, version: int | None = None):
        return (client or seller).post(
            f"{base(world)}/sales/{sale['id']}/confirmation",
            json={"version": version if version is not None else sale["version"]},
            headers={"Idempotency-Key": key or new_key()},
        )

    return _confirm


@pytest.fixture
def cancel(seller, world):
    def _cancel(sale: dict[str, Any], key: str | None = None, reason: str = "Error de registro", client=None, version=None):
        return (client or seller).post(
            f"{base(world)}/sales/{sale['id']}/cancellation",
            json={"version": version if version is not None else sale["version"], "reason": reason},
            headers={"Idempotency-Key": key or new_key()},
        )

    return _cancel
