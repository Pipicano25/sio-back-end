"""Caída y recuperación de PostgreSQL en el entorno integrado (GAP-PR-19).

Se ejecuta solo con `pytest -m integration` y exige el entorno integrado en marcha
(`sio-payment-reference-service` en `PAYMENT_REFERENCE_INTEGRATION_BASE_URL`, por defecto
`http://localhost:8105`, y `sio-payment-reference-db`), Docker disponible y la contraseña de los usuarios
de prueba en `KEYCLOAK_TEST_USER_PASSWORD` o en `infrastructure/.env`.

Verifica, sin reiniciar la aplicación:

1. **Caída prolongada** (`docker stop` de la base): `/health/live` `200`, `/health/ready` `503` y los
   endpoints con base `503` controlado, en tiempo acotado; al volver la base, `ready` `200` y consultas
   `200` sin intervención sobre la aplicación.
2. **Caída inesperada** (PostgreSQL termina con `pg_ctl stop -m immediate`): la política de reinicio de
   Docker la levanta sola y el servicio vuelve a `ready`.
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
BASE = os.environ.get("PAYMENT_REFERENCE_INTEGRATION_BASE_URL", "http://localhost:8105").rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
DB_CONTAINER = "sio-payment-reference-db"
APP_CONTAINER = "sio-payment-reference-service"
CONDITION_TYPES = f"{BASE}/global-payment-condition-types"


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


def _wait(predicate, timeout: float, message: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
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
            "username": "reportes.test", "password": password,
        }, timeout=10).raise_for_status().json()["access_token"]
    except (httpx.HTTPError, KeyError):
        pytest.skip("Entorno integrado de Payment Reference o Keycloak no disponible.")
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}) as http:
        yield http


@pytest.fixture
def item_url(client):
    items = client.get(CONDITION_TYPES, timeout=10).json()["items"]
    if not items:
        pytest.skip("El entorno integrado no tiene tipos de condición (ejecute el seed).")
    return f"{CONDITION_TYPES}/{items[0]['id']}"


def _assert_ready_again(client, item_url, app_started_at):
    _wait(lambda: _status(client, f"{BASE}/health/ready") == 200, 120, "El servicio no volvió a ready.")
    assert _status(client, item_url) == 200
    assert _status(client, CONDITION_TYPES) == 200
    assert _inspect(APP_CONTAINER, "{{.State.StartedAt}}") == app_started_at, "La aplicación se reinició"


def test_prolonged_outage_returns_controlled_503_and_recovers(client, item_url):
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    _docker("stop", DB_CONTAINER)
    try:
        started = time.monotonic()
        assert _status(client, f"{BASE}/health/live") == 200
        ready = client.get(f"{BASE}/health/ready", timeout=30)
        assert ready.status_code == 503
        response = client.get(item_url, timeout=30)
        assert response.status_code == 503
        assert set(response.json()) == {"detail"}
        assert "psycopg" not in response.text
        assert client.get(CONDITION_TYPES, timeout=30).status_code == 503
        assert time.monotonic() - started < 60
    finally:
        _docker("start", DB_CONTAINER)

    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    _assert_ready_again(client, item_url, app_started_at)


def test_unexpected_crash_is_restarted_by_docker(client, item_url):
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    assert _inspect(DB_CONTAINER, "{{.HostConfig.RestartPolicy.Name}}") in {"unless-stopped", "always"}
    restarts_before = int(_inspect(DB_CONTAINER, "{{.RestartCount}}"))

    subprocess.run(
        ["docker", "exec", "-u", "postgres", DB_CONTAINER, "sh", "-c", 'pg_ctl -D "$PGDATA" stop -m immediate'],
        capture_output=True, text=True, check=False,
    )

    _wait(lambda: int(_inspect(DB_CONTAINER, "{{.RestartCount}}")) > restarts_before, 60,
          "Docker no reinició la base tras la caída inesperada.")
    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    _assert_ready_again(client, item_url, app_started_at)
