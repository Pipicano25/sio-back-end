"""Preparación de snapshots GeoNames para geography-service."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from geography_service.seed.constants import (
    SOUTH_AMERICA_COUNTRIES,
)


@dataclass(frozen=True, slots=True)
class PreparationStats:
    """Representa el resultado de preparar los datos geográficos.

    Attributes:
        countries: Cantidad de países preparados.
        administrative_divisions: Cantidad de divisiones preparadas.
        cities: Cantidad de ciudades preparadas.
    """

    countries: int
    administrative_divisions: int
    cities: int


class GeoNamesSouthAmericaPreparer:
    """Normaliza archivos GeoNames al formato utilizado por SIO."""

    def prepare(
        self,
        *,
        source_dir: Path,
        output_dir: Path,
    ) -> PreparationStats:
        """Prepara el snapshot completo de Sudamérica.

        Args:
            source_dir: Directorio que contiene los archivos originales
                descargados desde GeoNames.
            output_dir: Directorio donde se escribirán los CSV normalizados.

        Returns:
            Estadísticas del proceso de preparación.

        Raises:
            FileNotFoundError: Si falta alguno de los archivos requeridos.
            RuntimeError: Si no se encuentra información para alguno de los
                países configurados.
        """
        self._validate_sources(
            source_dir,
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        countries = self._prepare_countries(
            source_dir / "countryInfo.txt",
            output_dir / "countries.csv",
        )

        divisions = self._prepare_divisions(
            source_dir / "admin1CodesASCII.txt",
            output_dir / "administrative_divisions.csv",
        )

        cities = self._prepare_cities(
            source_dir / "cities500.zip",
            output_dir / "cities.csv",
        )

        return PreparationStats(
            countries=countries,
            administrative_divisions=divisions,
            cities=cities,
        )

    @staticmethod
    def _validate_sources(
        source_dir: Path,
    ) -> None:
        """Valida que existan todos los archivos fuente.

        Args:
            source_dir: Directorio de datos originales.

        Raises:
            FileNotFoundError: Si falta un archivo requerido.
        """
        required_files = (
            "countryInfo.txt",
            "admin1CodesASCII.txt",
            "cities500.zip",
        )

        for filename in required_files:
            path = source_dir / filename

            if not path.is_file():
                raise FileNotFoundError(
                    f"No se encontró el archivo requerido: {path}"
                )

    @staticmethod
    def _prepare_countries(
        source_path: Path,
        output_path: Path,
    ) -> int:
        """Normaliza los países soberanos de Sudamérica.

        Args:
            source_path: Archivo countryInfo.txt de GeoNames.
            output_path: Archivo CSV de salida.

        Returns:
            Cantidad de países escritos.

        Raises:
            RuntimeError: Si falta alguno de los países configurados.
        """
        found: dict[str, dict[str, str]] = {}

        with source_path.open(
            "r",
            encoding="utf-8",
        ) as source:
            for line in source:
                if (
                    not line.strip()
                    or line.startswith("#")
                ):
                    continue

                columns = line.rstrip(
                    "\n"
                ).split("\t")

                iso2_code = columns[0]

                if iso2_code not in SOUTH_AMERICA_COUNTRIES:
                    continue

                phone = columns[12].strip()

                if phone:
                    phone = phone.split(",")[0].strip()

                    if not phone.startswith("+"):
                        phone = f"+{phone}"

                found[iso2_code] = {
                    "iso2_code": iso2_code,
                    "iso3_code": columns[1],
                    "name": SOUTH_AMERICA_COUNTRIES[
                        iso2_code
                    ]["name"],
                    "phone_prefix": phone,
                    "status": "ACTIVE",
                }

        missing = (
            set(SOUTH_AMERICA_COUNTRIES)
            - set(found)
        )

        if missing:
            raise RuntimeError(
                "No se encontró información de los países: "
                + ", ".join(sorted(missing))
            )

        with output_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "iso2_code",
                    "iso3_code",
                    "name",
                    "phone_prefix",
                    "status",
                ],
            )

            writer.writeheader()

            for iso2_code in SOUTH_AMERICA_COUNTRIES:
                writer.writerow(
                    found[iso2_code],
                )

        return len(found)

    @staticmethod
    def _prepare_divisions(
        source_path: Path,
        output_path: Path,
    ) -> int:
        """Normaliza las divisiones administrativas de primer nivel.

        Args:
            source_path: Archivo admin1CodesASCII.txt.
            output_path: CSV normalizado de divisiones.

        Returns:
            Cantidad de divisiones escritas.
        """
        count = 0

        with (
            source_path.open(
                "r",
                encoding="utf-8",
            ) as source,
            output_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as target,
        ):
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "country_iso2",
                    "admin1_code",
                    "code",
                    "name",
                    "division_type",
                    "status",
                ],
            )

            writer.writeheader()

            for line in source:
                if not line.strip():
                    continue

                columns = line.rstrip(
                    "\n"
                ).split("\t")

                complete_code = columns[0]

                if "." not in complete_code:
                    continue

                country_iso2, admin1_code = (
                    complete_code.split(
                        ".",
                        maxsplit=1,
                    )
                )

                country_config = (
                    SOUTH_AMERICA_COUNTRIES.get(
                        country_iso2,
                    )
                )

                if country_config is None:
                    continue

                writer.writerow(
                    {
                        "country_iso2": country_iso2,
                        "admin1_code": admin1_code,
                        "code": admin1_code,
                        "name": columns[1],
                        "division_type": country_config[
                            "division_type"
                        ],
                        "status": "ACTIVE",
                    }
                )

                count += 1

        return count

    @staticmethod
    def _prepare_cities(
        source_path: Path,
        output_path: Path,
    ) -> int:
        """Normaliza el catálogo amplio de ciudades sudamericanas.

        Args:
            source_path: Archivo comprimido cities500.zip de GeoNames.
            output_path: CSV normalizado de ciudades.

        Returns:
            Cantidad de ciudades escritas.
        """
        count = 0

        with (
            ZipFile(source_path) as archive,
            archive.open("cities500.txt") as source,
            output_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as target,
        ):
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "source_id",
                    "country_iso2",
                    "admin1_code",
                    "code",
                    "name",
                    "latitude",
                    "longitude",
                    "status",
                ],
            )

            writer.writeheader()

            for raw_line in source:
                line = raw_line.decode(
                    "utf-8",
                )

                columns = line.rstrip(
                    "\n"
                ).split("\t")

                country_iso2 = columns[8]

                if country_iso2 not in SOUTH_AMERICA_COUNTRIES:
                    continue

                if columns[6] != "P":
                    continue

                writer.writerow(
                    {
                        "source_id": columns[0],
                        "country_iso2": country_iso2,
                        "admin1_code": columns[10],
                        "code": "",
                        "name": columns[1],
                        "latitude": columns[4],
                        "longitude": columns[5],
                        "status": "ACTIVE",
                    }
                )

                count += 1

        return count
