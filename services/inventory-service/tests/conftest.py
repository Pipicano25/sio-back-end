"""Fixtures compartidos de inventory-service.

- Base de pruebas aislada (`INVENTORY_TEST_DATABASE_URL`), migrada una vez por
  sesión y vaciada antes de cada prueba. Como movimientos, operaciones y saldos
  rechazan `TRUNCATE` (RC-02), la limpieza desactiva los triggers solo dentro de la
  transacción del fixture.
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak).
  Los usuarios llevan los roles de sus grupos en la plantilla del realm (DS-17);
  las cuentas de servicio llevan `client_id` y `preferred_username =
  service-account-{client_id}`.
- Operational Context, Commercial Relationship y Keycloak se sustituyen por
  `tests/fakes.py` inyectados en `create_app`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from dataclasses import dataclass
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

from inventory_service.config import Settings  # noqa: E402
from inventory_service.main import create_app  # noqa: E402
from tests.fakes import FakeCommercialRelationship, FakeOperationalContext  # noqa: E402

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"

ENTRIES_CREATE = "perm:inventory:entries:create"
OUTPUTS_CREATE = "perm:inventory:outputs:create"
BALANCES_READ = "perm:inventory:balances:read"
MOVEMENTS_READ = "perm:inventory:movements:read"
PLATFORM_LOOKUP = "perm:inventory:platform:lookup"
ALL_INVENTORY = (ENTRIES_CREATE, OUTPUTS_CREATE, BALANCES_READ, MOVEMENTS_READ, PLATFORM_LOOKUP)

# 013 (R-13, DS-13): 9 permisos nuevos.
ADJUSTMENTS_CREATE = "perm:inventory:adjustments:create"
ADJUSTMENTS_READ = "perm:inventory:adjustments:read"
COUNTS_CREATE = "perm:inventory:counts:create"
COUNTS_READ = "perm:inventory:counts:read"
COMPANY_POLICIES_UPDATE = "perm:inventory:company-policies:update"
COMPANY_POLICIES_READ = "perm:inventory:company-policies:read"
PRODUCT_POLICIES_UPDATE = "perm:inventory:product-policies:update"
PRODUCT_POLICIES_READ = "perm:inventory:product-policies:read"
VALUATION_READ = "perm:inventory:valuation:read"
STOCK_EVOLUTION_READ = "perm:inventory:stock_evolution:read"  # spec 023, DR-11: solo INV-R1, sin costos
READS_013 = (ADJUSTMENTS_READ, COUNTS_READ, COMPANY_POLICIES_READ, PRODUCT_POLICIES_READ, VALUATION_READ)
OPERATOR_ROLES = (*ALL_INVENTORY, *READS_013)
"""Roles de `inventory-test-operator` en la plantilla: los cinco de la Fase A y las cinco lecturas (R-13)."""

OPERATOR = "inventory-test-operator"
PURCHASE_CLIENT = "purchase-service"
SALES_CLIENT = "sales-service"

# Roles de cada usuario de prueba según su grupo en la plantilla del realm
# (incluida la asignación de esta fase al grupo `inventario`, DS-17).
USER_ROLES: dict[str, tuple[str, ...]] = {
    "admin.test": ("perm:all:all:all",),
    "supervisor.test": ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update"),
    "compras.test": ("perm:purchase:all:all", "perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "ventas.test": ("perm:sales:all:all", "perm:commercial-relationship:all:read", "perm:operational-context:all:read"),
    "inventario.test": (
        "perm:operational-context:all:read",
        "perm:product-catalog:all:read",
        BALANCES_READ,
        MOVEMENTS_READ,
        "perm:commercial-relationship:company_products:read",
        # 013 (DS-14): ajustes, conteos y todas las lecturas; políticas solo por comodín.
        ADJUSTMENTS_CREATE,
        COUNTS_CREATE,
        *READS_013,
        STOCK_EVOLUTION_READ,
    ),
    # Spec 023 (DR-11): `reportes` recibe solo `stock_evolution:read` de Inventory (nunca `movements:read`).
    "reportes.test": ("perm:operational-context:application_users:read", "perm:commercial-relationship:company_products:read",
                      STOCK_EVOLUTION_READ),
    "consulta.test": ("perm:operational-context:application_users:read", "perm:commercial-relationship:company_products:read"),
}

TABLES = (
    "inventory_count_details",
    "inventory_adjustments",
    "inventory_counts",
    "inventory_cost_consumptions",
    "inventory_cost_layers",
    "inventory_policies",
    "company_inventory_policies",
    "inventory_movements",
    "inventory_operations",
    "inventory_balances",
    "audit_outbox",
)
TRIGGERS = {
    "inventory_movements": ("tr_inventory_movements_no_truncate", "tr_inventory_movements_no_delete"),
    "inventory_operations": ("tr_inventory_operations_no_truncate", "tr_inventory_operations_no_delete"),
    "inventory_balances": ("tr_inventory_balances_no_truncate", "tr_inventory_balances_no_delete"),
    "inventory_adjustments": ("tr_inventory_adjustments_no_truncate", "tr_inventory_adjustments_no_delete"),
    "inventory_cost_consumptions": (
        "tr_inventory_cost_consumptions_no_truncate",
        "tr_inventory_cost_consumptions_no_delete",
    ),
    "inventory_cost_layers": ("tr_inventory_cost_layers_no_truncate", "tr_inventory_cost_layers_no_delete"),
}


# --------------------------------------------------------------------------
# Base de datos de pruebas
# --------------------------------------------------------------------------


def get_test_database_url() -> str:
    value = os.getenv("INVENTORY_TEST_DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError("La variable INVENTORY_TEST_DATABASE_URL es obligatoria para ejecutar las pruebas.")

    url = value.strip()
    parsed = make_url(url)

    if parsed.database is None or "test" not in parsed.database.lower():
        raise RuntimeError(
            "INVENTORY_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas, nunca a la de desarrollo."
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
            "`docker compose --file ../../infrastructure/services/inventory-service.yaml "
            "--env-file ../../infrastructure/.env --profile test up -d inventory-test-db`."
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
    """Vacía las tablas desactivando los triggers de protección solo en esta transacción."""
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


def count_rows(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


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
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


def user_sub(username: str) -> str:
    """`sub` estable y determinista de un usuario de prueba."""
    return f"sub-{username}"


def service_sub(client_id: str) -> str:
    return f"sub-sa-{client_id}"


@pytest.fixture(scope="session")
def user_token(make_token):
    def _make(username: str) -> str:
        return make_token(*USER_ROLES[username], sub=user_sub(username), preferred_username=username)

    return _make


@pytest.fixture(scope="session")
def service_token(make_token):
    """Token `client_credentials` de una cuenta de servicio."""

    def _make(*roles: str, client_id: str = OPERATOR) -> str:
        return make_token(
            *roles,
            sub=service_sub(client_id),
            preferred_username=f"service-account-{client_id}",
            client_id=client_id,
        )

    return _make


# --------------------------------------------------------------------------
# Aplicación
# --------------------------------------------------------------------------


@pytest.fixture
def fake_oc() -> FakeOperationalContext:
    return FakeOperationalContext()


@pytest.fixture
def fake_cr() -> FakeCommercialRelationship:
    return FakeCommercialRelationship()


@pytest.fixture
def test_settings(test_database_url: str) -> Settings:
    return Settings(
        docs_enabled=True,
        database_url=test_database_url,
        operational_context_base_url="http://operational-context.test/api/v1",
        commercial_relationship_base_url="http://commercial-relationship.test/api/v1",
        keycloak_token_url="http://keycloak.test/realms/sio/protocol/openid-connect/token",
        client_id="inventory-service",
        client_secret="secreto-de-prueba",
        operational_context_timeout_seconds=1.0,
        commercial_relationship_timeout_seconds=1.0,
        lock_timeout_seconds=5.0,
    )


@pytest.fixture
def app(test_settings, clean_database, test_auth, fake_oc, fake_cr):
    return create_app(
        test_settings,
        auth=test_auth,
        operational_context_factory=fake_oc.directory,
        commercial_relationship_factory=fake_cr.directory,
        access_directory_factory=fake_oc.access_for,
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
def operator(test_client, service_token) -> ApiClient:
    """Cliente técnico de pruebas con sus roles de la plantilla (DS-13 (012) y R-13 (013))."""
    return ApiClient(test_client, service_token(*OPERATOR_ROLES))


@pytest.fixture
def purchase(test_client, service_token) -> ApiClient:
    """Consumidor técnico con solo entradas (como Purchase)."""
    return ApiClient(test_client, service_token(ENTRIES_CREATE, client_id=PURCHASE_CLIENT))


@pytest.fixture
def sales(test_client, service_token) -> ApiClient:
    """Consumidor técnico con solo salidas (como Sales)."""
    return ApiClient(test_client, service_token(OUTPUTS_CREATE, client_id=SALES_CLIENT))


# --------------------------------------------------------------------------
# Datos ficticios de validación
# --------------------------------------------------------------------------


@dataclass
class World:
    """Empresa, sucursales, usuario operativo y productos ficticios en los dobles."""

    company: UUID
    branch: UUID
    other_branch: UUID
    user: UUID
    products: list[UUID]
    other_company: UUID
    other_company_branch: UUID
    other_company_user: UUID
    other_company_product: UUID

    def operator_user(self, fake_oc: FakeOperationalContext, username: str) -> UUID:
        """Usuario operativo de un usuario de prueba en la empresa (lo devuelve `operational-access`)."""
        return fake_oc.application_user_of(user_sub(username), self.company)


@pytest.fixture
def world(fake_oc: FakeOperationalContext, fake_cr: FakeCommercialRelationship) -> World:
    company = uuid4()
    other = uuid4()
    w = World(
        company=company,
        branch=fake_oc.add_branch(company),
        other_branch=fake_oc.add_branch(company),
        user=fake_oc.add_user(company),
        products=[fake_cr.add_product(company) for _ in range(3)],
        other_company=other,
        other_company_branch=fake_oc.add_branch(other),
        other_company_user=fake_oc.add_user(other),
        other_company_product=fake_cr.add_product(other),
    )
    for username in USER_ROLES:
        fake_oc.add_member(user_sub(username), company)
        # 013 (DS-14): todos asignados a la sucursal principal y a ninguna otra.
        fake_oc.assign(user_sub(username), w.branch)
    return w


DEFAULT_ENTRY_UNIT_COST = "1000"
"""013 (DS-12, cambio incompatible aprobado): toda entrada lleva costo. Las pruebas que no lo
fijan reciben este valor ficticio; las que verifican su ausencia lo retiran de forma explícita."""


def operation_body(world: World, *lines: dict[str, Any], origin_type: str = "PURCHASE", **overrides: Any) -> dict[str, Any]:
    """Cuerpo de una operación con datos ficticios válidos."""
    if origin_type == "PURCHASE":
        lines = tuple({"unit_cost": DEFAULT_ENTRY_UNIT_COST, **item} for item in lines)
    body: dict[str, Any] = {
        "operation_key": str(uuid4()),
        "company_id": str(world.company),
        "branch_id": str(world.branch),
        "origin_type": origin_type,
        "origin_id": str(uuid4()),
        "application_user_id": str(world.user),
        "correlation_id": str(uuid4()),
        "reason": None,
        "lines": list(lines),
    }
    body.update(overrides)
    return body


def line(product: UUID, quantity: Any, *, unit_cost: Any = None, origin_detail_id: UUID | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "origin_detail_id": str(origin_detail_id or uuid4()),
        "company_product_id": str(product),
        "quantity": quantity,
    }
    if unit_cost is not None:
        item["unit_cost"] = unit_cost
    return item


def reversal_body(world: World, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "operation_key": str(uuid4()),
        "company_id": str(world.company),
        "application_user_id": str(world.user),
        "correlation_id": str(uuid4()),
        "reason": "Anulación del documento ficticio de validación",
    }
    body.update(overrides)
    return body
