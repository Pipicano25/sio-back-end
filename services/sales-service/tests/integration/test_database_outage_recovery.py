"""Caída y recuperación de PostgreSQL de Sales en el entorno integrado (Principio X; T081).

1. **Caída prolongada** (`docker stop sio-sales-db`): `live` `200`, `ready` `503`, rutas `503`
   controlado en tiempo acotado; al volver la base, todo responde sin reiniciar la aplicación.
2. **Caída inesperada** (`pg_ctl stop -m immediate`): Docker reinicia la base y el servicio vuelve a `ready`.

Si la prueba se interrumpe con la base detenida: `docker start sio-sales-db`.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import httpx
import pytest

from tests.integration.support import SALES, SALES_ROOT, docker, draft_body, wait_until

pytestmark = pytest.mark.integration

DB_CONTAINER = "sio-sales-db"
APP_CONTAINER = "sio-sales-service"


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


def status(client, method: str, url: str, **kwargs) -> int:
    try:
        return client.request(method, url, timeout=15, **kwargs).status_code
    except httpx.HTTPError:
        return 0


def test_prolonged_outage_and_recovery_without_restart(seller, real_world) -> None:
    started_at = docker("inspect", "-f", "{{.State.StartedAt}}", APP_CONTAINER)
    base = f"{SALES}/companies/{real_world.company}"
    docker("stop", DB_CONTAINER)
    try:
        assert httpx.get(f"{SALES_ROOT}/health/live", timeout=10).status_code == 200
        assert httpx.get(f"{SALES_ROOT}/health/ready", timeout=15).status_code == 503
        for method, url, body in (
            ("GET", f"{base}/sales", None),
            ("GET", f"{base}/sale-sequences", None),
            ("POST", f"{base}/sales", draft_body(real_world)),
        ):
            begin = time.monotonic()
            response = seller.request(method, url, json=body, timeout=30)
            assert response.status_code == 503, response.text
            assert response.json()["dependency"] == "database"
            assert time.monotonic() - begin < 15
    finally:
        docker("start", DB_CONTAINER)

    wait_until(lambda: httpx.get(f"{SALES_ROOT}/health/ready", timeout=5).status_code == 200, 90, "ready no volvió")
    wait_until(lambda: status(seller, "GET", f"{base}/sales") == 200, 60, "las consultas no volvieron")
    assert docker("inspect", "-f", "{{.State.StartedAt}}", APP_CONTAINER) == started_at  # sin reinicio


def test_unexpected_crash_is_restarted_by_docker(seller, real_world) -> None:
    subprocess.run(
        ["docker", "exec", "-u", "postgres", DB_CONTAINER, "sh", "-c", 'pg_ctl -D "$PGDATA" stop -m immediate'],
        capture_output=True,
    )
    wait_until(lambda: httpx.get(f"{SALES_ROOT}/health/ready", timeout=5).status_code == 200, 120, "la base no se reinició")
    wait_until(
        lambda: status(seller, "GET", f"{SALES}/companies/{real_world.company}/sales") == 200, 60, "el servicio no se recuperó"
    )
