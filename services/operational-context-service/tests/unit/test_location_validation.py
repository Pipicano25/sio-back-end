"""Algoritmo de validación de ubicación R-07 (RC-03, RC-04, FR-031 a FR-033, DS-04, DS-05, DS-06).

Pruebas obligatorias 4, 5, 6 y 7.
"""

from uuid import uuid4

import pytest

from operational_context_service.application.exceptions import (
    AdministrativeDivisionNotFoundError,
    CityNotFoundError,
    CountryNotFoundError,
    DependencyUnavailableError,
    GeographyIncoherentError,
    GeographyParentRequiredError,
    LocationInactiveError,
)
from operational_context_service.application.location_validation import Location, validate_location
from tests.fakes import FakeGeographyDirectory, GeographyFixture


@pytest.fixture
def geography():
    return FakeGeographyDirectory()


@pytest.fixture
def geo(geography):
    return GeographyFixture(geography)


def test_empty_location_makes_no_calls(geography):
    validate_location(Location(None, None, None), None, geography)

    assert geography.count() == 0


def test_unchanged_location_makes_no_calls(geography, geo):
    """Prueba obligatoria 7 (nivel algoritmo)."""
    location = Location(geo.colombia, geo.antioquia, geo.medellin)

    validate_location(location, location, geography)

    assert geography.count() == 0


def test_coherent_location_is_accepted_in_order(geography, geo):
    validate_location(Location(geo.colombia, geo.antioquia, geo.medellin), None, geography)

    assert [name for name, _ in geography.calls] == ["get_country", "get_administrative_division", "get_city"]


def test_city_without_division_is_accepted(geography, geo):
    validate_location(Location(geo.colombia, None, geo.city_without_division), None, geography)


def test_country_only_is_accepted(geography, geo):
    validate_location(Location(geo.colombia, None, None), None, geography)

    assert geography.count() == 1


@pytest.mark.parametrize("division, city", [("division", None), (None, "city")])
def test_parent_required_without_calls(geography, division, city):
    with pytest.raises(GeographyParentRequiredError):
        validate_location(
            Location(None, uuid4() if division else None, uuid4() if city else None),
            None,
            geography,
        )

    assert geography.count() == 0


def test_unknown_country(geography):
    """Prueba obligatoria 4 (país)."""
    with pytest.raises(CountryNotFoundError) as error:
        validate_location(Location(uuid4(), None, None), None, geography)

    assert error.value.field == "country_id"


def test_unknown_division_stops_before_city(geography, geo):
    """Prueba obligatoria 4 (división)."""
    with pytest.raises(AdministrativeDivisionNotFoundError) as error:
        validate_location(Location(geo.colombia, uuid4(), geo.medellin), None, geography)

    assert error.value.field == "administrative_division_id"
    assert geography.count("get_city") == 0


def test_unknown_city(geography, geo):
    """Prueba obligatoria 4 (ciudad)."""
    with pytest.raises(CityNotFoundError) as error:
        validate_location(Location(geo.colombia, geo.antioquia, uuid4()), None, geography)

    assert error.value.field == "city_id"


@pytest.mark.parametrize(
    "build, field",
    [
        (lambda g: Location(g.inactive_country, None, None), "country_id"),
        (lambda g: Location(g.colombia, g.inactive_division, None), "administrative_division_id"),
        (lambda g: Location(g.colombia, g.antioquia, g.inactive_city), "city_id"),
    ],
)
def test_inactive_levels_are_rejected(geography, geo, build, field):
    with pytest.raises(LocationInactiveError) as error:
        validate_location(build(geo), None, geography)

    assert error.value.field == field


@pytest.mark.parametrize(
    "build, field",
    [
        (lambda g: Location(g.peru, g.antioquia, None), "administrative_division_id"),
        (lambda g: Location(g.peru, None, g.medellin), "city_id"),
        (lambda g: Location(g.colombia, g.cundinamarca, g.medellin), "city_id"),
        (lambda g: Location(g.colombia, None, g.medellin), "city_id"),
        (lambda g: Location(g.colombia, g.antioquia, g.city_without_division), "city_id"),
    ],
    ids=["division-otro-pais", "ciudad-otro-pais", "ciudad-otra-division",
         "ciudad-con-division-no-enviada", "ciudad-sin-division-con-division-enviada"],
)
def test_incoherent_hierarchy(geography, geo, build, field):
    """Prueba obligatoria 6."""
    with pytest.raises(GeographyIncoherentError) as error:
        validate_location(build(geo), None, geography)

    assert error.value.field == field


def test_geography_unavailable(geography, geo):
    """Prueba obligatoria 5."""
    geography.mode = "unavailable"

    with pytest.raises(DependencyUnavailableError):
        validate_location(Location(geo.colombia, None, None), None, geography)


def test_changing_any_level_revalidates_all_levels(geography, geo):
    current = Location(geo.colombia, geo.antioquia, geo.medellin)

    # Cambiar solo el país invalida la división y la ciudad.
    with pytest.raises(GeographyIncoherentError):
        validate_location(Location(geo.peru, geo.antioquia, geo.medellin), current, geography)

    geography.reset()
    validate_location(Location(geo.colombia, geo.antioquia, geo.medellin), Location(geo.colombia, geo.antioquia, None), geography)

    assert [name for name, _ in geography.calls] == ["get_country", "get_administrative_division", "get_city"]
