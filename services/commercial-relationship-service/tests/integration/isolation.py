"""Contenedores de las pruebas que detienen servicios: solo los aislados (`sio.integration.isolated=true`).

`SIO_INTEGRATION_CONTAINER_PREFIX` (por ejemplo `sio-it-`) traduce `sio-audit-service` → `sio-it-audit-service`. Un
contenedor sin la etiqueta de aislamiento nunca se detiene: la prueba se omite (spec 021; mismas reglas que Purchase).
"""

from __future__ import annotations

import os
import subprocess

import pytest

PREFIX = os.environ.get("SIO_INTEGRATION_CONTAINER_PREFIX", "sio-")
LABEL = "sio.integration.isolated"


def container(name: str) -> str:
    resolved = PREFIX + name.removeprefix("sio-")
    try:
        label = subprocess.run(
            ["docker", "inspect", "-f", f'{{{{index .Config.Labels "{LABEL}"}}}}', resolved],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"Contenedor aislado no disponible: {resolved}")
    if label != "true":
        pytest.skip(f"{resolved} no lleva {LABEL}=true: no se detienen contenedores persistentes.")
    return resolved
