"""Expiración del Access Token, del Refresh Token y de la sesión contra la pila aislada `sio-it-*`.

Los tiempos reales del realm (Access Token 300 s, inactividad 30 min, máximo 10 h) no caben en una prueba: se crea
un cliente público **temporal** en el realm aislado con los mismos mecanismos y tiempos cortos (atributos de cliente
`access.token.lifespan`, `client.session.idle.timeout` y `client.session.max.lifespan`) y se elimina al terminar.
Se omite sin `SIO_TEST_TARGET=isolated`; `validation/isolation_guard.py` verifica los destinos antes de empezar.

    SIO_TEST_TARGET=isolated .venv/bin/pytest tests/integration/test_expiracion_de_sesion.py
"""

from __future__ import annotations

import importlib.util
import os
import secrets
import time
from collections.abc import Iterator
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
ACCESS_LIFESPAN, IDLE, MAX = 3, 8, 14  # segundos (margen: Keycloak trunca a segundos)


def _secret(name: str) -> str:
    path = Path(os.environ.get("SIO_IT_ENV_FILE", REPO / "validation" / "isolated-stack" / ".env"))
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip()
    raise RuntimeError(f"{name} no está en el .env de la pila aislada")


@pytest.fixture(scope="module")
def client_id() -> Iterator[str]:
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.check_targets({"keycloak": KEYCLOAK, "geography": GEOGRAPHY})

    token = httpx.post(f"{KEYCLOAK}/realms/master/protocol/openid-connect/token", timeout=30, data={
        "grant_type": "password", "client_id": "admin-cli",
        "username": _secret("SIO_IT_KEYCLOAK_ADMIN_USER"),
        "password": _secret("SIO_IT_KEYCLOAK_ADMIN_PASSWORD")}).raise_for_status().json()["access_token"]
    name = f"rt-expiracion-{secrets.token_hex(4)}"
    with httpx.Client(base_url=f"{KEYCLOAK}/admin/realms/sio", timeout=30,
                      headers={"Authorization": f"Bearer {token}"}) as admin:
        admin.post("/clients", json={
            "clientId": name, "enabled": True, "publicClient": True, "protocol": "openid-connect",
            "standardFlowEnabled": False, "directAccessGrantsEnabled": True, "fullScopeAllowed": True,
            "attributes": {"access.token.lifespan": str(ACCESS_LIFESPAN),
                           "client.session.idle.timeout": str(IDLE),
                           "client.session.max.lifespan": str(MAX)},
            "protocolMappers": [{"name": "sio-api-audience", "protocol": "openid-connect",
                                 "protocolMapper": "oidc-audience-mapper",
                                 "config": {"included.client.audience": "sio-api", "access.token.claim": "true"}}],
        }).raise_for_status()
        try:
            yield name
        finally:
            [created] = admin.get("/clients", params={"clientId": name}).json()
            admin.delete(f"/clients/{created['id']}")


def _login(client_id: str) -> dict:
    return httpx.post(f"{OIDC}/token", timeout=30, data={
        "grant_type": "password", "client_id": client_id, "scope": "openid",
        "username": "consulta.test", "password": _secret("KEYCLOAK_TEST_USER_PASSWORD")}).raise_for_status().json()


def _refresh(client_id: str, refresh_token: str) -> httpx.Response:
    return httpx.post(f"{OIDC}/token", timeout=30, data={
        "grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token})


def _countries(access_token: str) -> httpx.Response:
    return httpx.get(f"{GEOGRAPHY}/global-countries", timeout=30,
                     headers={"Authorization": f"Bearer {access_token}"})


def test_rt003_access_token_expirado_es_rechazado_por_el_microservicio(client_id):
    tokens = _login(client_id)
    assert tokens["expires_in"] == ACCESS_LIFESPAN
    assert _countries(tokens["access_token"]).status_code == 200

    time.sleep(ACCESS_LIFESPAN + 1.5)

    expired = _countries(tokens["access_token"])
    assert expired.status_code == 401
    assert expired.json()["detail"] == "El token de acceso ha expirado"
    # El Refresh Token sigue vigente: la renovación evita volver a iniciar sesión.
    renewed = _refresh(client_id, tokens["refresh_token"])
    assert renewed.status_code == 200
    assert _countries(renewed.json()["access_token"]).status_code == 200


def test_rt005_rt008_refresh_token_vencido_por_inactividad_exige_login(client_id):
    tokens = _login(client_id)

    time.sleep(IDLE + 1.5)

    response = _refresh(client_id, tokens["refresh_token"])
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


def test_la_vida_maxima_de_la_sesion_se_respeta_aunque_haya_actividad(client_id):
    tokens = _login(client_id)
    started = time.monotonic()
    rejected = None
    while time.monotonic() - started < MAX + 4:
        time.sleep(2)
        response = _refresh(client_id, tokens["refresh_token"])
        if response.status_code != 200:
            rejected = time.monotonic() - started
            assert response.json()["error"] == "invalid_grant"
            break
        tokens = response.json()
    assert rejected is not None, "la sesión superó su vida máxima"
    assert rejected >= MAX - 1
