"""Fixtures compartidos de purchase-service.

- Base de pruebas aislada (`PURCHASE_TEST_DATABASE_URL`), migrada una vez por sesión y
  vaciada antes de cada prueba (los triggers de protección se desactivan solo en la
  transacción del fixture).
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak). Los
  usuarios llevan los roles de sus grupos en la plantilla del realm; las cuentas de
  servicio llevan `client_id` y `preferred_username = service-account-{client_id}`.
- Las seis dependencias se sustituyen por `tests/fakes.py` inyectados en `create_app`.
- `compras.test` es miembro de la empresa ficticia y está asignado a la sucursal A.
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
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

from purchase_service.config import Settings  # noqa: E402
from purchase_service.main import create_app  # noqa: E402
from tests.fakes import Fakes, build_fakes, unit_presentation_of  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

PURCHASE_EXPLICIT = tuple(
    f"perm:purchase:{resource}:{action}"
    for resource in ("purchases", "purchase_details", "purchase_lifecycle_events", "purchase_sequences", "purchase_operations")
    for action in ("create", "read", "update", "delete")
)

# Roles de cada usuario de prueba según su grupo en la plantilla del realm.
USER_ROLES: dict[str, tuple[str, ...]] = {
    "admin.test": ("perm:all:all:all",),
    # Spec 021: los supervisores ajustan la tasa de impuesto de una línea (permiso explícito).
    "supervisor.test": (
        "perm:all:all:read", "perm:all:all:create", "perm:all:all:update", "perm:purchase:purchase_line_taxes:override",
    ),
    # Spec 021: `perm:purchase:all:all` se reemplazó en la plantilla por los permisos explícitos anteriores, sin
    # `purchase_line_taxes:override`.
    "compras.test": (*PURCHASE_EXPLICIT, "perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "ventas.test": ("perm:sales:all:all", "perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "inventario.test": (
        "perm:operational-context:all:read",
        "perm:product-catalog:all:read",
        "perm:inventory:balances:read",
        "perm:inventory:movements:read",
    ),
    "reportes.test": ("perm:purchase:all:read", "perm:operational-context:application_users:read"),
    "consulta.test": ("perm:purchase:all:read", "perm:operational-context:application_users:read"),
}

TABLES = (
    "purchase_price_update_outbox",  # spec 021
    "purchase_presentation_cost_series",  # spec 021
    "purchase_lifecycle_events",
    "purchase_operations",
    "purchase_details",
    "purchases",
    "purchase_sequence_counters",
    "purchase_sequences",
    "audit_outbox",
)
TRIGGERS = {
    "purchases": ("tr_purchases_no_truncate", "tr_purchases_no_delete", "tr_purchases_frozen"),
    "purchase_details": ("tr_purchase_details_draft_only",),
    "purchase_sequences": ("tr_purchase_sequences_no_delete",),
    "purchase_sequence_counters": ("tr_purchase_sequence_counters_no_delete",),
    "purchase_operations": ("tr_purchase_operations_no_delete",),
    "purchase_lifecycle_events": (
        "tr_purchase_lifecycle_events_no_truncate",
        "tr_purchase_lifecycle_events_no_delete",
    ),
}


def get_test_database_url() -> str:
    value = os.getenv("PURCHASE_TEST_DATABASE_URL")
    if value is None or not value.strip():
        raise RuntimeError("La variable PURCHASE_TEST_DATABASE_URL es obligatoria para ejecutar las pruebas.")
    url = value.strip()
    parsed = make_url(url)
    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError("PURCHASE_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas.")
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
            "../../infrastructure/services/purchase-service.yaml --env-file ../../infrastructure/.env "
            "--profile test up -d purchase-test-db`."
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
    def _make(*roles: str, client_id: str = "purchase-service") -> str:
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
    built.oc.add_member(user_sub("compras.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("admin.test"), world.company, branches=(world.branch, world.branch_b))
    built.oc.add_member(user_sub("supervisor.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("reportes.test"), world.company)
    built.oc.add_member(user_sub("consulta.test"), world.company)
    built.oc.add_member(user_sub("inventario.test"), world.company, branches=(world.branch,))
    built.oc.add_member(user_sub("ventas.test"), world.company, branches=(world.branch,))
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
        payment_reference_base_url="http://payment-reference.test",
        inventory_base_url="http://inventory.test/api/v1",
        keycloak_token_url="http://keycloak.test/realms/sio/protocol/openid-connect/token",
        client_id="purchase-service",
        client_secret="secreto-de-prueba",
        operational_context_timeout_seconds=1.0,
        commercial_relationship_timeout_seconds=1.0,
        product_catalog_timeout_seconds=1.0,
        party_identity_timeout_seconds=1.0,
        payment_reference_timeout_seconds=1.0,
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
def buyer(as_user) -> ApiClient:
    return as_user("compras.test")


# --------------------------------------------------------------------------
# Datos y atajos
# --------------------------------------------------------------------------


def base(world) -> str:
    return f"/api/v1/companies/{world.company}"


def purchase_body(world, *lines: dict[str, Any], **header: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "branch_id": str(world.branch),
        "company_supplier_id": str(world.supplier),
        "operation_date": date.today().isoformat(),
        "payment_method_id": str(world.payment_method),
        "lines": list(lines),
    }
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in header.items()})
    return body


def line(product, quantity: str = "2", unit_cost: str = "1000", **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "company_product_id": str(product),
        "company_product_presentation_id": str(unit_presentation_of(product)),
        "quantity": quantity,
        "unit_cost": unit_cost,
    }
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in extra.items()})
    return body


def distinct_lines(fakes, product, count: int, quantity: str = "2", unit_cost: str = "1000") -> list[dict[str, Any]]:
    """`count` líneas del producto, cada una con su propia presentación (spec 021, FR-021-13)."""
    return [
        line(product, quantity, unit_cost, company_product_presentation_id=presentation)
        for presentation in fakes.add_unit_presentations(product, count)
    ]


def sequence_body(**overrides: Any) -> dict[str, Any]:
    body = {"series_code": "PRINCIPAL", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "NEVER"}
    body.update(overrides)
    return body


def new_key() -> str:
    return f"key-{uuid4()}"


@pytest.fixture
def make_sequence(buyer, world):
    def _make(**overrides: Any) -> dict[str, Any]:
        response = buyer.post(f"{base(world)}/purchase-sequences", json=sequence_body(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def make_draft(buyer, world):
    def _make(*lines: dict[str, Any], **header: Any) -> dict[str, Any]:
        lines = lines or (line(world.product),)
        response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines, **header))
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def confirm(buyer, world):
    def _confirm(purchase: dict[str, Any], key: str | None = None, client=None, version: int | None = None):
        return (client or buyer).post(
            f"{base(world)}/purchases/{purchase['id']}/confirmation",
            json={"version": version if version is not None else purchase["version"]},
            headers={"Idempotency-Key": key or new_key()},
        )

    return _confirm


@pytest.fixture
def receive(buyer, world):
    """Recepción física completa (spec 020): la única operación que ingresa la mercancía en Inventory."""

    def _receive(purchase: dict[str, Any], key: str | None = None, client=None, version: int | None = None, full: bool = True):
        return (client or buyer).post(
            f"{base(world)}/purchases/{purchase['id']}/receipt",
            json={"version": version if version is not None else purchase["version"], "full_receipt_confirmed": full},
            headers={"Idempotency-Key": key or new_key()},
        )

    return _receive


@pytest.fixture
def cancel(buyer, world):
    def _cancel(purchase: dict[str, Any], key: str | None = None, reason: str = "Error de registro", client=None, version=None):
        return (client or buyer).post(
            f"{base(world)}/purchases/{purchase['id']}/cancellation",
            json={"version": version if version is not None else purchase["version"], "reason": reason},
            headers={"Idempotency-Key": key or new_key()},
        )

    return _cancel
