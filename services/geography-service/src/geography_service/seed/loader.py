"""Carga idempotente del catálogo geográfico inicial."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from geography_service.infrastructure.models import (
    GlobalAdministrativeDivisionModel,
    GlobalCityModel,
    GlobalCountryModel,
)
from geography_service.seed.constants import (
    SEED_ACTOR,
)


SEED_NAMESPACE = UUID(
    "0dbeebec-5f29-43da-94e7-24e192938abe"
)


@dataclass(slots=True)
class SeedStats:
    """Representa las estadísticas de una ejecución del seed.

    Attributes:
        countries_created: Países creados.
        countries_skipped: Países existentes reutilizados.
        divisions_created: Divisiones creadas.
        divisions_skipped: Divisiones existentes reutilizadas.
        cities_created: Ciudades creadas.
        cities_skipped: Ciudades existentes reutilizadas.
    """

    countries_created: int = 0
    countries_skipped: int = 0

    divisions_created: int = 0
    divisions_skipped: int = 0

    cities_created: int = 0
    cities_skipped: int = 0


class SouthAmericaSeedLoader:
    """Carga el snapshot normalizado de Sudamérica en PostgreSQL."""

    def __init__(
        self,
        session: Session,
        *,
        actor_id: str = SEED_ACTOR,
        batch_size: int = 1000,
    ) -> None:
        """Inicializa el cargador.

        Args:
            session: Sesión SQLAlchemy utilizada por la carga.
            actor_id: Actor técnico almacenado en la auditoría.
            batch_size: Cantidad de ciudades procesadas entre flushes.
        """
        self.session = session
        self.actor_id = actor_id
        self.batch_size = batch_size

    def load(
        self,
        *,
        data_dir: Path,
    ) -> SeedStats:
        """Carga países, divisiones y ciudades respetando las relaciones.

        Args:
            data_dir: Directorio que contiene los CSV normalizados.

        Returns:
            Estadísticas de registros creados y reutilizados.
        """
        stats = SeedStats()

        countries = self._load_countries(
            data_dir / "countries.csv",
            stats,
        )

        divisions = self._load_divisions(
            data_dir
            / "administrative_divisions.csv",
            countries,
            stats,
        )

        self._load_cities(
            data_dir / "cities.csv",
            countries,
            divisions,
            stats,
        )

        self.session.commit()

        return stats

    def _load_countries(
        self,
        path: Path,
        stats: SeedStats,
    ) -> dict[str, UUID]:
        """Carga países y construye un índice ISO2 a UUID.

        Args:
            path: CSV de países.
            stats: Estadísticas acumuladas.

        Returns:
            Mapeo entre código ISO2 y UUID persistido.
        """
        result: dict[str, UUID] = {}

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as source:
            for row in csv.DictReader(source):
                iso2_code = row["iso2_code"]

                model = self.session.scalar(
                    select(
                        GlobalCountryModel,
                    ).where(
                        GlobalCountryModel.iso2_code
                        == iso2_code
                    )
                )

                if model is None:
                    model = GlobalCountryModel(
                        id=uuid5(
                            SEED_NAMESPACE,
                            f"country:{iso2_code}",
                        ),
                        iso2_code=iso2_code,
                        iso3_code=row["iso3_code"],
                        name=row["name"],
                        phone_prefix=(
                            row["phone_prefix"]
                            or None
                        ),
                        status=row["status"],
                        created_by=self.actor_id,
                        updated_by=self.actor_id,
                    )

                    self.session.add(
                        model,
                    )

                    self.session.flush()

                    stats.countries_created += 1

                else:
                    stats.countries_skipped += 1

                result[iso2_code] = model.id

        return result

    def _load_divisions(
        self,
        path: Path,
        countries: dict[str, UUID],
        stats: SeedStats,
    ) -> dict[tuple[str, str], UUID]:
        """Carga divisiones administrativas de primer nivel.

        Args:
            path: CSV de divisiones.
            countries: Índice ISO2 a UUID de país.
            stats: Estadísticas acumuladas.

        Returns:
            Índice de ``(country_iso2, admin1_code)`` a UUID.
        """
        result: dict[
            tuple[str, str],
            UUID,
        ] = {}

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as source:
            for row in csv.DictReader(source):
                country_iso2 = row[
                    "country_iso2"
                ]

                country_id = countries[
                    country_iso2
                ]

                code = row["code"]

                model = self.session.scalar(
                    select(
                        GlobalAdministrativeDivisionModel,
                    ).where(
                        GlobalAdministrativeDivisionModel.country_id
                        == country_id,
                        GlobalAdministrativeDivisionModel.code
                        == code,
                    )
                )

                if model is None:
                    model = self.session.scalar(
                        select(
                            GlobalAdministrativeDivisionModel,
                        ).where(
                            GlobalAdministrativeDivisionModel.country_id
                            == country_id,
                            func.lower(
                                GlobalAdministrativeDivisionModel.name
                            )
                            == row["name"].lower(),
                        )
                    )

                if model is None:
                    model = GlobalAdministrativeDivisionModel(
                        id=uuid5(
                            SEED_NAMESPACE,
                            (
                                "division:"
                                f"{country_iso2}:"
                                f"{row['admin1_code']}"
                            ),
                        ),
                        country_id=country_id,
                        parent_division_id=None,
                        code=code,
                        name=row["name"],
                        division_type=row[
                            "division_type"
                        ],
                        status=row["status"],
                        created_by=self.actor_id,
                        updated_by=self.actor_id,
                    )

                    self.session.add(
                        model,
                    )

                    self.session.flush()

                    stats.divisions_created += 1

                else:
                    stats.divisions_skipped += 1

                result[
                    (
                        country_iso2,
                        row["admin1_code"],
                    )
                ] = model.id

        return result

    def _load_cities(
        self,
        path: Path,
        countries: dict[str, UUID],
        divisions: dict[
            tuple[str, str],
            UUID,
        ],
        stats: SeedStats,
    ) -> None:
        """Carga las ciudades del snapshot.

        Args:
            path: CSV normalizado de ciudades.
            countries: Índice ISO2 a UUID de país.
            divisions: Índice de divisiones administrativas.
            stats: Estadísticas acumuladas.

        Raises:
            RuntimeError: Si una ciudad referencia una división ADM1 que no
                fue encontrada durante la preparación.
        """
        processed = 0

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as source:
            for row in csv.DictReader(source):
                country_iso2 = row[
                    "country_iso2"
                ]

                country_id = countries[
                    country_iso2
                ]

                admin1_code = row[
                    "admin1_code"
                ]

                division_id: UUID | None = None

                if admin1_code:
                    division_id = divisions.get(
                        (
                            country_iso2,
                            admin1_code,
                        )
                    )

                    if division_id is None:
                        raise RuntimeError(
                            "No fue posible resolver la división "
                            f"{country_iso2}.{admin1_code} "
                            f"para la ciudad {row['name']}."
                        )

                city_id = uuid5(
                    SEED_NAMESPACE,
                    f"city:geonames:{row['source_id']}",
                )

                model = self.session.get(
                    GlobalCityModel,
                    city_id,
                )

                if model is None:
                    model = self._find_existing_city(
                        country_id=country_id,
                        division_id=division_id,
                        name=row["name"],
                    )

                if model is not None:
                    stats.cities_skipped += 1
                    continue

                model = GlobalCityModel(
                    id=city_id,
                    country_id=country_id,
                    administrative_division_id=division_id,
                    code=(
                        row["code"]
                        or None
                    ),
                    name=row["name"],
                    latitude=Decimal(
                        row["latitude"],
                    ),
                    longitude=Decimal(
                        row["longitude"],
                    ),
                    status=row["status"],
                    created_by=self.actor_id,
                    updated_by=self.actor_id,
                )

                self.session.add(
                    model,
                )

                stats.cities_created += 1
                processed += 1

                if (
                    processed
                    % self.batch_size
                    == 0
                ):
                    self.session.flush()

        self.session.flush()

    def _find_existing_city(
        self,
        *,
        country_id: UUID,
        division_id: UUID | None,
        name: str,
    ) -> GlobalCityModel | None:
        """Busca una ciudad existente antes de insertar datos del seed.

        Esta comprobación permite reutilizar datos que pudieron haberse
        creado manualmente antes de introducir el proceso de carga inicial.

        Args:
            country_id: País propietario de la ciudad.
            division_id: División administrativa asociada.
            name: Nombre de la ciudad.

        Returns:
            Ciudad encontrada o None.
        """
        statement = select(
            GlobalCityModel,
        ).where(
            GlobalCityModel.country_id
            == country_id,
            func.lower(
                GlobalCityModel.name,
            )
            == name.lower(),
        )

        if division_id is None:
            statement = statement.where(
                GlobalCityModel.administrative_division_id.is_(
                    None
                )
            )
        else:
            statement = statement.where(
                GlobalCityModel.administrative_division_id
                == division_id
            )

        matches = self.session.scalars(
            statement,
        ).all()

        if len(matches) == 1:
            return matches[0]

        return None
