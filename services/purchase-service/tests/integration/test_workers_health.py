"""Salud de los workers de precios en contenedores aislados (spec 021; T072; CP-T18).

Ejecutar con `pytest -m integration` en la pila aislada (`SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-`). Solo lee:
ejecuta `--check` dentro de cada contenedor aislado y consulta su healthcheck; no detiene nada.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from tests.integration.support import container, docker, wait_until

pytestmark = pytest.mark.integration

WORKERS = {
    "sio-purchase-price-update-worker": "purchase_service.price_update_worker",
    "sio-commercial-relationship-price-worker": "commercial_relationship_service.price_worker",
}


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


@pytest.mark.parametrize("name", sorted(WORKERS))
def test_cpt18_worker_check_and_healthcheck(name) -> None:
    target = container(name)
    assert docker("inspect", "-f", "{{.State.Running}}", target) == "true"
    result = subprocess.run(["docker", "exec", target, "python", "-m", WORKERS[name], "--check"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr[-500:]
    health = docker("inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{end}}", target)
    if health:  # el contenedor declara healthcheck: debe quedar sano
        wait_until(lambda: docker("inspect", "-f", "{{.State.Health.Status}}", target) == "healthy", 90,
                   f"{target} no quedó healthy")
    logs = subprocess.run(["docker", "logs", "--tail", "200", target], capture_output=True, text=True)
    text = logs.stdout + logs.stderr
    # Un Traceback de una caída de la base aislada (otra prueba de la suite) es esperable; los secretos no.
    assert "password" not in text.lower() and "Bearer " not in text and "client_secret" not in text
