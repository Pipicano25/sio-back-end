"""Fixtures compartidos de business-reporting-service.

- Sin base de datos: el servicio no persiste (spec 023).
- `sio-auth` real con un JWKS local: tokens firmados en la prueba (sin Keycloak). Los usuarios llevan los roles de
  su grupo **leídos de la plantilla del realm** (incluidos los permisos nuevos de la spec 023).
- Las dependencias se sustituyen por `tests/fakes.py` (Principio IV). Como el servicio propaga el token del usuario
  (DR-07), los dobles de los propietarios evalúan el permiso del propietario sobre ese mismo token.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sio_auth import AuthSettings, SIOAuth

from business_reporting_service.config import Settings
from business_reporting_service.main import create_app
from tests.fakes import Fakes, build_fakes

TEST_ISSUER = "https://keycloak.test/realms/sio"
TEST_AUDIENCE = "sio-api"
TEST_KID = "test-key"
NOW = datetime(2026, 10, 18, 15, 0, tzinfo=UTC)
REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"


def _template_roles() -> dict[str, tuple[str, ...]]:
    realm = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    groups = {group["name"]: tuple(group.get("clientRoles", {}).get("sio-api", [])) for group in realm["groups"]}
    roles: dict[str, tuple[str, ...]] = {}
    for user in realm["users"]:
        if user.get("serviceAccountClientId"):
            continue
        names = [g.strip("/") for g in user.get("groups", [])]
        roles[user["username"]] = tuple(role for name in names for role in groups.get(name, ()))
    return roles


USER_ROLES = _template_roles()


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
    return SIOAuth(AuthSettings(issuer=TEST_ISSUER, audience=TEST_AUDIENCE),
                   jwks_client=LocalJWKSClient(rsa_private_key.public_key()))


@pytest.fixture(scope="session")
def make_token(rsa_private_key: rsa.RSAPrivateKey):
    def _make(*roles: str, sub: str = "user-admin", preferred_username: str | None = None) -> str:
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": sub, "iss": TEST_ISSUER, "aud": TEST_AUDIENCE, "iat": now, "exp": now + 600,
            "resource_access": {TEST_AUDIENCE: {"roles": list(roles)}},
        }
        if preferred_username is not None:
            payload["preferred_username"] = preferred_username
        return jwt.encode(payload, rsa_private_key, algorithm="RS256", headers={"kid": TEST_KID})

    return _make


@pytest.fixture(scope="session")
def user_token(make_token):
    def _make(username: str) -> str:
        return make_token(*USER_ROLES[username], sub=f"sub-{username}", preferred_username=username)

    return _make


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "docs_enabled": True,
        "operational_context_base_url": "http://operational-context.test/api/v1",
        "sales_base_url": "http://sales.test/api/v1",
        "purchase_base_url": "http://purchase.test/api/v1",
        "inventory_base_url": "http://inventory.test/api/v1",
        "commercial_relationship_base_url": "http://commercial-relationship.test/api/v1",
        "product_catalog_base_url": "http://product-catalog.test/api/v1",
        "jwks_url": "http://keycloak.test/realms/sio/protocol/openid-connect/certs",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def test_settings() -> Settings:
    return build_test_settings()


@pytest.fixture
def fakes() -> Fakes:
    return build_fakes()


@pytest.fixture
def jwks_state() -> dict[str, bool]:
    return {"available": True}


@pytest.fixture
def app(test_settings: Settings, test_auth: SIOAuth, jwks_state: dict[str, bool], fakes: Fakes):
    return create_app(test_settings, auth=test_auth, jwks_probe=lambda: jwks_state["available"],
                      ports_factory=fakes.ports_for, clock=lambda: NOW)


class ApiClient:
    def __init__(self, client: TestClient, token: str | None) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get(self, url: str, **kwargs: Any):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.get(url, headers=headers, **kwargs)

    def stream(self, url: str, **kwargs: Any):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.stream("GET", url, headers=headers, **kwargs)


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
