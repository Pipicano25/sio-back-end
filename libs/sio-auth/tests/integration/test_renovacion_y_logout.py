"""Renovación, rotación y logout de sesiones de `sio-web` contra la pila aislada `sio-it-*`.

Pruebas activas: emiten, renuevan y revocan tokens del usuario de prueba `consulta.test` solo en Keycloak de la
pila aislada (`validation/isolation_guard.py` antes de la primera solicitud). Se omiten sin `SIO_TEST_TARGET=isolated`.
Política verificada (plantilla del realm): `revokeRefreshToken=true`, `refreshTokenMaxReuse=0`, sin `offline_access`
en `sio-web` y clientes técnicos con `client_credentials` sin Refresh Token.

    SIO_TEST_TARGET=isolated .venv/bin/pytest tests/integration/test_renovacion_y_logout.py
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[4]

if os.environ.get("SIO_TEST_TARGET", "").strip() != "isolated":
    pytest.skip("Pruebas activas: solo con SIO_TEST_TARGET=isolated contra la pila aislada sio-it-*.",
                allow_module_level=True)

KEYCLOAK = os.environ.get("SIO_IT_KEYCLOAK_URL", "http://127.0.0.1:18081").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_INTEGRATION_BASE_URL", "http://127.0.0.1:18102").rstrip("/")
OIDC = f"{KEYCLOAK}/realms/sio/protocol/openid-connect"


def _secret(name: str) -> str:
    path = Path(os.environ.get("SIO_IT_ENV_FILE", REPO / "validation" / "isolated-stack" / ".env"))
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip()
    raise RuntimeError(f"{name} no está en el .env de la pila aislada")


@pytest.fixture(scope="module", autouse=True)
def isolated() -> None:
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.check_targets({"keycloak": KEYCLOAK, "geography": GEOGRAPHY})


def _login(scope: str = "openid") -> httpx.Response:
    return httpx.post(f"{OIDC}/token", timeout=30, data={
        "grant_type": "password", "client_id": "sio-web", "scope": scope,
        "username": "consulta.test", "password": _secret("KEYCLOAK_TEST_USER_PASSWORD")})


def _refresh(refresh_token: str) -> httpx.Response:
    return httpx.post(f"{OIDC}/token", timeout=30, data={
        "grant_type": "refresh_token", "client_id": "sio-web", "refresh_token": refresh_token})


def _payload(token: str) -> dict:
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def _countries(access_token: str) -> int:
    return httpx.get(f"{GEOGRAPHY}/global-countries", timeout=30,
                     headers={"Authorization": f"Bearer {access_token}"}).status_code


def test_rt001_rt004_rt011_login_y_renovacion_aceptada_por_un_microservicio():
    login = _login().raise_for_status().json()
    assert {"access_token", "refresh_token", "expires_in"} <= set(login)
    renewed = _refresh(login["refresh_token"])
    assert renewed.status_code == 200
    body = renewed.json()
    assert body["refresh_token"] != login["refresh_token"]  # rotación: se entrega uno nuevo
    assert _countries(body["access_token"]) == 200


def test_rt007_un_refresh_token_ya_usado_se_rechaza_y_cierra_la_sesion():
    login = _login().raise_for_status().json()
    current = _refresh(login["refresh_token"]).raise_for_status().json()["refresh_token"]
    reused = _refresh(login["refresh_token"])
    assert reused.status_code == 400
    assert reused.json()["error"] == "invalid_grant"
    # Keycloak trata la reutilización como posible robo: invalida también el Refresh Token vigente de la sesión.
    assert _refresh(current).status_code == 400


def test_rt006_refresh_token_invalido():
    response = _refresh("no-es-un-token")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


def test_rt010_renovaciones_concurrentes_solo_una_gana_y_la_otra_cierra_la_sesion():
    refresh_token = _login().raise_for_status().json()["refresh_token"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(_refresh, [refresh_token, refresh_token]))
    assert sorted(r.status_code for r in responses) == [200, 400]
    # La perdedora cuenta como reutilización: el token de la ganadora también queda inválido. Por eso el frontend
    # debe mantener una sola renovación en vuelo (docs/frontend-permissions.md).
    [winner] = [r.json() for r in responses if r.status_code == 200]
    assert _refresh(winner["refresh_token"]).status_code == 400


def test_rt009_logout_invalida_la_sesion():
    login = _login().raise_for_status().json()
    logout = httpx.post(f"{OIDC}/logout", timeout=30,
                        data={"client_id": "sio-web", "refresh_token": login["refresh_token"]})
    assert logout.status_code == 204
    assert _refresh(login["refresh_token"]).status_code == 400


def test_sio_web_no_emite_tokens_offline():
    response = _login("openid offline_access")
    if response.status_code == 200:
        assert _payload(response.json()["refresh_token"]).get("typ") == "Refresh"
    else:
        assert response.json()["error"] == "invalid_scope"


def test_rt012_identidad_tecnica_sin_refresh_token():
    body = httpx.post(f"{OIDC}/token", timeout=30, data={
        "grant_type": "client_credentials", "client_id": "sales-service",
        "client_secret": _secret("SALES_SERVICE_CLIENT_SECRET")}).raise_for_status().json()
    assert "access_token" in body and "refresh_token" not in body
