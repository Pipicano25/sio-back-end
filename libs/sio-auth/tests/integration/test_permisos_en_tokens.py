"""Permisos efectivos en el Access Token al iniciar sesión y al renovarlo con Refresh Token.

Pruebas activas contra la pila aislada `sio-it-*` (`validation/isolated-stack/`): emiten y renuevan tokens y
cambian, solo en el realm de esa pila, los permisos de un usuario temporal que crean y eliminan ellas mismas.
`validation/isolation_guard.py` verifica Keycloak y Geography antes de la primera solicitud; sin
`SIO_TEST_TARGET=isolated` el módulo se omite. Los secretos son los de `validation/isolated-stack/.env`; nunca
se imprimen ni se leen los de `infrastructure/.env`.

Validan:
1. El login entrega en `resource_access.sio-api.roles` exactamente los client roles efectivos del usuario
   (grupos y asignaciones directas), en la estructura `perm:{servicio}:{recurso}:{accion}` que lee sio-auth.
2. El token renovado con `grant_type=refresh_token` refleja los permisos **vigentes**: un alta o una baja hecha
   después del login aparece en la siguiente renovación, sin volver a iniciar sesión.
3. Un microservicio real (Geography) autoriza según el token: `403` sin el permiso y `200` con él.
4. Un Access Token ya emitido conserva sus permisos hasta su `exp` (ventana de propagación).
5. Los permisos no se duplican en claims adicionales.

Ejecución, con la pila mínima levantada (Keycloak y Geography migrada):

    SIO_TEST_TARGET=isolated .venv/bin/pytest tests/integration/test_permisos_en_tokens.py
"""

from __future__ import annotations

import importlib.util
import os
import secrets
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from sio_auth import AuthSettings, SioPermission
from sio_auth.jwks import JWKSClient
from sio_auth.permissions import has_permission
from sio_auth.tokens import AccessTokenDecoder, TokenClaims

REPO = Path(__file__).resolve().parents[4]

if os.environ.get("SIO_TEST_TARGET", "").strip() != "isolated":
    pytest.skip(
        "Pruebas activas: solo con SIO_TEST_TARGET=isolated contra la pila aislada sio-it-*.",
        allow_module_level=True,
    )

KEYCLOAK = os.environ.get("SIO_IT_KEYCLOAK_URL", "http://127.0.0.1:18081").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_INTEGRATION_BASE_URL", "http://127.0.0.1:18102").rstrip("/")
REALM = "sio"
ISSUER = os.environ.get("SIO_IT_KEYCLOAK_ISSUER", f"http://localhost:18081/realms/{REALM}")
TOKEN_URL = f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token"
ADMIN = f"{KEYCLOAK}/admin/realms/{REALM}"

COUNTRIES_READ = SioPermission("geography", "global_countries", "read")
DIRECT_ROLE = "perm:geography:global_countries:read"
GROUP = "inventario"  # incluye perm:geography:all:read (plantilla del realm)


def _guard():
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _isolated_secret(name: str) -> str:
    path = Path(os.environ.get("SIO_IT_ENV_FILE", REPO / "validation" / "isolated-stack" / ".env"))
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip()
    raise RuntimeError(f"{name} no está en el .env de la pila aislada")


@pytest.fixture(scope="module")
def admin() -> Iterator[httpx.Client]:
    _guard().check_targets({"keycloak": KEYCLOAK, "geography": GEOGRAPHY})
    body = httpx.post(
        f"{KEYCLOAK}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli",
              "username": _isolated_secret("SIO_IT_KEYCLOAK_ADMIN_USER"),
              "password": _isolated_secret("SIO_IT_KEYCLOAK_ADMIN_PASSWORD")},
        timeout=30,
    ).raise_for_status().json()
    with httpx.Client(base_url=ADMIN, timeout=30,
                      headers={"Authorization": f"Bearer {body['access_token']}"}) as client:
        yield client


