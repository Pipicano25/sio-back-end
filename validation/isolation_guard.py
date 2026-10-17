"""Barrera de aislamiento para las pruebas que escriben contra servicios reales de SIO.

Origen: el 2026-10-16 una ejecución de la guía E2E contra el entorno integrado persistente creó datos de prueba en
las bases persistentes (incidente E2E 268427DC/218839C8). Esta barrera hace **fallar** la ejecución antes de la
primera escritura si no se puede demostrar que todos los destinos son entornos aislados de pruebas.

Reglas (todas obligatorias):

1. **Autorización explícita:** `SIO_TEST_TARGET=isolated`. Sin esa variable no se ejecuta nada contra servicios
   reales (no hay valor por omisión que apunte al entorno persistente).
2. **Destino verificable:** cada URL (servicios y Keycloak) debe ser HTTP en una dirección de bucle local y su puerto
   debe estar publicado por **exactamente un** contenedor Docker en marcha. `localhost` no basta: los servicios
   persistentes también usan `127.0.0.1`.
3. **Contenedor aislado:** ese contenedor debe llevar la etiqueta `sio.integration.isolated=true` y un nombre con el
   prefijo autorizado (`SIO_INTEGRATION_CONTAINER_PREFIX`, por omisión `sio-it-`). Los contenedores persistentes no
   llevan esa etiqueta.
4. **Operaciones de Docker:** detener, iniciar o ejecutar comandos solo sobre contenedores que cumplan la regla 3.

Si Docker no responde, un puerto no tiene contenedor o hay ambigüedad, la barrera falla (nunca supone aislamiento).
No imprime secretos: los mensajes solo contienen nombres de servicio, puertos y nombres de contenedor.

Uso desde otra suite (sin instalar nada), como `sio_query` carga `services/get_token.py`:

    spec = importlib.util.spec_from_file_location("isolation_guard", REPO / "validation" / "isolation_guard.py")
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    guard.check_targets({"purchase": "http://127.0.0.1:18107/api/v1", ...})
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from typing import NamedTuple
from urllib.parse import urlparse

LABEL = "sio.integration.isolated"
DEFAULT_PREFIX = "sio-it-"
TARGET_VARIABLE = "SIO_TEST_TARGET"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_PUBLISHED = re.compile(r"(?:(?P<ip>[0-9.]+|\[[0-9a-f:]*\]|::):)?(?P<host>\d+)->\d+/tcp")


class IsolationError(RuntimeError):
    """El destino no se pudo demostrar aislado: la ejecución se detiene antes de escribir."""


class Container(NamedTuple):
    name: str
    isolated: bool
    ports: frozenset[int]


Runner = Callable[[list[str]], str]


def _docker(args: list[str]) -> str:
    try:
        completed = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise IsolationError(f"Docker no responde ({type(error).__name__}): no se puede verificar el aislamiento.") from None
    return completed.stdout


def running_containers(runner: Runner = _docker) -> list[Container]:
    """Contenedores en marcha con sus puertos publicados en el host y su etiqueta de aislamiento."""
    output = runner(["ps", "--format", "{{json .}}"])
    containers = []
    for line in output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        labels = dict(item.split("=", 1) for item in (row.get("Labels") or "").split(",") if "=" in item)
        ports = frozenset(int(match.group("host")) for match in _PUBLISHED.finditer(row.get("Ports") or ""))
        containers.append(Container(row["Names"], labels.get(LABEL) == "true", ports))
    return containers


def _prefix(environ: Mapping[str, str]) -> str:
    return environ.get("SIO_INTEGRATION_CONTAINER_PREFIX") or DEFAULT_PREFIX


def _authorized(environ: Mapping[str, str]) -> None:
    if environ.get(TARGET_VARIABLE, "").strip() != "isolated":
        raise IsolationError(
            f"{TARGET_VARIABLE}=isolated no está definido: estas pruebas escriben en servicios reales y solo se ejecutan "
            "contra la pila aislada (sio-it-*). Use la configuración de la pila aislada; nunca el entorno persistente."
        )
    if not _prefix(environ).startswith("sio-it"):
        raise IsolationError("SIO_INTEGRATION_CONTAINER_PREFIX debe identificar la pila aislada (sio-it-…).")


def check_targets(
    urls: Mapping[str, str], *, environ: Mapping[str, str] | None = None, runner: Runner = _docker
) -> dict[str, str]:
    """Verifica que cada URL llegue a un contenedor aislado; devuelve `{nombre: contenedor}` o lanza `IsolationError`."""
    environ = os.environ if environ is None else environ
    _authorized(environ)
    prefix = _prefix(environ)
    containers = running_containers(runner)
    resolved: dict[str, str] = {}
    problems: list[str] = []
    for name, url in sorted(urls.items()):
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port
        if parsed.scheme != "http" or host not in LOOPBACK or port is None:
            problems.append(f"{name}: destino no verificable ({parsed.scheme}://{host}:{port}); solo puertos locales publicados")
            continue
        owners = [container for container in containers if port in container.ports]
        if len(owners) != 1:
            problems.append(f"{name}: el puerto {port} lo publican {len(owners)} contenedores (se exige exactamente uno)")
            continue
        owner = owners[0]
        if not owner.isolated or not owner.name.startswith(prefix):
            problems.append(f"{name}: el puerto {port} pertenece a {owner.name}, que no es un contenedor aislado ({LABEL}=true, {prefix}*)")
            continue
        resolved[name] = owner.name
    if problems:
        raise IsolationError("Destinos no autorizados; no se ejecutó ninguna escritura:\n- " + "\n- ".join(problems))
    return resolved


def check_container(name: str, *, environ: Mapping[str, str] | None = None, runner: Runner = _docker) -> str:
    """Autoriza una operación de Docker (stop, start, exec) solo sobre un contenedor aislado en marcha o detenido."""
    environ = os.environ if environ is None else environ
    _authorized(environ)
    label = runner(["inspect", "-f", f'{{{{index .Config.Labels "{LABEL}"}}}}', name]).strip()
    if label != "true" or not name.startswith(_prefix(environ)):
        raise IsolationError(f"{name} no es un contenedor aislado ({LABEL}=true, {_prefix(environ)}*): operación bloqueada.")
    return name
