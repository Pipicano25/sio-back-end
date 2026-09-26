"""Validación de la ubicación contra Geography (R-07, FR-030 a FR-035).

1. Regla local, sin llamadas: división o ciudad sin país → rechazo.
2. Si ningún nivel cambió respecto del valor persistido, no se consulta
   Geography (DS-06). En el alta, "cambió" = hay algún nivel informado.
3. Si cambió alguno, se consultan en orden país → división → ciudad los niveles
   informados y se detiene en el primer rechazo. Se revalidan los tres niveles
   porque la coherencia depende de todos (DS-05).

Los registros de Geography se usan solo en memoria (FR-044).
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from operational_context_service.application.exceptions import (
    AdministrativeDivisionNotFoundError,
    CityNotFoundError,
    CountryNotFoundError,
    GeographyIncoherentError,
    LocationInactiveError,
    OperationalContextError,
)
from operational_context_service.application.ports import GeographyDirectory
from operational_context_service.domain.location import check_hierarchy
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)


@dataclass(frozen=True, slots=True)
class Location:
    """Los tres niveles geográficos de una empresa o sucursal."""

    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None

    def is_empty(self) -> bool:
        return (
            self.country_id is None
            and self.administrative_division_id is None
            and self.city_id is None
        )


def log_rejected_reference(error: OperationalContextError, reference_id: UUID) -> None:
    """Registra un rechazo `422` de referencia externa en `INFO` (R-03).

    Solo `code`, campo y UUID rechazado (no sensible); el `trace_id` lo añade el
    filtro de logging. Nunca el token ni el cuerpo.
    """
    logger.info(
        "Referencia externa rechazada code=%s campo=%s referencia=%s",
        error.code,
        error.field,
        reference_id,
    )


def _reject(error: OperationalContextError, reference_id: UUID) -> OperationalContextError:
    log_rejected_reference(error, reference_id)
    return error


def validate_location(
    new: Location,
    current: Location | None,
    geography: GeographyDirectory,
) -> None:
    """Aplica el algoritmo de R-07.

    Args:
        new: Ubicación solicitada.
        current: Ubicación persistida (`None` en el alta).
        geography: Puerto de Geography.

    Raises:
        GeographyParentRequiredError, CountryNotFoundError,
        AdministrativeDivisionNotFoundError, CityNotFoundError,
        LocationInactiveError, GeographyIncoherentError,
        DependencyUnavailableError.
    """
    check_hierarchy(new.country_id, new.administrative_division_id, new.city_id)

    if new.is_empty() or new == current:
        return

    country_id = new.country_id
    assert country_id is not None  # garantizado por check_hierarchy

    country = geography.get_country(country_id)

    if country is None:
        raise _reject(CountryNotFoundError(field="country_id"), country_id)

    if country.status != "ACTIVE":
        raise _reject(
            LocationInactiveError("El país indicado está inactivo en Geography Service.", field="country_id"),
            country_id,
        )

    if new.administrative_division_id is not None:
        division_id = new.administrative_division_id
        division = geography.get_administrative_division(division_id)

        if division is None:
            raise _reject(
                AdministrativeDivisionNotFoundError(field="administrative_division_id"),
                division_id,
            )

        if division.status != "ACTIVE":
            raise _reject(
                LocationInactiveError(
                    "La división administrativa indicada está inactiva en Geography Service.",
                    field="administrative_division_id",
                ),
                division_id,
            )

        if division.country_id != country_id:
            raise _reject(
                GeographyIncoherentError(
                    "La división administrativa no pertenece al país indicado.",
                    field="administrative_division_id",
                ),
                division_id,
            )

    if new.city_id is not None:
        city_id = new.city_id
        city = geography.get_city(city_id)

        if city is None:
            raise _reject(CityNotFoundError(field="city_id"), city_id)

        if city.status != "ACTIVE":
            raise _reject(
                LocationInactiveError(
                    "La ciudad indicada está inactiva en Geography Service.",
                    field="city_id",
                ),
                city_id,
            )

        if city.country_id != country_id:
            raise _reject(
                GeographyIncoherentError(
                    "La ciudad no pertenece al país indicado.",
                    field="city_id",
                ),
                city_id,
            )

        if city.administrative_division_id != new.administrative_division_id:
            if city.administrative_division_id is None:
                message = "La ciudad no tiene división administrativa; no debe enviarse una."
            elif new.administrative_division_id is None:
                message = "La ciudad pertenece a una división administrativa que debe informarse."
            else:
                message = "La ciudad no pertenece a la división administrativa enviada."
            raise _reject(GeographyIncoherentError(message, field="city_id"), city_id)