@pytest.fixture(scope="module")
def decoder() -> Iterator[AccessTokenDecoder]:
    settings = AuthSettings(issuer=ISSUER, jwks_url=f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/certs")
    with JWKSClient(settings) as jwks:
        yield AccessTokenDecoder(settings, jwks)


@pytest.fixture(scope="module")
def api_client_id(admin: httpx.Client) -> str:
    [client] = admin.get("/clients", params={"clientId": "sio-api"}).raise_for_status().json()
    return client["id"]


class TemporaryUser:
    """Usuario temporal del realm aislado, sin grupos ni roles; su contraseña solo vive en memoria."""

    def __init__(self, admin: httpx.Client, api_client_id: str) -> None:
        self._admin, self._api = admin, api_client_id
        self.username = f"rt-permisos-{secrets.token_hex(4)}"
        self.password = secrets.token_urlsafe(24)
        admin.post("/users", json={
            "username": self.username, "enabled": True, "emailVerified": True,
            "firstName": "Prueba", "lastName": "Permisos", "email": f"{self.username}@sio-it.invalid",
            "credentials": [{"type": "password", "value": self.password, "temporary": False}],
        }).raise_for_status()
        [user] = admin.get("/users", params={"username": self.username, "exact": "true"}).raise_for_status().json()
        self.id = user["id"]

    def _role(self, name: str) -> dict:
        role = self._admin.get(f"/clients/{self._api}/roles/{name}").raise_for_status().json()
        return {"id": role["id"], "name": role["name"]}

    def _group_id(self, name: str) -> str:
        groups = self._admin.get("/groups", params={"search": name, "exact": "true"}).raise_for_status().json()
        return next(group["id"] for group in groups if group["name"] == name)

    def grant_role(self, name: str) -> None:
        self._admin.post(f"/users/{self.id}/role-mappings/clients/{self._api}", json=[self._role(name)]).raise_for_status()

    def revoke_role(self, name: str) -> None:
        self._admin.request("DELETE", f"/users/{self.id}/role-mappings/clients/{self._api}",
                            json=[self._role(name)]).raise_for_status()

    def join(self, group: str) -> None:
        self._admin.put(f"/users/{self.id}/groups/{self._group_id(group)}").raise_for_status()

    def leave(self, group: str) -> None:
        self._admin.delete(f"/users/{self.id}/groups/{self._group_id(group)}").raise_for_status()

    def effective_roles(self) -> set[str]:
        """Client roles efectivos de `sio-api` según Keycloak (grupos, asignaciones directas y compuestos)."""
        roles = self._admin.get(f"/users/{self.id}/role-mappings/clients/{self._api}/composite").raise_for_status()
        return {role["name"] for role in roles.json()}

    def delete(self) -> None:
        self._admin.delete(f"/users/{self.id}")


@pytest.fixture
def user(admin: httpx.Client, api_client_id: str) -> Iterator[TemporaryUser]:
    created = TemporaryUser(admin, api_client_id)
    try:
        yield created
    finally:
        created.delete()


def _login(user: TemporaryUser) -> dict:
    response = httpx.post(TOKEN_URL, timeout=30, data={
        "grant_type": "password", "client_id": "sio-web", "scope": "openid",
        "username": user.username, "password": user.password})
    assert response.status_code == 200, f"login rechazado: estado={response.status_code}"
    return response.json()


def _refresh(tokens: dict) -> dict:
    response = httpx.post(TOKEN_URL, timeout=30, data={
        "grant_type": "refresh_token", "client_id": "sio-web", "refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200, f"renovación rechazada: estado={response.status_code}"
    renewed = response.json()
    assert renewed["access_token"] != tokens["access_token"]
    return renewed


def _countries(access_token: str) -> int:
    return httpx.get(f"{GEOGRAPHY}/global-countries", timeout=30,
                     headers={"Authorization": f"Bearer {access_token}"}).status_code


def _claims(decoder: AccessTokenDecoder, tokens: dict) -> TokenClaims:
    return decoder.decode(tokens["access_token"])


def test_login_entrega_los_permisos_efectivos_en_la_estructura_de_sio_auth(user, decoder):
    user.join(GROUP)
    user.grant_role(DIRECT_ROLE)

    claims = _claims(decoder, _login(user))

    assert claims.roles == user.effective_roles()
    assert "perm:geography:all:read" in claims.roles  # del grupo
    assert DIRECT_ROLE in claims.roles  # asignación directa
    # Además de los `perm:*`, cada grupo trae su rol de perfil (`inventario`), que sio-auth no interpreta.
    perms = {role for role in claims.roles if role.startswith("perm:")}
    assert claims.roles - perms == {GROUP}
    assert len(claims.permissions) == len(perms)
    assert has_permission(claims.permissions, COUNTRIES_READ)


def test_la_renovacion_refleja_altas_y_bajas_posteriores_al_login(user, decoder):
    tokens = _login(user)
    assert _claims(decoder, tokens).roles == set()
    assert _countries(tokens["access_token"]) == 403

    user.grant_role(DIRECT_ROLE)
    tokens = _refresh(tokens)
    claims = _claims(decoder, tokens)
    assert claims.roles == {DIRECT_ROLE} == user.effective_roles()
    assert _countries(tokens["access_token"]) == 200

    user.join(GROUP)
    tokens = _refresh(tokens)
    claims = _claims(decoder, tokens)
    assert claims.roles == user.effective_roles()
    assert {DIRECT_ROLE, "perm:geography:all:read"} <= claims.roles

    user.revoke_role(DIRECT_ROLE)
    user.leave(GROUP)
    tokens = _refresh(tokens)
    claims = _claims(decoder, tokens)
    assert claims.roles == set() == user.effective_roles()
    assert not has_permission(claims.permissions, COUNTRIES_READ)
    assert _countries(tokens["access_token"]) == 403


def test_un_token_ya_emitido_conserva_sus_permisos_hasta_expirar(user):
    user.grant_role(DIRECT_ROLE)
    granted = _login(user)
    assert _countries(granted["access_token"]) == 200

    user.revoke_role(DIRECT_ROLE)

    # Keycloak no reemite tokens: el ya emitido sigue siendo válido hasta su `exp` (accessTokenLifespan, 300 s).
    assert _countries(granted["access_token"]) == 200
    assert _countries(_refresh(granted)["access_token"]) == 403


def test_los_permisos_no_se_duplican_en_otros_claims(user, decoder):
    user.join(GROUP)

    claims = _claims(decoder, _login(user))

    assert set(claims.raw["resource_access"]) <= {"sio-api", "account"}
    assert not {"permissions", "perms", "authorities", "groups"} & set(claims.raw)
    assert "sio-api" in claims.audiences
    assert not any(role.startswith("perm:") for role in claims.raw.get("realm_access", {}).get("roles", []))
