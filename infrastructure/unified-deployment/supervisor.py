"""Proceso principal (PID 1) del contenedor unificado: arranca y vigila la API y los workers.

    python supervisor.py

1. Arranca la API (`uvicorn main:app` en `$PORT`) y espera a que `/health/live` responda.
2. Después arranca el proceso de workers (`workers.py`), salvo `SIO_UNIFIED_WORKERS=none`.
   Los workers llaman a la API por 127.0.0.1, por eso van segundos; además así no compiten
   por la CPU durante el arranque lento de las 12 aplicaciones.
3. Si un proceso termina sin que se haya pedido, lo vuelve a arrancar con espera creciente
   (1 s … 60 s; vuelve a 1 s tras 5 min estable). Un fallo de los workers nunca detiene la API.
4. `SIGTERM`/`SIGINT` (Render envía `SIGTERM` y espera 30 s): detiene primero los workers (cada
   uno termina su ciclo), luego la API (termina las peticiones en curso) y fuerza lo que quede al
   agotar `SIO_UNIFIED_SHUTDOWN_TIMEOUT` (25 s por defecto).

Solo usa la biblioteca estándar, para ocupar poca memoria. Un bloqueo de archivo impide un
segundo supervisor en el mismo contenedor.
"""

from __future__ import annotations

import fcntl
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("sio_unified.supervisor")

HERE = Path(__file__).resolve().parent
RESTART_INITIAL_SECONDS = 1.0
RESTART_MAX_SECONDS = 60.0
STABLE_RUN_SECONDS = 300.0


def _number(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


@dataclass
class Child:
    name: str
    command: list[str]
    process: subprocess.Popen | None = None
    started_at: float = 0.0
    restarts: int = 0
    delay: float = RESTART_INITIAL_SECONDS
    next_start_at: float = 0.0
    history: list[int] = field(default_factory=list)

    def start(self) -> None:
        self.process = subprocess.Popen(self.command, cwd=HERE)  # hereda stdout/stderr y el entorno
        self.started_at = time.monotonic()
        logger.info("%s arrancado pid=%s", self.name, self.process.pid)

    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def check(self, now: float) -> None:
        """Si terminó sin que se pidiera, programa y hace el rearranque con espera creciente."""
        if self.process is None:
            if now >= self.next_start_at:
                self.start()
            return
        code = self.process.poll()
        if code is None:
            return
        ran = now - self.started_at
        self.restarts += 1
        self.history = (self.history + [code])[-10:]
        if ran > STABLE_RUN_SECONDS:
            self.delay = RESTART_INITIAL_SECONDS
        logger.error(
            "%s terminó código=%s tras %.0f s; se rearranca en %.0f s (reinicios=%s)",
            self.name, code, ran, self.delay, self.restarts,
        )
        self.process = None
        self.next_start_at = now + self.delay
        self.delay = min(self.delay * 2, RESTART_MAX_SECONDS)

    def stop(self, deadline: float) -> None:
        if not self.running():
            return
        assert self.process is not None
        logger.info("Deteniendo %s pid=%s", self.name, self.process.pid)
        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=max(deadline - time.monotonic(), 0.1))
            logger.info("%s detenido código=%s", self.name, self.process.returncode)
        except subprocess.TimeoutExpired:
            logger.warning("%s no terminó a tiempo; se fuerza (SIGKILL)", self.name)
            self.process.kill()
            self.process.wait()


def api_is_live(port: str) -> bool:
    """`GET /health/live` por socket (urllib carga ssl y http: ≈ 15 MiB más en el proceso PID 1)."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=2) as connection:
            connection.sendall(b"GET /health/live HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
            return connection.recv(64).split(b" ", 2)[1:2] == [b"200"]
    except (OSError, ValueError):
        return False


def acquire_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "w")  # noqa: SIM115 — se mantiene abierto mientras viva el proceso
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, stream=sys.stdout,
        format="%(asctime)s %(levelname)s [supervisor] %(message)s",
    )
    state_dir = Path(os.environ.get("SIO_UNIFIED_STATE_DIR", "").strip() or "/tmp/sio-unified")
    lock = acquire_lock(state_dir / "supervisor.lock")
    if lock is None:
        logger.error("Ya hay un supervisor en este contenedor; no se arranca otro")
        return 3
    (state_dir / "workers.json").unlink(missing_ok=True)  # estado de una ejecución anterior

    port = os.environ.get("PORT", "8000")
    graceful = str(int(_number("SIO_UNIFIED_API_GRACEFUL_SECONDS", 10)))
    api = Child("api", [
        sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", port,
        "--timeout-graceful-shutdown", graceful,
    ])
    workers_enabled = os.environ.get("SIO_UNIFIED_WORKERS", "all").strip().lower() != "none"
    workers = Child("workers", [sys.executable, "workers.py"])
    start_timeout = _number("SIO_UNIFIED_API_START_TIMEOUT", 300)

    stopping = threading.Event()
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_number, lambda number, _frame: stopping.set())

    api.start()
    began = time.monotonic()
    while not stopping.is_set() and not api_is_live(port):
        api.check(time.monotonic())
        if time.monotonic() - began > start_timeout:
            logger.warning("La API no respondió en %.0f s; se arrancan los workers igualmente", start_timeout)
            break
        stopping.wait(1)
    if not stopping.is_set():
        logger.info("API lista en %.1f s", time.monotonic() - began)
        if workers_enabled:
            workers.start()
        else:
            logger.info("SIO_UNIFIED_WORKERS=none: solo la API")

    while not stopping.wait(1):
        now = time.monotonic()
        api.check(now)
        if workers_enabled:
            workers.check(now)

    timeout = _number("SIO_UNIFIED_SHUTDOWN_TIMEOUT", 25)
    deadline = time.monotonic() + timeout
    logger.info("Señal de parada: se detienen workers y API (máximo %.0f s)", timeout)
    workers.stop(min(deadline, time.monotonic() + timeout * 0.6))
    api.stop(deadline)
    logger.info("Contenedor detenido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
