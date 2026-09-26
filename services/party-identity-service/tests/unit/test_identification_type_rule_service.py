"""Pruebas del servicio de reglas con dobles (FR-011, FR-013, R-09, DS-07)."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    DependencyUnavailableError,
    ExampleDoesNotMatchPatternError,
    ImmutableFieldError,
    InvalidAgeRangeError,
    InvalidNumberPatternError,
    InvalidStatusTransitionError,
    InvalidValidityRangeError,
    RuleChangeRequiresNewVersionError,
    VersionConflictError,
)
from party_identity_service.application.identification_type_rule_service import (
    IdentificationTypeRuleService,
)
from party_identity_service.domain.identification_type_rule import IdentificationTypeRule
from tests.conftest import COLOMBIA_ID, FakeCountryDirectory


class InMemoryRules:
    def __init__(self) -> None:
        self.items: dict = {}
        self.writes = 0

    def get_by_id(self, rule_id):
        return self.items.get(rule_id)

    def create(self, *, actor_id, valid_from, **values):
        now = datetime.now(timezone.utc)
        rule = IdentificationTypeRule(
            id=uuid4(),
            is_active=True,
            valid_from=valid_from or now,
            version=1,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.items[rule.id] = rule
        self.writes += 1
        return rule

    def update(self, rule_id, *, expected_version, values, actor_id):
        rule = replace(self.items[rule_id], **values, version=expected_version + 1, updated_by=actor_id)
        self.items[rule_id] = rule
        self.writes += 1
        return rule

    def create_version(self, rule_id, *, expected_version, actor_id, **values):
        current = self.items[rule_id]
        self.items[rule_id] = replace(current, is_active=False, version=current.version + 1)
        successor = replace(current, id=uuid4(), version=1, **values)
        self.items[successor.id] = successor
        self.writes += 1
        return successor

    def deactivate(self, rule_id, *, expected_version, actor_id):
        rule = replace(self.items[rule_id], is_active=False, version=expected_version + 1)
        self.items[rule_id] = rule
        self.writes += 1
        return rule


@pytest.fixture
def countries() -> FakeCountryDirectory:
    return FakeCountryDirectory()


@pytest.fixture
def repository() -> InMemoryRules:
    return InMemoryRules()


@pytest.fixture
def service(repository, countries) -> IdentificationTypeRuleService:
    return IdentificationTypeRuleService(repository, countries)


def _create(service, **overrides):
    values = {
        "party_kind": "PERSON",
        "country_id": COLOMBIA_ID,
        "identification_type": "citizen_id_modern",
        "sigla": "cc",
        "number_pattern": " ^[0-9]{10}$ ",
        "number_pattern_description": "Cédula moderna de 10 dígitos.",
        "example_value": "1000000000",
        "min_age_years": 18,
        "max_age_years": None,
        "valid_from": None,
        "valid_to": None,
        "actor_id": "admin",
    }
    values.update(overrides)
    return service.create(**values)


def _update(service, rule, **overrides):
    values = {
        "expected_version": rule.version,
        "number_pattern_description": rule.number_pattern_description,
        "example_value": rule.example_value,
        "actor_id": "editor",
    }
    values.update(overrides)
    return service.update(rule.id, **values)


def test_create_normalizes_codes_and_pattern(service) -> None:
    rule = _create(service)

    assert rule.identification_type == "CITIZEN_ID_MODERN"
    assert rule.sigla == "CC"
    assert rule.number_pattern == "^[0-9]{10}$"


@pytest.mark.parametrize("pattern", ["   ", "[0-9", "(?P<x"])
def test_invalid_pattern_is_rejected(service, pattern) -> None:
    with pytest.raises(InvalidNumberPatternError):
        _create(service, number_pattern=pattern)


def test_example_must_match_pattern(service) -> None:
    with pytest.raises(ExampleDoesNotMatchPatternError):
        _create(service, example_value="12AB")


@pytest.mark.parametrize(("minimum", "maximum"), [(-1, None), (None, -2), (18, 10)])
def test_invalid_age_range(service, minimum, maximum) -> None:
    with pytest.raises(InvalidAgeRangeError):
        _create(service, min_age_years=minimum, max_age_years=maximum)


def test_invalid_validity_range(service) -> None:
    start = datetime.now(timezone.utc)

    with pytest.raises(InvalidValidityRangeError):
        _create(service, valid_from=start, valid_to=start - timedelta(days=1))


def test_unknown_country_or_geography_down_does_not_write(service, repository, countries) -> None:
    with pytest.raises(CountryNotFoundError):
        _create(service, country_id=uuid4())

    countries.mode = "unavailable"
    with pytest.raises(DependencyUnavailableError):
        _create(service)

    assert repository.writes == 0


@pytest.mark.parametrize(
    "field_value",
    [("party_kind", "ORGANIZATION"), ("country_id", uuid4()), ("identification_type", "OTRO"), ("sigla", "XX")],
)
def test_put_rejects_identity_fields(service, field_value) -> None:
    rule = _create(service)
    field, value = field_value

    with pytest.raises(ImmutableFieldError):
        _update(service, rule, requested_identity={field: value})


def test_put_accepts_identity_fields_equal_to_current(service) -> None:
    rule = _create(service)

    result = _update(
        service,
        rule,
        number_pattern_description="Nueva descripción.",
        requested_identity={"sigla": "cc", "country_id": COLOMBIA_ID},
        requested_semantics={"number_pattern": "^[0-9]{10}$", "min_age_years": 18},
    )

    assert result.number_pattern_description == "Nueva descripción."


@pytest.mark.parametrize(
    "semantics",
    [{"number_pattern": "^[0-9]{11}$"}, {"min_age_years": 21}, {"max_age_years": 99}],
)
def test_put_rejects_semantic_changes(service, semantics) -> None:
    rule = _create(service)

    with pytest.raises(RuleChangeRequiresNewVersionError):
        _update(service, rule, requested_semantics=semantics)


def test_identical_put_does_not_write(service, repository) -> None:
    rule = _create(service)
    writes = repository.writes

    result = _update(service, rule)

    assert result.version == rule.version
    assert repository.writes == writes


def test_put_with_stale_version_is_conflict(service) -> None:
    rule = _create(service)

    with pytest.raises(VersionConflictError):
        _update(service, rule, expected_version=5)


def test_put_example_must_match_current_pattern(service) -> None:
    rule = _create(service)

    with pytest.raises(ExampleDoesNotMatchPatternError):
        _update(service, rule, example_value="ABC")


def test_historic_rule_rejects_put_version_and_deactivate(service) -> None:
    rule = _create(service)
    retired = service.deactivate(rule.id, expected_version=1, actor_id="admin")

    with pytest.raises(InvalidStatusTransitionError):
        _update(service, retired, number_pattern_description="x")
    with pytest.raises(InvalidStatusTransitionError):
        service.create_version(
            retired.id,
            expected_version=retired.version,
            number_pattern="^[0-9]{11}$",
            number_pattern_description="x",
            example_value=None,
            min_age_years=None,
            max_age_years=None,
            actor_id="admin",
        )
    with pytest.raises(InvalidStatusTransitionError):
        service.deactivate(retired.id, expected_version=retired.version, actor_id="admin")


def test_create_version_validates_and_does_not_call_geography(service, countries) -> None:
    rule = _create(service)
    countries.calls.clear()

    with pytest.raises(InvalidNumberPatternError):
        service.create_version(
            rule.id,
            expected_version=1,
            number_pattern="[",
            number_pattern_description="x",
            example_value=None,
            min_age_years=None,
            max_age_years=None,
            actor_id="admin",
        )

    successor = service.create_version(
        rule.id,
        expected_version=1,
        number_pattern="^[0-9]{11}$",
        number_pattern_description="Nueva longitud.",
        example_value="10000000000",
        min_age_years=18,
        max_age_years=None,
        actor_id="admin",
    )

    assert successor.id != rule.id
    assert successor.number_pattern == "^[0-9]{11}$"
    assert countries.calls == []
