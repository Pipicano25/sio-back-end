"""Proceso `commercial-relationship-price-worker` (spec 021: FR-021-22..26; `python -m commercial_relationship_service.price_worker`).

- Sin argumentos: bucle con `CR_PRICE_WORKER_INTERVAL_SECONDS` entre ciclos.
- `--once`: un ciclo y termina (pruebas y operación manual).
- `--check`: comprobación de salud (configuración y base disponibles) para el healthcheck.

Solo usa la base propia: no hace llamadas HTTP ni necesita credenciales técnicas. Registra `updated_by =
system:commercial-relationship-price-worker` y audita con esa identidad (D1, D22). Los logs no incluyen datos
sensibles.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from commercial_relationship_service.application.automatic_price_application_service import (
    WORKER_ACTOR,
    WORKER_USERNAME,
    AutomaticPriceApplicationService,
)
from commercial_relationship_service.audit_context import AuditActor, reset_actor, set_actor
from commercial_relationship_service.config import load_price_worker_settings
from commercial_relationship_service.infrastructure.pricing_repositories import AutomaticPricingRepository

logger = logging.getLogger("commercial_relationship_service.price_worker")


@dataclass
class CycleResult:
    processed: int = 0
    failed: int = 0
    statuses: list[str] = field(default_factory=list)


def run_cycle(engine: Engine, *, batch_size: int, max_backoff_seconds: float, interval_seconds: float) -> CycleResult:
    """Procesa hasta `batch_size` aplicaciones procesables; cada una en su transacción."""
    result = CycleResult()
    token = set_actor(AuditActor(WORKER_ACTOR, WORKER_USERNAME))
    try:
        with Session(engine, expire_on_commit=False) as session:
            ids = AutomaticPricingRepository(session).processable_ids(batch_size)
        for application_id in ids:
            with Session(engine, expire_on_commit=False) as session:
                service = AutomaticPriceApplicationService(
                    AutomaticPricingRepository(session),
                    interval_seconds=interval_seconds,
                    max_backoff_seconds=max_backoff_seconds,
                )
                try:
                    processed = service.process(application_id)
                except Exception as error:  # noqa: BLE001 - se registra y se reintenta (FR-021-26)
                    session.rollback()
                    logger.warning("Aplicación automática fallida id=%s causa=%s", application_id, type(error).__name__)
                    service.fail(application_id, error)
                    result.failed += 1
                    continue
                if processed is not None:
                    result.processed += 1
                    result.statuses.append(processed.status)
    finally:
        reset_actor(token)
    return result


def check(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1 FROM automatic_price_applications LIMIT 1"))
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Worker de precios automáticos de Commercial Relationship (spec 021).")
    parser.add_argument("--once", action="store_true", help="Ejecuta un ciclo y termina")
    parser.add_argument("--check", action="store_true", help="Comprobación de salud")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    settings = load_price_worker_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        if args.check:
            return 0 if check(engine) else 1
        stop = threading.Event()
        for signal_number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signal_number, lambda *_: stop.set())
        while not stop.is_set():
            result = run_cycle(
                engine,
                batch_size=settings.batch_size,
                max_backoff_seconds=settings.max_backoff_seconds,
                interval_seconds=settings.interval_seconds,
            )
            if result.processed or result.failed:
                logger.info("Ciclo de precios procesadas=%s fallidas=%s", result.processed, result.failed)
            if args.once:
                break
            stop.wait(settings.interval_seconds)
        return 0
    except Exception as error:  # noqa: BLE001
        logger.error("Worker de precios detenido causa=%s", type(error).__name__)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
