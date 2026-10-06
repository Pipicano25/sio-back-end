"""`python -m sio_audit.worker` y `python -m sio_audit.worker --check`.

- Sin argumentos: ejecuta el worker hasta recibir `SIGTERM`/`SIGINT`; termina el ciclo
  en curso sin perder filas (la outbox conserva todo lo no confirmado).
- `--check`: código `0` si el latido es reciente (healthcheck del contenedor).
- Configuración inválida → código `2`, para que Docker reinicie y el error quede visible.
"""

from __future__ import annotations

import logging
import signal
import sys

from sio_audit.worker.loop import Worker, heartbeat_is_fresh
from sio_audit.worker.settings import WorkerConfigurationError, WorkerSettings


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    try:
        settings = WorkerSettings.from_env()
    except WorkerConfigurationError as exc:
        logging.getLogger("sio_audit").error("Configuración inválida: %s", exc)
        return 2

    if "--check" in args:
        return 0 if heartbeat_is_fresh(settings) else 1

    worker = Worker(settings)

    def stop(signum, frame) -> None:  # noqa: ARG001
        worker.stop_event.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    worker.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
