"""Control de contenedores para caídas y verificaciones de solo lectura (research R-09).

Solo admite comandos no destructivos: `inspect`, `stop`, `start`, `logs`, `exec` (consultas de
lectura), `info`, `ps` y `compose … up -d` de las bases de pruebas. Nunca `rm`, `down`, `volume`,
`kill` ni `prune` (runner-cli §4).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

HEALTH_TIMEOUT_SECONDS = 180.0
POLL_SECONDS = 2.0
ALLOWED_COMMANDS = {"inspect", "stop", "start", "logs", "exec", "info", "ps", "compose"}
FORBIDDEN_WORDS = {"rm", "down", "volume", "kill", "prune", "rmi", "--volumes", "-v"}
# `exec` solo para lecturas: psql (SELECT), alembic current/heads y comprobaciones de los procesos.
EXEC_PROGRAMS = {"psql", "alembic", "python", "pg_isready"}

Runner = Callable[[list[str]], tuple[int, str]]


class RestoreError(RuntimeError):
    """Un contenedor no volvió a estar sano dentro del límite."""


@dataclass(frozen=True)
class ContainerState:
    name: str
    status: str  # running, exited, created…; "missing" si no existe
    health: str | None  # healthy, unhealthy, starting o None si no tiene healthcheck
    started_at: str | None

    @property
    def healthy(self) -> bool:
        return self.status == "running" and self.health in (None, "healthy")


@dataclass
class RestoreReport:
    restored: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


def subprocess_runner(binary: str | None = None, timeout: float = 600.0) -> Runner:
    docker = binary or os.environ.get("SIO_MVP_DOCKER", "docker")

    def run(args: list[str]) -> tuple[int, str]:
        completed = subprocess.run(
            [docker, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
        )
        return completed.returncode, completed.stdout if completed.returncode == 0 else completed.stdout + completed.stderr

    return run


class DockerEnv:
    def __init__(
        self,
        runner: Runner | None = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        health_timeout: float = HEALTH_TIMEOUT_SECONDS,
        on_event: Callable[[str, dict], None] | None = None,
        container_guard: Callable[[str], object] | None = None,
    ) -> None:
        self._runner = runner or subprocess_runner()
        # Barrera de aislamiento (`validation/isolation_guard.py`): `stop`, `start` y `exec` solo sobre contenedores
        # aislados, y nunca `compose` (los proyectos Compose son los del entorno persistente).
        self._container_guard = container_guard
        self._sleep = sleep
        self._clock = clock
        self.health_timeout = health_timeout
        self._on_event = on_event or (lambda kind, data: None)

    def run(self, args: list[str]) -> tuple[int, str]:
        if not args or args[0] not in ALLOWED_COMMANDS:
            raise ValueError(f"Comando Docker no permitido: {args[:1]}")
        if args[0] == "exec":
            program = next((item for item in args[1:] if not item.startswith("-")), None)
            inner = args[args.index(program) + 1 :] if program else []
            if not inner or inner[0] not in EXEC_PROGRAMS:
                raise ValueError(f"docker exec solo admite {sorted(EXEC_PROGRAMS)}")
        elif FORBIDDEN_WORDS & set(args):
            raise ValueError(f"Comando Docker destructivo no permitido: {args}")
        if args[0] == "compose" and "up" not in args:
            raise ValueError("Solo se permite 'docker compose … up -d'")
        if self._container_guard is not None:
            if args[0] == "compose":
                raise ValueError("docker compose no se permite con la barrera de aislamiento activa")
            if args[0] in {"stop", "start", "exec"}:
                target = next((item for item in args[1:] if not item.startswith("-")), None)
                self._container_guard(target or "")
        return self._runner(list(args))

    def inspect(self, name: str) -> ContainerState:
        code, output = self.run(["inspect", "--type", "container", name])
        if code != 0:
            return ContainerState(name, "missing", None, None)
        state = json.loads(output)[0]["State"]
        health = (state.get("Health") or {}).get("Status")
        return ContainerState(name, state.get("Status", "unknown"), health, state.get("StartedAt"))

    def select(self, container: str, user: str, database: str, sql: str) -> list[list[str]]:
        """Consulta de solo lectura en una base (`psql -tA`); rechaza todo lo que no sea un SELECT."""
        statement = sql.strip().rstrip(";")
        if not statement.upper().startswith("SELECT") or ";" in statement:
            raise ValueError("Solo se admiten consultas SELECT únicas")
        code, output = self.run(["exec", container, "psql", "-U", user, "-d", database, "-v", "ON_ERROR_STOP=1", "-tAF", "\t", "-c", statement])
        if code != 0:
            raise RuntimeError(f"La consulta en {container} falló: {output.strip()[:200]}")
        return [line.split("\t") for line in output.splitlines() if line.strip()]

    def stop(self, name: str) -> None:
        self._on_event("stop", {"container": name})
        code, output = self.run(["stop", name])
        if code != 0:
            raise RuntimeError(f"No se pudo detener {name}: {output.strip()[:200]}")

    def start(self, name: str) -> bool:
        self._on_event("start", {"container": name})
        code, _ = self.run(["start", name])
        return code == 0

    def wait_healthy(self, name: str, health: Callable[[], bool] | None = None) -> float:
        """Espera `running` + `healthy` (si hay healthcheck) y, si se pasa, `health()`; devuelve segundos."""
        started = self._clock()
        deadline = started + self.health_timeout
        while True:
            state = self.inspect(name)
            ready = state.healthy
            if ready and health is not None:
                try:
                    ready = bool(health())
                except Exception:  # noqa: BLE001 - mientras arranca, cualquier error es "aún no"
                    ready = False
            if ready:
                return self._clock() - started
            if self._clock() >= deadline:
                raise RestoreError(f"{name} no quedó sano en {self.health_timeout:.0f} s (estado {state.status}/{state.health})")
            self._sleep(POLL_SECONDS)

    @contextmanager
    def stopped(self, name: str, health: Callable[[], bool] | None = None) -> Iterator[ContainerState]:
        """Detiene `name` y lo arranca en `finally`, esperando su salud (180 s)."""
        before = self.inspect(name)
        self.stop(name)
        try:
            yield before
        finally:
            if not self.start(name):
                raise RestoreError(f"No se pudo arrancar {name}")
            self.wait_healthy(name, health)

    def snapshot(self, names: Iterable[str]) -> dict[str, ContainerState]:
        return {name: self.inspect(name) for name in names}

    def restore_all(self, snapshot: dict[str, ContainerState]) -> RestoreReport:
        """Arranca los contenedores que estaban sanos al inicio y ya no están en ejecución."""
        report = RestoreReport()
        for name, before in snapshot.items():
            if not before.healthy:
                continue
            current = self.inspect(name)
            if current.status == "running":
                continue
            if not self.start(name):
                report.failed.append(name)
                continue
            try:
                self.wait_healthy(name)
            except RestoreError:
                report.failed.append(name)
            else:
                report.restored.append(name)
        return report
