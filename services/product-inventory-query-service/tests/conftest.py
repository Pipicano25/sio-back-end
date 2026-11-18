"""Fixtures compartidos de product-inventory-query-service.

- Sin base de datos: el servicio no persiste (spec 022, A-02).
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak). Los usuarios del realm
  llevan los roles de su grupo en la plantilla (spec 026), más identidades sintéticas para la visibilidad por bloque; las cuentas de servicio llevan `client_id` y `preferred_username`.
- Las dependencias (OC, CR, PC, Inventory) se sustituyen por `tests/fakes.py` (Principio IV).
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sio_auth import AuthSettings, SIOAuth

from product_inventory_query_service.config import Settings
from product_inventory_query_service.main import create_app

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"
TEST_CURSOR_SECRET = "cursor-secret-for-tests-only-0123456789abcdef"

PIQ = "perm:product-inventory-query"
REALM = Path(__file__).resolve().parents[3] / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"


def _realm_user_roles() -> dict[str, tuple[str, ...]]:
    """Roles de cada usuario de prueba según su grupo en la plantilla del realm (spec 026: superadmin, admin, Compras, Ventas, Inventario; suma de sus grupos)."""
    data = json.loads(REALM.read_text(encoding="utf-8"))
    groups = {"/" + group["name"]: tuple(group["clientRoles"]["sio-api"]) for group in data["groups"]}
    return {
        user["username"]: tuple(dict.fromkeys(role for path in user["groups"] for role in groups[path]))
        for user in data["users"]
        if "serviceAccountClientId" not in user
    }


# Usuarios de prueba del realm más identidades **sintéticas** (no existen en el realm) que conservan las combinaciones
# de permisos que ya ningún grupo tiene por separado desde la spec 026, para seguir probando la visibilidad por bloque:
# `vendedor.sintetico` (precios y existencias, sin mínimos), `bodeguero.sintetico` (existencias y mínimos, sin precios),
# `sin-acceso.sintetico` (sin permisos de este servicio) y `sin-permisos.sintetico` (solo lectura de usuarios de OC).
USER_ROLES: dict[str, tuple[str, ...]] = {
    **_realm_user_roles(),
    "vendedor.sintetico": (
        "perm:commercial-relationship:price_list_items:read",
        "perm:commercial-relationship:company_products:read",
        "perm:product-catalog:all:read",
        "perm:operational-context:all:read",
        f"{PIQ}:product_overviews:read",
        f"{PIQ}:inventory_overviews:read",
        f"{PIQ}:stock:read",
    ),
    "bodeguero.sintetico": (
        "perm:operational-context:all:read",
        "perm:product-catalog:all:read",
        "perm:inventory:balances:read",
        "perm:inventory:product-policies:read",
        "perm:inventory:valuation:read",
        f"{PIQ}:product_overviews:read",
        f"{PIQ}:inventory_overviews:read",
        f"{PIQ}:inventory_summary:read",
        f"{PIQ}:low_stock_products:read",
        f"{PIQ}:stock:read",
    ),
    "sin-acceso.sintetico": ("perm:product-catalog:all:read", "perm:operational-context:all:read"),
    "sin-permisos.sintetico": ("perm:operational-context:application_users:read",),
}


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


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "docs_enabled": True,
        "operational_context_base_url": "http://operational-context.test/api/v1",
        "commercial_relationship_base_url": "http://commercial-relationship.test/api/v1",
        "product_catalog_base_url": "http://product-catalog.test/api/v1",
        "inventory_base_url": "http://inventory.test/api/v1",
        "keycloak_token_url": "http://keycloak.test/realms/sio/protocol/openid-connect/token",
        "client_id": "product-inventory-query-service",
        "client_secret": "client-secret-for-tests",
        "cursor_secret": TEST_CURSOR_SECRET,
        "jwks_url": "http://keycloak.test/realms/sio/protocol/openid-connect/certs",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def test_settings() -> Settings:
    return build_test_settings()


@pytest.fixture
def jwks_state() -> dict[str, bool]:
    """Estado del JWKS simulado para `/health/ready`."""
    return {"available": True}


@pytest.fixture
def app(test_settings: Settings, test_auth: SIOAuth, jwks_state: dict[str, bool]):
    return create_app(test_settings, auth=test_auth, jwks_probe=lambda: jwks_state["available"])


class ApiClient:
    def __init__(self, client: TestClient, token: str | None) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get(self, url: str, **kwargs: Any):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.get(url, headers=headers, **kwargs)


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
