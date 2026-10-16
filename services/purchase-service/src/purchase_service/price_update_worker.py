"""Worker de entrega de solicitudes de precio a Commercial Relationship (spec 021, EXC-001).

`python -m purchase_service.price_update_worker`:

- Sin argumentos: bucle con `PURCHASE_PRICE_WORKER_INTERVAL_SECONDS` entre ciclos.
- `--once`: un ciclo y termina (pruebas y operación manual).
- `--check`: comprobación de salud (configuración y base disponibles) para el healthcheck.

Entrega con la identidad técnica de Purchase (`client_credentials`, D5). Los logs no incluyen tokens ni el contenido
de las solicitudes.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from datetime import UTC, datetime

from dotenv import load_dotenv

from purchase_service.application.price_update_delivery import PriceUpdateDeliveryService
from purchase_service.application.ports import CommercialPricingGateway
from purchase_service.config import Settings, load_settings
from purchase_service.infrastructure.database import Database
from purchase_service.infrastructure.repository import PurchaseRepository
from purchase_service.observability import SERVICE_LOGGER, configure_logging

logger = logging.getLogger(SERVICE_LOGGER)


def run_cycle(database: Database, gateway: CommercialPricingGateway, settings: Settings) -> dict[str, int]:
    with database.session_factory() as session:
        repository = PurchaseRepository(session, lock_timeout_ms=database.lock_timeout_ms)
        service = PriceUpdateDeliveryService(
            repository,
            gateway,
            interval_seconds=settings.price_worker_interval_seconds,
            max_backoff_seconds=settings.price_worker_max_backoff_seconds,
            clock=lambda: datetime.now(UTC),
        )
        return service.run_once()


def build_gateway(settings: Settings) -> CommercialPricingGateway:
    from purchase_service.infrastructure.commercial_pricing_gateway import HTTPCommercialPricingGateway
    from purchase_service.main import build_token_provider

    return HTTPCommercialPricingGateway(
        base_url=settings.commercial_relationship_base_url,
        timeout_seconds=settings.commercial_relationship_timeout_seconds,
        tokens=build_token_provider(settings),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="purchase_service.price_update_worker")
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
            logger.error("Worker de precios no preparado: base de datos no disponible")
            return 1
        return 0

    gateway = build_gateway(settings)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    while True:
        try:
            counts = run_cycle(database, gateway, settings)
            if any(counts.values()):
                logger.info(
                    "Ciclo de entrega de precios entregadas=%s rechazadas=%s reintento=%s",
                    counts["delivered"], counts["rejected"], counts["retry"],
                )
        except Exception:  # noqa: BLE001 — el proceso no muere por un ciclo fallido
            logger.exception("Ciclo de entrega de precios fallido")
        if args.once or stop.wait(settings.price_worker_interval_seconds):
            break

    database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
