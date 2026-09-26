"""Reglas de dominio puras (RC-04, RC-05, FR-012, FR-021, FR-031, FR-034, R-08)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from operational_context_service.domain.branch_code import normalize_code
from operational_context_service.domain.currency import normalize_currency
from operational_context_service.domain.errors import (
    DomainValidationError,
    GeographyParentRequiredError,
)
from operational_context_service.domain.location import (
    check_hierarchy,
    normalize_coordinate,
    validate_coordinates,
)
from operational_context_service.domain.timezone import is_valid_timezone, normalize_timezone


class TestHierarchy:
    def test_empty_location_is_valid(self):
        check_hierarchy(None, None, None)

    def test_country_only_is_valid(self):
        check_hierarchy(uuid4(), None, None)

    def test_full_location_is_valid_locally(self):
        check_hierarchy(uuid4(), uuid4(), uuid4())

    @pytest.mark.parametrize("division, city", [(uuid4(), None), (None, uuid4()), (uuid4(), uuid4())])
    def test_division_or_city_without_country(self, division, city):
        with pytest.raises(GeographyParentRequiredError) as error:
            check_hierarchy(None, division, city)
        assert error.value.code == "GEOGRAPHY_PARENT_REQUIRED"
        assert error.value.field == "country_id"


class TestCoordinates:
    def test_pair_within_range(self):
        validate_coordinates(Decimal("6.244203"), Decimal("-75.581211"))

    def test_both_missing_is_valid(self):
        validate_coordinates(None, None)

    @pytest.mark.parametrize("latitude, longitude, field", [
        (Decimal("6.2"), None, "longitude"),
        (None, Decimal("-75.5"), "latitude"),
        (Decimal("90.000001"), Decimal("0"), "latitude"),
        (Decimal("-90.1"), Decimal("0"), "latitude"),
        (Decimal("0"), Decimal("180.5"), "longitude"),
        (Decimal("0"), Decimal("-181"), "longitude"),
    ])
    def test_invalid(self, latitude, longitude, field):
        with pytest.raises(DomainValidationError) as error:
            validate_coordinates(latitude, longitude)
        assert error.value.field == field

    def test_limits_are_valid(self):
        validate_coordinates(Decimal("90"), Decimal("-180"))
        validate_coordinates(Decimal("-90"), Decimal("180"))

    def test_six_decimals_accepted_without_rounding(self):
        assert normalize_coordinate(6.244203, field="latitude") == Decimal("6.244203")
        assert normalize_coordinate("6.244203", field="latitude") == Decimal("6.244203")

    def test_more_than_six_decimals_rejected_not_rounded(self):
        with pytest.raises(DomainValidationError):
            normalize_coordinate("6.2442031", field="latitude")

    def test_non_numeric_rejected(self):
        with pytest.raises(DomainValidationError):
            normalize_coordinate("abc", field="latitude")


class TestTimezone:
    @pytest.mark.parametrize("value", ["America/Bogota", "Europe/Madrid", "America/Argentina/Buenos_Aires", "UTC"])
    def test_valid(self, value):
        assert is_valid_timezone(value)
        assert normalize_timezone(f"  {value} ") == value

    @pytest.mark.parametrize("value", ["Bogota", "GMT-5", "", "   ", "America/Nowhere", "../etc/passwd",
                                       "/America/Bogota", "America\\Bogota", "A" * 61])
    def test_invalid(self, value):
        assert not is_valid_timezone(value.strip())
        with pytest.raises(DomainValidationError) as error:
            normalize_timezone(value)
        assert error.value.field == "timezone"


class TestCurrency:
    def test_normalizes_to_upper(self):
        assert normalize_currency(" cop ") == "COP"

    @pytest.mark.parametrize("value", ["CO", "COPS", "C0P", "", "12$"])
    def test_invalid(self, value):
        with pytest.raises(DomainValidationError) as error:
            normalize_currency(value)
        assert error.value.field == "default_currency"


class TestBranchCode:
    def test_normalizes(self):
        assert normalize_code(" bog-01 ") == "BOG-01"

    def test_forty_characters_accepted(self):
        assert normalize_code("a" * 40) == "A" * 40

    @pytest.mark.parametrize("value", ["", "   ", "a" * 41])
    def test_invalid(self, value):
        with pytest.raises(DomainValidationError) as error:
            normalize_code(value)
        assert error.value.field == "code"
