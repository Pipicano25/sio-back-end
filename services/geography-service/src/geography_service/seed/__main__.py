"""CLI para preparar y cargar datos iniciales de geography-service."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from geography_service.config import Settings
from geography_service.seed.loader import (
    SouthAmericaSeedLoader,
)
from geography_service.seed.preparer import (
    GeoNamesSouthAmericaPreparer,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]


def prepare_data(
    source_dir: Path,
    output_dir: Path,
) -> None:
    """Prepara los archivos normalizados de Sudamérica.

    Args:
        source_dir: Directorio que contiene los archivos GeoNames.
        output_dir: Directorio donde se generará el snapshot SIO.
    """
    preparer = GeoNamesSouthAmericaPreparer()

    stats = preparer.prepare(
        source_dir=source_dir,
        output_dir=output_dir,
    )

    print(
        "Preparación completada: "
        f"{stats.countries} países, "
        f"{stats.administrative_divisions} divisiones, "
        f"{stats.cities} ciudades."
    )


def load_data(
    data_dir: Path,
) -> None:
    """Carga el snapshot normalizado en PostgreSQL.

    Args:
        data_dir: Directorio que contiene los CSV normalizados.
    """
    load_dotenv(
        PROJECT_ROOT / ".env",
        override=False,
    )

    settings = Settings.from_env()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )

    try:
        with Session(engine) as session:
            loader = SouthAmericaSeedLoader(
                session,
            )

            stats = loader.load(
                data_dir=data_dir,
            )

            print(
                "Carga completada:\n"
                f"  Países creados: {stats.countries_created}\n"
                f"  Países existentes: {stats.countries_skipped}\n"
                f"  Divisiones creadas: {stats.divisions_created}\n"
                f"  Divisiones existentes: {stats.divisions_skipped}\n"
                f"  Ciudades creadas: {stats.cities_created}\n"
                f"  Ciudades existentes: {stats.cities_skipped}"
            )

    finally:
        engine.dispose()


def main() -> None:
    """Ejecuta la interfaz de línea de comandos del seed."""
    parser = argparse.ArgumentParser(
        description=(
            "Preparación y carga del catálogo "
            "geográfico inicial de SIO."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Normaliza los archivos GeoNames.",
    )

    prepare_parser.add_argument(
        "--source-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "raw"
        / "geonames",
    )

    prepare_parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "south_america",
    )

    load_parser = subparsers.add_parser(
        "load",
        help="Carga el snapshot normalizado en PostgreSQL.",
    )

    load_parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "south_america",
    )

    args = parser.parse_args()

    if args.command == "prepare":
        prepare_data(
            args.source_dir,
            args.output_dir,
        )

    elif args.command == "load":
        load_data(
            args.data_dir,
        )


if __name__ == "__main__":
    main()
