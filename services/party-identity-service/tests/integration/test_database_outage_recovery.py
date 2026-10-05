"""Caída y recuperación de PostgreSQL en el entorno integrado (feature 009, FR-012).

Se ejecuta solo con `pytest -m integration -o addopts=""` y exige el entorno integrado en marcha
(`sio-party-identity-service` en `PARTY_IDENTITY_INTEGRATION_BASE_URL`, por defecto `http://localhost:8101`, y `sio-party-identity-db`), Docker disponible y la contraseña de los
usuarios de prueba en `KEYCLOAK_TEST_USER_PASSWORD` o en `infrastructure/.env`. Solo hace lecturas con
`admin.test`.

Verifica, sin reiniciar la aplicación:

1. **Caída prolongada** (`docker stop` de la base): `/health/live` `200`, `/health/ready` `503` y los
   endpoints con base `503` controlado, en tiempo acotado; al volver la base, `ready` `200` y consultas
   `200` sin intervención sobre la aplicación.
2. **Caída inesperada** (PostgreSQL termina con `pg_ctl stop -m immediate`): la política de reinicio de
   Docker la levanta sola y el servicio vuelve a `ready`.

Si la prueba se interrumpe con la base detenida: `docker start sio-party-identity-db`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
BASE = os.environ.get("PARTY_IDENTITY_INTEGRATION_BASE_URL", "http://localhost:8101").rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
DB_CONTAINER = "sio-party-identity-db"
APP_CONTAINER = "sio-party-identity-service"
COLLECTION = f"{BASE}/api/v1/person-identities"
ITEM_PREFIX = f"{BASE}/api/v1/person-identities"
DEADLINE_SECONDS = 15
RECOVERY_SECONDS = 60


def _password() -> str | None:
    value = os.environ.get("KEYCLOAK_TEST_USER_PASSWORD", "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == "KEYCLOAK_TEST_USER_PASSWORD":
                value = content.strip().strip('"').strip("'")
    return value or None


def _docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout.strip()


def _inspect(container: str, template: str) -> str:
    return _docker("inspect", "-f", template, container)


def _wait(predicate, timeout: float, message: str) -> float:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if predicate():
            return time.monotonic() - started
        time.sleep(1)
    pytest.fail(message)


def _status(client: httpx.Client, url: str) -> int:
    try:
        return client.get(url, timeout=10).status_code
    except httpx.HTTPError:
        return 0


@pytest.fixture(scope="module")
def client():
    if shutil.which("docker") is None:
        pytest.skip("Docker no está disponible.")
    password = _password()
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    try:
        httpx.get(f"{BASE}/health/ready", timeout=5).raise_for_status()
        token = httpx.post(TOKEN_URL, data={
            "grant_type": "password", "client_id": "sio-web", "scope": "openid",
            "username": "admin.test", "password": password,
        }, timeout=10).raise_for_status().json()["access_token"]
    except (httpx.HTTPError, KeyError):
        pytest.skip("Entorno integrado del servicio o Keycloak no disponible.")
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}) as http:
        yield http


@pytest.fixture
def item_url(client):
    response = client.get(COLLECTION, timeout=10)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    if not items:
        pytest.skip("El entorno integrado no tiene datos para la lectura por id.")
    return f"{ITEM_PREFIX}/{items[0]['id']}"


def _health(path: str) -> str:
    return f"{BASE}/health/{path}"


def _assert_controlled_503(response: httpx.Response) -> None:
    assert response.status_code == 503, response.text
    assert "psycopg" not in response.text and "Traceback" not in response.text
    body = response.json()
    assert body["code"] == "PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"


def _assert_ready_again(client, item_url, app_started_at) -> float:
    elapsed = _wait(lambda: _status(client, _health("ready")) == 200, RECOVERY_SECONDS,
                    "El servicio no volvió a ready.")
    assert _status(client, item_url) == 200
    assert _status(client, COLLECTION) == 200
    assert _inspect(APP_CONTAINER, "{{.State.StartedAt}}") == app_started_at, "La aplicación se reinició"
    return elapsed


def test_prolonged_outage_returns_controlled_503_and_recovers(client, item_url):
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    _docker("stop", DB_CONTAINER)
    try:
        started = time.monotonic()
        assert _status(client, _health("live")) == 200
        assert client.get(_health("ready"), timeout=30).status_code == 503
        _assert_controlled_503(client.get(item_url, timeout=30))
        _assert_controlled_503(client.get(COLLECTION, timeout=30))
        outage_seconds = time.monotonic() - started
        assert outage_seconds < DEADLINE_SECONDS
    finally:
        _docker("start", DB_CONTAINER)

    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    recovery = _assert_ready_again(client, item_url, app_started_at)
    print(f"caida_prolongada respuestas_con_base_caida={outage_seconds:.2f}s recuperacion_ready={recovery:.2f}s")


def test_unexpected_crash_is_restarted_by_docker(client, item_url):
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    assert _inspect(DB_CONTAINER, "{{.HostConfig.RestartPolicy.Name}}") in {"unless-stopped", "always"}
    assert _inspect(APP_CONTAINER, "{{.HostConfig.RestartPolicy.Name}}") in {"unless-stopped", "always"}
    restarts_before = int(_inspect(DB_CONTAINER, "{{.RestartCount}}"))

    subprocess.run(
        ["docker", "exec", "-u", "postgres", DB_CONTAINER, "sh", "-c", 'pg_ctl -D "$PGDATA" stop -m immediate'],
        capture_output=True, text=True, check=False,
    )

    _wait(lambda: int(_inspect(DB_CONTAINER, "{{.RestartCount}}")) > restarts_before, 60,
          "Docker no reinició la base tras la caída inesperada.")
    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    recovery = _assert_ready_again(client, item_url, app_started_at)
    print(f"caida_inesperada recuperacion_ready={recovery:.2f}s")
