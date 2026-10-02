"""Geografía estricta de las direcciones de los perfiles (DS-02, FR-035–FR-037, R-07).

Mismo algoritmo que Operational Context Fase A:

1. Regla local: división o ciudad sin país → `GEOGRAPHY_PARENT_REQUIRED`.
2. Sin niveles informados, o niveles idénticos a la versión vigente → no se
   consulta Geography.
3. Si no hay versión vigente o cambió algún nivel, se revalida el conjunto
   informado en orden país → división → ciudad y se detiene en el primer rechazo.
"""

from __future__ import annotations

from uuid import UUID

from party_identity_service.application.exceptions import (
    AdministrativeDivisionNotFoundError,
    CityNotFoundError,
    CountryNotFoundError,
    GeographyIncoherentError,
    GeographyParentRequiredError,
    LocationInactiveError,
)
from party_identity_service.application.ports import LocationDirectory

Geography = tuple[UUID | None, UUID | None, UUID | None]


def validate_profile_geography(
    locations: LocationDirectory,
    *,
    new: Geography,
    current: Geography | None,
) -> None:
    """Valida país, división y ciudad de una versión nueva de perfil.

    Args:
        locations: Puerto de Geography.
        new: `(country_id, administrative_division_id, city_id)` de la versión nueva.
        current: Los mismos niveles de la versión vigente, o `None` si no hay.

    Raises:
        GeographyParentRequiredError, CountryNotFoundError,
        AdministrativeDivisionNotFoundError, CityNotFoundError,
        LocationInactiveError, GeographyIncoherentError,
        DependencyUnavailableError.
    """
    country_id, division_id, city_id = new

    if country_id is None:
        if division_id is not None:
            raise GeographyParentRequiredError(field="administrative_division_id")
        if city_id is not None:
            raise GeographyParentRequiredError(field="city_id")
        return

    if current is not None and tuple(current) == tuple(new):
        return

    country = locations.get_country(country_id)
    if country is None:
        raise CountryNotFoundError
    if country.status != "ACTIVE":
        raise LocationInactiveError(field="country_id")

    if division_id is not None:
        division = locations.get_administrative_division(division_id)
        if division is None:
            raise AdministrativeDivisionNotFoundError
        if division.status != "ACTIVE":
            raise LocationInactiveError(field="administrative_division_id")
        if division.country_id != country_id:
            raise GeographyIncoherentError(field="administrative_division_id")

    if city_id is not None:
        city = locations.get_city(city_id)
        if city is None:
            raise CityNotFoundError
        if city.status != "ACTIVE":
            raise LocationInactiveError(field="city_id")
        if city.country_id != country_id or city.administrative_division_id != division_id:
            raise GeographyIncoherentError(field="city_id")
