"""Geography leído de sus vistas de contrato (spec 025, T069; D27).

Hoy Party Identity consulta Geography con el token del usuario. Con `GEOGRAPHY_READ_SOURCE=contract`:

| Método | Vista | Reemplaza | Permiso de la ruta |
|---|---|---|---|
| `ContractGeographyLocationDirectory.get_country` | `v1_countries` | `GET /global-countries/{id}` | `perm:geography:global_countries:read` |
| `ContractGeographyLocationDirectory.get_administrative_division` | `v1_administrative_divisions` | `GET /global-administrative-divisions/{id}` | `...:global_administrative_divisions:read` |
| `ContractGeographyLocationDirectory.get_city` | `v1_cities` | `GET /global-cities/{id}` | `...:global_cities:read` |
| `ContractGeographyCountryValidator.exists` | `v1_countries` | `GET /global-countries/{id}` (`200` → existe, `404` → no) | `...:global_countries:read` |

- Sin token (el `401`) o sin el permiso (el `403`) → `DependencyUnavailableError(dependency="geography",
  cause=COUNTRY_VALIDATION_DENIED)`, igual que hoy.
- Sin fila → `None` / `False` (el `404`). `status` fuera de `ACTIVE`/`INACTIVE` o un id vacío → la misma
  indisponibilidad que un cuerpo inesperado.
- Cualquier error de base → `DependencyUnavailableError(dependency="geography")`, el mismo `503` de hoy, con causa
  `contract:<causa>`.
- `find_id_by_iso3` sigue por API (FR-036): se delega en el adaptador HTTP de siempre.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sqlalchemy import Engine

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    DependencyUnavailableError,
)
from party_identity_service.application.ports import LocationRecord
from party_identity_service.infrastructure.geography_country_validator import HTTPGeographyCountryValidator
from party_identity_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

DEPENDENCY = "geography"
VALID_STATUSES = {"ACTIVE", "INACTIVE"}
COUNTRIES_READ = SioPermission("geography", "global_countries", "read")
DIVISIONS_READ = SioPermission("geography", "global_administrative_divisions", "read")
CITIES_READ = SioPermission("geography", "global_cities", "read")

_COUNTRY = "SELECT id, status FROM contract.v1_countries WHERE id = :id"
_DIVISION = "SELECT id, country_id, status FROM contract.v1_administrative_divisions WHERE id = :id"
_CITY = "SELECT id, country_id, administrative_division_id, status FROM contract.v1_cities WHERE id = :id"


class _Reader:
    """Lectura de una vista de Geography con el permiso del usuario de la solicitud."""

    def __init__(self, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def one(self, operation: str, required: SioPermission, sql: str, row_id: UUID) -> dict[str, Any] | None:
        self._require(operation, required)
        with contract_errors(lambda cause: self.unavailable(operation, cause), dependency=DEPENDENCY):
            found = read(self._engine, sql, {"id": row_id})
        return found[0] if found else None

    def status(self, operation: str, row: Mapping[str, Any]) -> str:
        value = row.get("status")
        if value not in VALID_STATUSES:
            raise self.unavailable(operation, "cuerpo_inesperado:status")
        return value

    def uuid(self, operation: str, row: Mapping[str, Any], name: str) -> UUID:
        value = row.get(name)
        if not isinstance(value, UUID):
            raise self.unavailable(operation, f"cuerpo_inesperado:{name}")
        return value

    @staticmethod
    def unavailable(operation: str, cause: str) -> DependencyUnavailableError:
        logger.error("Geography no disponible causa=contract:%s operacion=%s", cause, operation)
        return DependencyUnavailableError(dependency=DEPENDENCY, cause=f"contract:{cause}")

    def _require(self, operation: str, required: SioPermission) -> None:
        if self._claims is not None and has_permission(self._claims.permissions, required):
            return
        logger.warning(
            "Geography rechazó la consulta causa=%s operacion=%s estado=%s",
            COUNTRY_VALIDATION_DENIED,
            operation,
            401 if self._claims is None else 403,
        )
        raise DependencyUnavailableError(dependency=DEPENDENCY, cause=COUNTRY_VALIDATION_DENIED)


class ContractGeographyLocationDirectory:
    """Mismo puerto `LocationDirectory` que `HTTPGeographyLocationDirectory`."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = _Reader(engine, claims)

    def get_country(self, country_id: UUID) -> LocationRecord | None:
        operation = "get_country"
        row = self._reader.one(operation, COUNTRIES_READ, _COUNTRY, country_id)
        if row is None:
            return None
        return LocationRecord(id=country_id, status=self._reader.status(operation, row))

    def get_administrative_division(self, division_id: UUID) -> LocationRecord | None:
        operation = "get_administrative_division"
        row = self._reader.one(operation, DIVISIONS_READ, _DIVISION, division_id)
        if row is None:
            return None
        return LocationRecord(
            id=division_id,
            status=self._reader.status(operation, row),
            country_id=self._reader.uuid(operation, row, "country_id"),
        )

    def get_city(self, city_id: UUID) -> LocationRecord | None:
        operation = "get_city"
        row = self._reader.one(operation, CITIES_READ, _CITY, city_id)
        if row is None:
            return None
        division = row.get("administrative_division_id")
        return LocationRecord(
            id=city_id,
            status=self._reader.status(operation, row),
            country_id=self._reader.uuid(operation, row, "country_id"),
            administrative_division_id=(
                None if division is None else self._reader.uuid(operation, row, "administrative_division_id")
            ),
        )


class ContractGeographyCountryValidator:
    """Mismo puerto `CountryDirectory` que `HTTPGeographyCountryValidator`: `exists` por vista, ISO3 por API."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None, http: HTTPGeographyCountryValidator) -> None:
        self._reader = _Reader(engine, claims)
        self._http = http

    def exists(self, country_id: UUID) -> bool:
        """`True` si hay fila en `v1_countries`, en cualquier estado (el `200` de hoy); `False` sin fila (el `404`)."""
        return self._reader.one("exists", COUNTRIES_READ, _COUNTRY, country_id) is not None

    def find_id_by_iso3(self, iso3_code: str) -> UUID:
        """Sigue por API (FR-036)."""
        return self._http.find_id_by_iso3(iso3_code)
