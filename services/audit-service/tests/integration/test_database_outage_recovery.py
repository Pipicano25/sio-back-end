"""Caída y recuperación de PostgreSQL en el entorno integrado (Principio X; T067).

Ejecutar con `pytest -m integration`. Exige `sio-audit-service` y `sio-audit-db` en marcha, Docker y
las credenciales de prueba. Verifica, sin reiniciar la aplicación:

1. **Caída prolongada** (`docker stop` de la base): `live` `200`, `ready` `503`, registro y consultas
   `503` controlado en tiempo acotado; al volver la base, todo responde sin intervención.
2. **Caída inesperada** (`pg_ctl stop -m immediate`): Docker reinicia la base y el servicio vuelve a
   `ready`.

Si la prueba se interrumpe con la base detenida: `docker start sio-audit-db`.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from tests.integration.support import AUDIT, AUDIT_ROOT, emitter_client, require_audit, user_client

pytestmark = pytest.mark.integration

DB_CONTAINER = "sio-audit-db"
APP_CONTAINER = "sio-audit-service"
# Cota por respuesta: tiempo de espera de conexión (5 s) más margen; no por suma de llamadas.
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


def _event() -> dict:
    return {
        "event_id": str(uuid4()),
        "action": "CREATE",
        "entity_type": "GlobalProduct",
        "result": "SUCCESS",
        "occurred_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture(scope="module")
def clients():
    if shutil.which("docker") is None:
        pytest.skip("Docker no está disponible.")
    require_audit()
    with emitter_client() as emitter, user_client("supervisor.test") as supervisor:
        yield emitter, supervisor


def _assert_controlled_503(response: httpx.Response) -> None:
    assert response.status_code == 503, response.text
    assert "psycopg" not in response.text and "Traceback" not in response.text
    body = response.json()
    assert body["code"] == "AUDIT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "database"


def _assert_ready_again(clients, app_started_at: str) -> float:
    emitter, supervisor = clients
    elapsed = _wait(
        lambda: _status(supervisor, "GET", f"{AUDIT_ROOT}/health/ready") == 200,
        RECOVERY_SECONDS,
        "El servicio no volvió a ready.",
    )
    assert _status(supervisor, "GET", f"{AUDIT}/platform-audit-events") == 200
    assert _status(emitter, "POST", f"{AUDIT}/audit-events", json=_event()) == 201
    assert _inspect(APP_CONTAINER, "{{.State.StartedAt}}") == app_started_at, "La aplicación se reinició"
    return elapsed


def test_prolonged_outage_returns_controlled_503_and_recovers(clients) -> None:
    emitter, supervisor = clients
    app_started_at = _inspect(APP_CONTAINER, "{{.State.StartedAt}}")
    _docker("stop", DB_CONTAINER)
    try:
        assert _status(supervisor, "GET", f"{AUDIT_ROOT}/health/live") == 200
        ready, seconds = _timed(lambda: supervisor.get(f"{AUDIT_ROOT}/health/ready", timeout=30))
        assert ready.status_code == 503 and seconds < RESPONSE_DEADLINE_SECONDS
        for call in (
            lambda: emitter.post(f"{AUDIT}/audit-events", json=_event(), timeout=30),
            lambda: supervisor.get(f"{AUDIT}/platform-audit-events", timeout=30),
        ):
            response, seconds = _timed(call)
            _assert_controlled_503(response)
            assert seconds < RESPONSE_DEADLINE_SECONDS, seconds
    finally:
        _docker("start", DB_CONTAINER)

    _wait(lambda: _inspect(DB_CONTAINER, "{{.State.Health.Status}}") == "healthy", 120, "La base no volvió a healthy.")
    _assert_ready_again(clients, app_started_at)


def test_unexpected_crash_is_restarted_by_docker(clients) -> None:
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
    _assert_ready_again(clients, app_started_at)
