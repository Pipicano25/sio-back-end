"""Geography leído de sus vistas de contrato (spec 025, T068; D27).

`ContractGeographyDirectory` implementa `GeographyDirectory` igual que `HTTPGeographyDirectory`, que hoy va con el
token del usuario. En Geography cada `GET` por id solo exige el permiso de lectura de su ruta y devuelve el registro
en cualquier estado:

| Método | Vista | Reemplaza | Permiso de la ruta |
|---|---|---|---|
| `get_country` | `v1_countries` | `GET /global-countries/{id}` | `perm:geography:global_countries:read` |
| `get_administrative_division` | `v1_administrative_divisions` | `GET /global-administrative-divisions/{id}` | `...:global_administrative_divisions:read` |
| `get_city` | `v1_cities` | `GET /global-cities/{id}` | `...:global_cities:read` |

Sin el permiso o sin token → `DependencyUnavailableError(cause=GEOGRAPHY_VALIDATION_DENIED)`, como el `401`/`403`.
Sin fila → `None` (el `404`). `status` fuera de `ACTIVE`/`INACTIVE` o un id vacío → la misma indisponibilidad que un
cuerpo inesperado. Cualquier error de base → `DependencyUnavailableError("geography")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sqlalchemy import Engine

from operational_context_service.application.exceptions import GEOGRAPHY_VALIDATION_DENIED
from operational_context_service.application.ports import CityRef, DivisionRef, ExternalRef
from operational_context_service.infrastructure.contract_support import ContractReader

PROVIDER = "geography"
SERVICE = "geography"
COUNTRIES_READ = SioPermission(SERVICE, "global_countries", "read")
DIVISIONS_READ = SioPermission(SERVICE, "global_administrative_divisions", "read")
CITIES_READ = SioPermission(SERVICE, "global_cities", "read")

_COUNTRY = "SELECT id, status FROM contract.v1_countries WHERE id = :id"
_DIVISION = "SELECT id, country_id, status FROM contract.v1_administrative_divisions WHERE id = :id"
_CITY = "SELECT id, country_id, administrative_division_id, status FROM contract.v1_cities WHERE id = :id"


class ContractGeographyDirectory:
    """Países, divisiones y ciudades por UUID desde las vistas de Geography, con el permiso del usuario."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = ContractReader(
            engine, provider=PROVIDER, claims=claims, denied_cause=GEOGRAPHY_VALIDATION_DENIED
        )

    def get_country(self, country_id: UUID) -> ExternalRef | None:
        operation = "get_country"
        self._reader.require(operation, COUNTRIES_READ)
        row = self._reader.one(operation, _COUNTRY, {"id": country_id})
        if row is None:
            return None
        return ExternalRef(id=country_id, status=self._reader.status(operation, row))

    def get_administrative_division(self, division_id: UUID) -> DivisionRef | None:
        operation = "get_administrative_division"
        self._reader.require(operation, DIVISIONS_READ)
        row = self._reader.one(operation, _DIVISION, {"id": division_id})
        if row is None:
            return None
        return DivisionRef(
            id=division_id,
            status=self._reader.status(operation, row),
            country_id=self._reader.uuid(operation, row, "country_id"),
        )

    def get_city(self, city_id: UUID) -> CityRef | None:
        operation = "get_city"
        self._reader.require(operation, CITIES_READ)
        row = self._reader.one(operation, _CITY, {"id": city_id})
        if row is None:
            return None
        division = row.get("administrative_division_id")
        return CityRef(
            id=city_id,
            status=self._reader.status(operation, row),
            country_id=self._reader.uuid(operation, row, "country_id"),
            administrative_division_id=(
                None if division is None else self._reader.uuid(operation, row, "administrative_division_id")
            ),
        )
