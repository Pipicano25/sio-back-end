"""Proceso del conciliador de operaciones `PENDING` (`python -m purchase_service.reconciler`; R-08).

- Sin argumentos: bucle con `PURCHASE_RECONCILER_INTERVAL_SECONDS` entre ciclos.
- `--once`: un ciclo y termina (pruebas y operación manual).
- `--check`: comprobación de salud (configuración y base disponibles) para el healthcheck.

Actúa con la identidad técnica de Purchase hacia Inventory y registra `updated_by =
system:purchase-reconciler` (D1, D22). Los logs no incluyen tokens ni datos sensibles.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from datetime import UTC, datetime

from dotenv import load_dotenv

from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.ports import InventoryGateway
from purchase_service.application.reconciliation_service import CycleResult, ReconciliationService
from purchase_service.config import Settings, load_settings
from purchase_service.infrastructure.database import Database
from purchase_service.infrastructure.repository import PurchaseRepository
from purchase_service.infrastructure.sequence_repository import SequenceRepository
from purchase_service.observability import SERVICE_LOGGER, configure_logging

logger = logging.getLogger(SERVICE_LOGGER)


def run_cycle(database: Database, inventory: InventoryGateway, settings: Settings) -> CycleResult:
    with database.session_factory() as session:
        repository = PurchaseRepository(session, lock_timeout_ms=database.lock_timeout_ms)
        clock = lambda: datetime.now(UTC)  # noqa: E731
        engine = OperationEngine(repository, SequenceRepository(session), inventory, clock=clock)
        service = ReconciliationService(
            repository, engine, inventory, threshold_seconds=settings.reconciler_threshold_seconds
        )
        return service.run_once()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="purchase_service.reconciler")
    parser.add_argument("--once", action="store_true", help="Ejecuta un ciclo y termina.")
    parser.add_argument("--check", action="store_true", help="Comprueba configuración y base de datos.")
    args = parser.parse_args(argv)

    load_dotenv(override=False)
    configure_logging()
    settings = load_settings()
    database = Database(settings.database_url, lock_timeout_seconds=settings.lock_timeout_seconds)

    if args.check:
        try:
            database.check_connection()
        except Exception:  # noqa: BLE001
            logger.error("Conciliador no preparado: base de datos no disponible")
            return 1
        return 0

    from purchase_service.main import build_inventory, build_token_provider

    inventory = build_inventory(settings, build_token_provider(settings))()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    while True:
        try:
            result = run_cycle(database, inventory, settings)
            if result.claimed:
                logger.info(
                    "Ciclo de conciliación tomadas=%s completadas=%s fallidas=%s compensadas=%s sin_cambios=%s",
                    result.claimed,
                    len(result.completed),
                    len(result.failed),
                    len(result.compensated),
                    len(result.unchanged),
                )
        except Exception:  # noqa: BLE001 — el proceso no muere por un ciclo fallido
            logger.exception("Ciclo de conciliación fallido")
        if args.once or stop.wait(settings.reconciler_interval_seconds):
            break

    database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
