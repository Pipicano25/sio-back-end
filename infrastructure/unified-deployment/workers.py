"""Proceso de workers del despliegue unificado: los 11 procesos auxiliares en hilos.

`supervisor.py` lo arranca después de la API (`python workers.py`). Cada worker conserva
su código: el `audit-outbox-worker` usa el `Worker` y el `run_once` de `sio_audit` sin cambios
(con turno de entrega, ver `AUDIT_SEMAPHORE`), y los demás ejecutan el `run_cycle` de su módulo con los mismos objetos que arma su `main()`
y el mismo bucle (ciclo, log, espera del intervalo). No se usa `main()` directamente
porque instala manejadores de señal, que solo funcionan en el hilo principal.

Por qué hilos en un solo proceso y no un proceso por worker: cada proceso de Python con
su servicio importado ocupa 43–80 MiB; los 11 suman ≈ 610 MiB, más que los 512 MiB de
Render Free. Los workers pasan casi todo el tiempo esperando (base o HTTP), así que los
hilos no compiten por CPU con la API, que está en otro proceso.

Configuración: cada worker se construye con el entorno de su servicio (`registry.py`),
uno tras otro y antes de arrancar ningún hilo; después ya no lee el entorno.

- `SIO_UNIFIED_WORKERS`: `all` (por defecto), `none` o nombres separados por comas.
- Un worker con configuración inválida no arranca y queda `config_error` en el estado;
  los demás siguen. Si un ciclo lanza una excepción que el bucle original no atrapa,
  el hilo se reinicia con espera creciente (1 s … 60 s).
- `SIGTERM`/`SIGINT`: cada worker termina su ciclo en curso y el proceso sale.
- Un bloqueo de archivo impide un segundo proceso de workers en el contenedor.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from registry import SERVICES_BY_PREFIX, Service, service_environment, state_dir, temporary_environment

logger = logging.getLogger("sio_unified.workers")

LOG_FORMAT = "%(asctime)s %(levelname)s [worker=%(threadName)s] [%(name)s] %(message)s"
RESTART_INITIAL_SECONDS = 1.0
RESTART_MAX_SECONDS = 60.0
STABLE_RUN_SECONDS = 300.0  # tras este tiempo sin fallar, la espera de reinicio vuelve a 1 s
STATUS_INTERVAL_SECONDS = 5.0


class Loop:
    """Un worker construido: `run(stop)` hasta que `stop` se activa; `reset()` tras un fallo."""

    interval_seconds: float

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        """Descarta conexiones del pool, como lo haría un proceso nuevo."""

    def close(self) -> None:
        self.reset()


# ----------------------------------------------------------------- audit-outbox-worker (sio-audit)

# Ciclos de entrega simultáneos a Audit entre los 7 workers (SIO_UNIFIED_AUDIT_CONCURRENCY; 0 = sin límite).
# Audit está en este mismo contenedor: con 0,1 CPU, 7 lotes a la vez agotan el tiempo de espera de
# todos y ninguno avanza. El turno se toma ANTES de que `run_once` abra su transacción: ningún worker
# espera a los demás con filas bloqueadas ni con una transacción abierta en su base.
AUDIT_SEMAPHORE: threading.BoundedSemaphore | None = None


class AuditOutboxLoop(Loop):
    def __init__(self, env: Mapping[str, str], heartbeat_file: str) -> None:
        from sio_audit.worker.loop import Worker
        from sio_audit.worker.settings import WorkerSettings

        # Un latido por worker: el valor por defecto (/tmp/sio-audit-worker.heartbeat) lo compartirían los 7.
        settings = WorkerSettings.from_env({**env, "AUDIT_OUTBOX_HEARTBEAT_FILE": heartbeat_file})
        self.worker = Worker(settings)
        self.interval_seconds = settings.poll_interval_seconds
        self.heartbeat_max_age = settings.heartbeat_max_age_seconds
        if AUDIT_SEMAPHORE is not None:
            # puede esperar su turno mientras los otros seis entregan un lote cada uno
            self.heartbeat_max_age += (len(AUDIT_EMITTERS) - 1) * settings.http_timeout_seconds

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        if AUDIT_SEMAPHORE is None:
            self.worker.stop_event = stop  # Worker.run() comprueba este evento entre ciclos
            self.worker.run()  # escribe su propio latido en cada ciclo; ver WorkerThread.last_beat
            return
        # El mismo bucle que `Worker.run()` (ciclo, log, latido, espera), con el turno alrededor de `run_once`.
        from sio_audit.worker.loop import logger as audit_logger
        from sio_audit.worker.loop import run_once, write_heartbeat

        worker, settings = self.worker, self.worker.settings
        audit_logger.info("audit-outbox-worker iniciado cliente=%s", settings.client_id)
        while not stop.is_set():
            try:
                with AUDIT_SEMAPHORE:
                    result = run_once(worker.engine, worker.client, settings)
                if result.selected:
                    audit_logger.info(
                        "Ciclo de outbox seleccionados=%s enviados=%s reintentos=%s rechazados=%s",
                        result.selected, len(result.sent), len(result.retried), len(result.rejected),
                    )
            except Exception as exc:  # noqa: BLE001 — como el original: la base del emisor puede estar caída
                audit_logger.error("Ciclo de outbox fallido causa=%s", type(exc).__name__)
            write_heartbeat(settings.heartbeat_file)
            stop.wait(settings.poll_interval_seconds)
        audit_logger.info("audit-outbox-worker detenido")

    def reset(self) -> None:
        self.worker.engine.dispose()


# ----------------------------------------------------------------- Purchase y Sales


class PurchaseReconcilerLoop(Loop):
    """`python -m purchase_service.reconciler` sin `--once` ni `--check`."""

    def __init__(self) -> None:
        from purchase_service import reconciler
        from purchase_service.main import build_inventory, build_token_provider

        reconciler.configure_logging()
        self.module = reconciler
        self.settings = reconciler.load_settings()
        self.database = reconciler.Database(
            self.settings.database_url, lock_timeout_seconds=self.settings.lock_timeout_seconds
        )
        self.inventory = build_inventory(self.settings, build_token_provider(self.settings))()
        self.interval_seconds = self.settings.reconciler_interval_seconds

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        log = self.module.logger
        while True:
            try:
                result = self.module.run_cycle(self.database, self.inventory, self.settings)
                if result.claimed:
                    log.info(
                        "Ciclo de conciliación tomadas=%s completadas=%s fallidas=%s sin_cambios=%s",
                        result.claimed, len(result.completed), len(result.failed), len(result.unchanged),
                    )
            except Exception:  # noqa: BLE001 — como el original: el proceso no muere por un ciclo fallido
                log.exception("Ciclo de conciliación fallido")
            beat()
            if stop.wait(self.interval_seconds):
                break

    def reset(self) -> None:
        self.database.dispose()


class SalesReconcilerLoop(Loop):
    """`python -m sales_service.reconciler` sin `--once` ni `--check`."""

    def __init__(self) -> None:
        from sales_service import reconciler
        from sales_service.main import build_inventory, build_token_provider

        reconciler.configure_logging()
        self.module = reconciler
        self.settings = reconciler.load_settings()
        self.database = reconciler.Database(
            self.settings.database_url, lock_timeout_seconds=self.settings.lock_timeout_seconds
        )
        self.inventory = build_inventory(self.settings, build_token_provider(self.settings))()
        self.interval_seconds = self.settings.reconciler_interval_seconds

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        log = self.module.logger
        while True:
            try:
                result = self.module.run_cycle(self.database, self.inventory, self.settings)
                if result.claimed:
                    log.info(
                        "Ciclo de conciliación tomadas=%s completadas=%s fallidas=%s compensadas=%s sin_cambios=%s",
                        result.claimed, len(result.completed), len(result.failed),
                        len(result.compensated), len(result.unchanged),
                    )
            except Exception:  # noqa: BLE001
                log.exception("Ciclo de conciliación fallido")
            beat()
            if stop.wait(self.interval_seconds):
                break

    def reset(self) -> None:
        self.database.dispose()


class PurchasePriceUpdateLoop(Loop):
    """`python -m purchase_service.price_update_worker` sin `--once` ni `--check`."""

    def __init__(self) -> None:
        from purchase_service import price_update_worker

        price_update_worker.configure_logging()
        self.module = price_update_worker
        self.settings = price_update_worker.load_settings()
        self.database = price_update_worker.Database(
            self.settings.database_url, lock_timeout_seconds=self.settings.lock_timeout_seconds
        )
        self.gateway = price_update_worker.build_gateway(self.settings)
        self.interval_seconds = self.settings.price_worker_interval_seconds

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        log = self.module.logger
        while True:
            try:
                counts = self.module.run_cycle(self.database, self.gateway, self.settings)
                if any(counts.values()):
                    log.info(
                        "Ciclo de entrega de precios entregadas=%s rechazadas=%s reintento=%s",
                        counts["delivered"], counts["rejected"], counts["retry"],
                    )
            except Exception:  # noqa: BLE001
                log.exception("Ciclo de entrega de precios fallido")
            beat()
            if stop.wait(self.interval_seconds):
                break

    def reset(self) -> None:
        self.database.dispose()


# ----------------------------------------------------------------- Commercial Relationship


class CommercialRelationshipPriceLoop(Loop):
    """`python -m commercial_relationship_service.price_worker` sin `--once` ni `--check`.

    Como el original, una excepción del ciclo termina el bucle (allí, el proceso con código 1 y
    Docker lo reinicia); aquí la atrapa `WorkerThread`, que descarta el pool y lo reinicia.
    """

    def __init__(self) -> None:
        from sqlalchemy import create_engine

        from commercial_relationship_service import price_worker

        self.module = price_worker
        self.settings = price_worker.load_price_worker_settings()
        self.engine = create_engine(self.settings.database_url, pool_pre_ping=True)
        self.interval_seconds = self.settings.interval_seconds

    def run(self, stop: threading.Event, beat: Callable[[], None]) -> None:
        log = self.module.logger
        while not stop.is_set():
            result = self.module.run_cycle(
                self.engine,
                batch_size=self.settings.batch_size,
                max_backoff_seconds=self.settings.max_backoff_seconds,
                interval_seconds=self.settings.interval_seconds,
            )
            if result.processed or result.failed:
                log.info("Ciclo de precios procesadas=%s fallidas=%s", result.processed, result.failed)
            beat()
            stop.wait(self.settings.interval_seconds)

    def reset(self) -> None:
        self.engine.dispose()


# ----------------------------------------------------------------- registro


@dataclass(frozen=True)
class WorkerSpec:
    name: str  # el mismo nombre que el contenedor de Compose (sin el prefijo `sio-`)
    service: str  # prefijo del servicio dueño en `registry.SERVICES`
    kind: str
    build: Callable[[Mapping[str, str], str], Loop]  # (entorno del servicio, archivo de latido)


def _audit(env: Mapping[str, str], heartbeat: str) -> Loop:
    return AuditOutboxLoop(env, heartbeat)  # WorkerSettings.from_env recibe el entorno: no toca os.environ


def _in_env(factory: Callable[[], Loop]) -> Callable[[Mapping[str, str], str], Loop]:
    def build(env: Mapping[str, str], heartbeat: str) -> Loop:  # noqa: ARG001
        with temporary_environment(env):  # `load_settings()` lee os.environ
            return factory()

    return build


AUDIT_EMITTERS = (
    "party-identity", "product-catalog", "operational-context", "commercial-relationship",
    "purchase", "sales", "inventory",
)

WORKERS: tuple[WorkerSpec, ...] = (
    *(
        WorkerSpec(f"{service}-audit-outbox-worker", service, "audit-outbox", _audit)
        for service in AUDIT_EMITTERS
    ),
    WorkerSpec("purchase-reconciler", "purchase", "reconciler", _in_env(PurchaseReconcilerLoop)),
    WorkerSpec("sales-reconciler", "sales", "reconciler", _in_env(SalesReconcilerLoop)),
    WorkerSpec("purchase-price-update-worker", "purchase", "price-delivery", _in_env(PurchasePriceUpdateLoop)),
    WorkerSpec("commercial-relationship-price-worker", "commercial-relationship", "price-application",
               _in_env(CommercialRelationshipPriceLoop)),
)

WORKERS_BY_NAME = {spec.name: spec for spec in WORKERS}


def selected_workers(value: str) -> list[WorkerSpec]:
    value = value.strip().lower() or "all"
    if value == "all":
        return list(WORKERS)
    if value == "none":
        return []
    names = [name.strip() for name in value.split(",") if name.strip()]
    unknown = [name for name in names if name not in WORKERS_BY_NAME]
    if unknown:
        raise ValueError(f"SIO_UNIFIED_WORKERS: nombres desconocidos {unknown}; válidos: {sorted(WORKERS_BY_NAME)}")
    return [spec for spec in WORKERS if spec.name in names]


def worker_environment(spec: WorkerSpec, environ: Mapping[str, str]) -> dict[str, str]:
    service: Service = SERVICES_BY_PREFIX[spec.service]
    return service_environment(service, environ)


# ----------------------------------------------------------------- ejecución


@dataclass
class WorkerThread:
    spec: WorkerSpec
    heartbeat_file: str
    loop: Loop | None = None
    error: str | None = None  # configuración inválida: no arranca
    thread: threading.Thread | None = None
    restarts: int = 0
    last_failure: str | None = None
    last_failure_at: float = 0.0
    last_beat: float = 0.0
    started_at: float = field(default_factory=time.time)

    def beat(self) -> None:
        self.last_beat = time.time()

    def current_beat(self) -> float:
        if isinstance(self.loop, AuditOutboxLoop):  # el Worker de sio-audit escribe su propio latido
            try:
                return float(Path(self.heartbeat_file).read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return 0.0
        return self.last_beat

    def max_beat_age(self) -> float:
        if self.loop is None:
            return 0.0
        if isinstance(self.loop, AuditOutboxLoop):
            return self.loop.heartbeat_max_age
        # un ciclo de conciliación o de precios puede tardar: intervalo × 3 + 60 s de margen
        return 3 * self.loop.interval_seconds + 60

    def run_forever(self, stop: threading.Event) -> None:
        assert self.loop is not None
        delay = RESTART_INITIAL_SECONDS
        while not stop.is_set():
            started = time.monotonic()
            try:
                self.loop.run(stop, self.beat)
                if stop.is_set():
                    break
                raise RuntimeError("el bucle terminó sin señal de parada")
            except Exception as exc:  # noqa: BLE001 — se registra y se reinicia el worker, no el proceso
                self.restarts += 1
                self.last_failure = type(exc).__name__
                self.last_failure_at = time.time()
                logger.error(
                    "Worker detenido por un fallo; se reinicia en %.0f s causa=%s reinicios=%s",
                    delay, type(exc).__name__, self.restarts, exc_info=True,
                )
                try:
                    self.loop.reset()
                except Exception:  # noqa: BLE001
                    logger.warning("No se pudo descartar el pool del worker", exc_info=True)
                if time.monotonic() - started > STABLE_RUN_SECONDS:
                    delay = RESTART_INITIAL_SECONDS
                if stop.wait(delay):
                    break
                delay = min(delay * 2, RESTART_MAX_SECONDS)
        try:
            self.loop.close()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Worker detenido")

    def status(self, now: float) -> dict[str, Any]:
        alive = bool(self.thread and self.thread.is_alive())
        beat = self.current_beat()
        fresh = beat > 0 and now - beat <= self.max_beat_age()
        starting = beat == 0 and now - self.started_at <= self.max_beat_age()
        restarting = self.last_failure_at > beat  # falló después de su último ciclo completo
        if self.error:
            state = "config_error"
        elif not alive:
            state = "stopped"
        else:
            state = "restarting" if restarting else "running"
        return {
            "service": self.spec.service,
            "kind": self.spec.kind,
            "state": state,
            "healthy": state == "running" and (fresh or starting),
            "last_cycle_at": datetime.fromtimestamp(beat, UTC).isoformat() if beat else None,
            "restarts": self.restarts,
            "last_failure": self.last_failure,
            "error": self.error,
        }


_CREDENTIALS = re.compile(r"(://[^:/@\s]+:)[^@\s]+@")


def _mask(text: str) -> str:
    """Oculta la contraseña de cualquier URL con credenciales (p. ej. un DATABASE_URL mal formado)."""
    return _CREDENTIALS.sub(r"\1***@", text)


def write_status(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def acquire_lock(path: Path):
    handle = open(path, "w")  # noqa: SIM115 — se mantiene abierto mientras viva el proceso
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stdout)


def tag_service_loggers() -> None:
    """Purchase y Sales agregan su propio handler (con trace_id) al construirse: se les añade el nombre
    del worker y no se propagan a la raíz para no duplicar líneas. Se llama después de construirlos."""
    for name in ("purchase_service", "sales_service"):
        service_logger = logging.getLogger(name)
        service_logger.propagate = False
        for handler in service_logger.handlers:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s [worker=%(threadName)s] [%(name)s] trace_id=%(trace_id)s %(message)s"
            ))


def main() -> int:
    global AUDIT_SEMAPHORE
    configure_logging()
    root = Path(state_dir())
    (root / "heartbeat").mkdir(parents=True, exist_ok=True)
    status_path = root / "workers.json"

    lock = acquire_lock(root / "workers.lock")
    if lock is None:
        logger.error("Ya hay un proceso de workers en este contenedor; no se arranca otro")
        return 3

    try:
        specs = selected_workers(os.environ.get("SIO_UNIFIED_WORKERS", "all"))
    except ValueError as exc:
        logger.error("%s", exc)
        return 2
    if not specs:
        write_status(status_path, {"enabled": False, "written_at": time.time(), "workers": {}})
        logger.info("SIO_UNIFIED_WORKERS=none: no se arranca ningún worker")
        return 0

    # Con poca CPU, la API va primero: el planificador da menos tiempo a este proceso cuando compiten.
    try:
        os.nice(int(os.environ.get("SIO_UNIFIED_WORKERS_NICE", "10")))
    except (OSError, ValueError):
        logger.warning("No se pudo bajar la prioridad del proceso de workers")
    concurrency = int(os.environ.get("SIO_UNIFIED_AUDIT_CONCURRENCY", "1"))
    AUDIT_SEMAPHORE = threading.BoundedSemaphore(concurrency) if concurrency > 0 else None

    environ = dict(os.environ)
    threads: list[WorkerThread] = []
    for spec in specs:  # uno tras otro y antes de cualquier hilo: temporary_environment no es concurrente
        item = WorkerThread(spec, str(root / "heartbeat" / spec.name))
        try:
            item.loop = spec.build(worker_environment(spec, environ), item.heartbeat_file)
        except Exception as exc:  # noqa: BLE001 — configuración inválida: este worker no arranca
            item.error = type(exc).__name__  # /health/workers es público: solo el tipo
            logger.error("Worker %s no arranca: %s: %s", spec.name, item.error, _mask(str(exc))[:300])
        threads.append(item)

    tag_service_loggers()

    stop = threading.Event()
    for signal_number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signal_number, lambda *_: stop.set())

    for item in threads:
        if item.loop is not None:
            item.thread = threading.Thread(target=item.run_forever, args=(stop,), name=item.spec.name, daemon=True)
            item.thread.start()
    logger.info(
        "Workers en ejecución=%s con_error=%s",
        sum(1 for item in threads if item.thread), sum(1 for item in threads if item.error),
    )

    def publish() -> None:
        now = time.time()
        write_status(status_path, {
            "enabled": True, "pid": os.getpid(), "written_at": now,
            "workers": {item.spec.name: item.status(now) for item in threads},
        })

    publish()
    while not stop.wait(STATUS_INTERVAL_SECONDS):
        publish()

    timeout = float(os.environ.get("SIO_UNIFIED_WORKERS_STOP_TIMEOUT", "12"))
    deadline = time.monotonic() + timeout
    logger.info("Deteniendo workers (máximo %.0f s)", timeout)
    for item in threads:
        if item.thread:
            item.thread.join(max(deadline - time.monotonic(), 0))
    pending = [item.spec.name for item in threads if item.thread and item.thread.is_alive()]
    if pending:
        logger.warning("Workers que no terminaron su ciclo a tiempo: %s", pending)
    publish()
    logger.info("Proceso de workers detenido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
