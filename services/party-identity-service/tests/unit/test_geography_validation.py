"""Algoritmo de geografía estricta de perfiles (T030; DS-02, FR-035–FR-037)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from party_identity_service.application.exceptions import (
    AdministrativeDivisionNotFoundError,
    CityNotFoundError,
    CountryNotFoundError,
    GeographyIncoherentError,
    GeographyParentRequiredError,
    LocationInactiveError,
)
from party_identity_service.application.geography_validation import validate_profile_geography
from party_identity_service.application.ports import LocationRecord

COUNTRY, OTHER_COUNTRY = uuid4(), uuid4()
DIVISION, OTHER_DIVISION = uuid4(), uuid4()
CITY = uuid4()


class SpyLocations:
    def __init__(self) -> None:
        self.records: dict[UUID, LocationRecord] = {
            COUNTRY: LocationRecord(id=COUNTRY, status="ACTIVE"),
            OTHER_COUNTRY: LocationRecord(id=OTHER_COUNTRY, status="ACTIVE"),
            DIVISION: LocationRecord(id=DIVISION, status="ACTIVE", country_id=COUNTRY),
            OTHER_DIVISION: LocationRecord(id=OTHER_DIVISION, status="ACTIVE", country_id=COUNTRY),
            CITY: LocationRecord(id=CITY, status="ACTIVE", country_id=COUNTRY, administrative_division_id=DIVISION),
        }
        self.calls: list[str] = []

    def _get(self, kind: str, record_id: UUID) -> LocationRecord | None:
        self.calls.append(kind)
        return self.records.get(record_id)

    def get_country(self, country_id):
        return self._get("country", country_id)

    def get_administrative_division(self, division_id):
        return self._get("division", division_id)

    def get_city(self, city_id):
        return self._get("city", city_id)


@pytest.fixture
def spy() -> SpyLocations:
    return SpyLocations()


@pytest.mark.parametrize(
    "geography, field",
    [((None, DIVISION, None), "administrative_division_id"), ((None, None, CITY), "city_id")],
)
def test_lower_level_without_country_is_rejected_without_calls(spy, geography, field) -> None:
    with pytest.raises(GeographyParentRequiredError) as error:
        validate_profile_geography(spy, new=geography, current=None)

    assert error.value.field == field
    assert spy.calls == []


def test_no_geography_makes_no_calls(spy) -> None:
    validate_profile_geography(spy, new=(None, None, None), current=None)

    assert spy.calls == []


def test_identical_geography_to_current_version_makes_no_calls(spy) -> None:
    validate_profile_geography(spy, new=(COUNTRY, DIVISION, CITY), current=(COUNTRY, DIVISION, CITY))

    assert spy.calls == []


def test_any_change_revalidates_the_whole_informed_set_in_order(spy) -> None:
    validate_profile_geography(spy, new=(COUNTRY, DIVISION, CITY), current=(COUNTRY, DIVISION, None))

    assert spy.calls == ["country", "division", "city"]


def test_removing_a_level_revalidates_remaining_set(spy) -> None:
    validate_profile_geography(spy, new=(COUNTRY, None, None), current=(COUNTRY, DIVISION, None))

    assert spy.calls == ["country"]


def test_first_validation_without_current_version(spy) -> None:
    validate_profile_geography(spy, new=(COUNTRY, None, None), current=None)

    assert spy.calls == ["country"]


@pytest.mark.parametrize(
    "geography, error_class",
    [
        ((uuid4(), None, None), CountryNotFoundError),
        ((COUNTRY, uuid4(), None), AdministrativeDivisionNotFoundError),
        ((COUNTRY, DIVISION, uuid4()), CityNotFoundError),
    ],
)
def test_not_found_by_level(spy, geography, error_class) -> None:
    with pytest.raises(error_class):
        validate_profile_geography(spy, new=geography, current=None)


def test_stops_at_first_rejection(spy) -> None:
    with pytest.raises(CountryNotFoundError):
        validate_profile_geography(spy, new=(uuid4(), DIVISION, CITY), current=None)

    assert spy.calls == ["country"]


@pytest.mark.parametrize("level", ["country", "division", "city"])
def test_inactive_level_is_rejected_with_field(spy, level) -> None:
    target = {"country": COUNTRY, "division": DIVISION, "city": CITY}[level]
    record = spy.records[target]
    spy.records[target] = LocationRecord(
        id=record.id, status="INACTIVE", country_id=record.country_id,
        administrative_division_id=record.administrative_division_id,
    )

    with pytest.raises(LocationInactiveError) as error:
        validate_profile_geography(spy, new=(COUNTRY, DIVISION, CITY), current=None)

    assert error.value.field == {"country": "country_id", "division": "administrative_division_id",
                                 "city": "city_id"}[level]


def test_division_from_another_country_is_incoherent(spy) -> None:
    with pytest.raises(GeographyIncoherentError) as error:
        validate_profile_geography(spy, new=(OTHER_COUNTRY, DIVISION, None), current=None)

    assert error.value.field == "administrative_division_id"


def test_city_from_another_division_is_incoherent(spy) -> None:
    with pytest.raises(GeographyIncoherentError) as error:
        validate_profile_geography(spy, new=(COUNTRY, OTHER_DIVISION, CITY), current=None)

    assert error.value.field == "city_id"


def test_city_from_another_country_is_incoherent(spy) -> None:
    with pytest.raises(GeographyIncoherentError) as error:
        validate_profile_geography(spy, new=(OTHER_COUNTRY, None, CITY), current=None)

    assert error.value.field == "city_id"


def test_city_without_division_must_have_no_division_in_geography(spy) -> None:
    """Ciudad con división en Geography y sin división enviada: incoherente (ambas nulas o iguales)."""
    with pytest.raises(GeographyIncoherentError):
        validate_profile_geography(spy, new=(COUNTRY, None, CITY), current=None)
