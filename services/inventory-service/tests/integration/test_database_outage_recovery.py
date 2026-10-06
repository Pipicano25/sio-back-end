"""Caída y recuperación de PostgreSQL en el entorno integrado (Principio X, SC-008; T062).

Ejecutar con `pytest -m integration`. Exige `sio-inventory-service` y `sio-inventory-db` en marcha,
Docker y las credenciales de prueba. Verifica, sin reiniciar la aplicación:

1. **Caída prolongada** (`docker stop` de la base): `live` `200`, `ready` `503`, operaciones y
   consultas `503` controlado en tiempo acotado; al volver la base, todo responde sin intervención.
2. **Caída inesperada** (`pg_ctl stop -m immediate`): Docker reinicia la base y el servicio vuelve a
   `ready`.

Si la prueba se interrumpe con la base detenida: `docker start sio-inventory-db`.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import httpx
import pytest

from tests.integration.support import INVENTORY, INVENTORY_ROOT, operation, user_client

pytestmark = pytest.mark.integration

DB_CONTAINER = "sio-inventory-db"
APP_CONTAINER = "sio-inventory-service"
RESPONSE_DEADLINE_SECONDS = 10
RECOVERY_SECONDS = 60


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


def _status(client: httpx.Client, method: str, url: str, **kwargs) -> int:
    try:
        return client.request(method, url, timeout=10, **kwargs).status_code
    except httpx.HTTPError:
        return 0


def _timed(call):
    started = time.monotonic()
    response = call()
    return response, time.monotonic() - started


@pytest.fixture(scope="module")
def reader():
    if shutil.which("docker") is None:
        pytest.skip("Docker no está disponible.")
    with user_client("inventario.test") as client:
        yield client


def _assert_controlled_503(response: httpx.Response) -> None:
    assert response.status_code == 503, response.text
    assert "psycopg" not in response.text and "Traceback" not in response.text
    body = response.json()
    assert body["code"] == "INVENTORY.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"


def _assert_ready_again(operator, reader, world, app_started_at: str) -> float:
    elapsed = _wait(
        lambda: _status(reader, "GET", f"{INVENTORY_ROOT}/health/ready") == 200,
        RECOVERY_SECONDS,
        "El servicio no volvió a ready.",
    )
    base = f"{INVENTORY}/companies/{world.company}/branches/{world.branch}"
    assert _status(reader, "GET", f"{base}/balances") == 200
    assert _status(operator, "POST", f"{INVENTORY}/inventory-entries", json=operation(world, (world.products[0], "1"))) == 201
    assert _inspect(APP_CONTAINER, "{{.State.StartedAt}}") == app_started_at, "La aplicación se reinició"
    return elapsed


def test_prolonged_outage_returns_controlled_503_and_recovers(operator, reader, real_world) -> None:
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    base = f"{INVENTORY}/companies/{real_world.company}/branches/{real_world.branch}"
    _docker("stop", DB_CONTAINER)
    try:
        assert _status(reader, "GET", f"{INVENTORY_ROOT}/health/live") == 200
        ready, seconds = _timed(lambda: reader.get(f"{INVENTORY_ROOT}/health/ready", timeout=30))
        assert ready.status_code == 503 and seconds < RESPONSE_DEADLINE_SECONDS
        for call in (
            lambda: operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.products[0], "1")), timeout=30),
            lambda: reader.get(f"{base}/balances", timeout=30),
        ):
            response, seconds = _timed(call)
            _assert_controlled_503(response)
            assert seconds < RESPONSE_DEADLINE_SECONDS, seconds
    finally:
        _docker("start", DB_CONTAINER)

    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    elapsed = _assert_ready_again(operator, reader, real_world, app_started_at)
    assert elapsed < 30, elapsed


def test_unexpected_crash_is_restarted_by_docker(operator, reader, real_world) -> None:
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
    _assert_ready_again(operator, reader, real_world, app_started_at)
