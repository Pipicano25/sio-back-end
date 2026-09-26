"""Comando de carga inicial: `python -m product_catalog_service.seed load`."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from product_catalog_service.config import load_settings
from product_catalog_service.infrastructure.database import Database
from product_catalog_service.seed.loader import load_seed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m product_catalog_service.seed",
        description="Carga idempotente de los catálogos base de Product Catalog Service.",
    )
    parser.add_argument("command", choices=["load"], help="Operación a ejecutar.")
    parser.parse_args(argv)

    load_dotenv(override=False)
    database = Database(load_settings().database_url)

    try:
        with database.session_factory() as session:
            results = load_seed(session)
    finally:
        database.dispose()

    for result in results:
        print(f"{result.table}: {result.inserted} insertados, {result.skipped} omitidos")

    return 0


if __name__ == "__main__":
    sys.exit(main())
