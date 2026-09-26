"""Pruebas del servicio de personas con dobles (RC-04, RC-05, FR-021–FR-023, RN-10)."""

import logging
from datetime import date, timedelta
from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    AgeOutOfRangeError,
    BirthDateInFutureError,
    BirthDateRequiredError,
    CountryNotFoundError,
    DependencyUnavailableError,
    DuplicateIdentificationError,
    InvalidIdentificationNumberError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
    operational_today,
)
from party_identity_service.application.person_identity_service import (
    PersonIdentityService,
)
from tests.conftest import COLOMBIA_ID, FakeCountryDirectory
from tests.doubles import InMemoryPersonRepository, InMemoryRuleRepository

ACTOR = "user-admin"


def _rule(identification_type, sigla, pattern, *, min_age=None, max_age=None, party_kind="PERSON"):
    return IdentificationRule(
        party_kind=party_kind,
        country_id=COLOMBIA_ID,
        identification_type=identification_type,
        sigla=sigla,
        pattern=pattern,
        description=f"Regla {identification_type}.",
        min_age_years=min_age,
        max_age_years=max_age,
    )


COLOMBIAN_RULES = [
    _rule("CITIZEN_ID_MODERN", "CC", r"^[0-9]{10}$", min_age=18),
    _rule("CITIZEN_ID_OLD", "CC", r"^[0-9]{3,8}$", min_age=18),
    _rule("IDENTITY_CARD_MODERN", "TI", r"^[0-9]{10}$", min_age=7, max_age=17),
    _rule("CIVIL_REGISTRY", "RC", r"^[0-9]{10}$", min_age=0, max_age=6),
]


def _years_ago(years: int) -> date:
    today = operational_today()
    return today.replace(year=today.year - years) - timedelta(days=1)


@pytest.fixture
def countries() -> FakeCountryDirectory:
    return FakeCountryDirectory()


@pytest.fixture
def repository() -> InMemoryPersonRepository:
    return InMemoryPersonRepository()


@pytest.fixture
def service(repository, countries) -> PersonIdentityService:
    return PersonIdentityService(repository, InMemoryRuleRepository(COLOMBIAN_RULES), countries)


def _create(service, **overrides):
    values = {
        "identification_country_id": COLOMBIA_ID,
        "identification_type": "CC",
        "identification_number": "1000000000",
        "first_name": "ANA",
        "middle_name": None,
        "last_name": "PRUEBA",
        "second_last_name": None,
        "birth_date": _years_ago(30),
        "verification_status": "UNVERIFIED",
        "actor_id": ACTOR,
    }
    values.update(overrides)
    return service.create(**values)


def test_normalizes_type_and_number(service) -> None:
    person = _create(service, identification_type=" cc ", identification_number=" 1000000000 ")

    assert person.identification_type == "CC"
    assert person.identification_number == "1000000000"
    assert person.status == "ACTIVE"


def test_valid_if_matches_any_rule_of_the_sigla(service) -> None:
    person = _create(service, identification_number="12345678")

    assert person.identification_number == "12345678"


def test_number_not_matching_any_rule_is_rejected(service, repository) -> None:
    with pytest.raises(InvalidIdentificationNumberError):
        _create(service, identification_number="12AB")

    assert repository.writes == 0


def test_sigla_without_rules_in_country_with_rules_uses_base_validation(service) -> None:
    """DS-03: el país tiene reglas PERSON, pero ninguna para la sigla PA."""
    person = _create(service, identification_type="PA", identification_number="X-99 libre")

    assert person.identification_type == "PA"


def test_country_without_rules_uses_base_validation(countries, repository) -> None:
    other_country = uuid4()
    countries.countries[other_country] = "PER"
    service = PersonIdentityService(repository, InMemoryRuleRepository(COLOMBIAN_RULES), countries)

    person = _create(service, identification_country_id=other_country, identification_number="ABC")

    assert person.identification_number == "ABC"


def test_rule_with_age_requires_birth_date(service) -> None:
    with pytest.raises(BirthDateRequiredError):
        _create(service, birth_date=None)


def test_age_out_of_range_in_every_matching_rule(service) -> None:
    with pytest.raises(AgeOutOfRangeError):
        _create(service, identification_type="TI", birth_date=_years_ago(30))


def test_age_in_range_is_accepted(service) -> None:
    person = _create(service, identification_type="TI", birth_date=_years_ago(10))

    assert person.identification_type == "TI"


def test_future_birth_date_is_rejected(service) -> None:
    with pytest.raises(BirthDateInFutureError):
        _create(service, birth_date=operational_today() + timedelta(days=1))


def test_unknown_country_does_not_persist(service, repository) -> None:
    with pytest.raises(CountryNotFoundError):
        _create(service, identification_country_id=uuid4())

    assert repository.writes == 0


@pytest.mark.parametrize("mode", ["unavailable", "denied"])
def test_geography_unavailable_does_not_persist(service, repository, countries, mode) -> None:
    countries.mode = mode

    with pytest.raises(DependencyUnavailableError):
        _create(service)

    assert repository.writes == 0


def test_duplicate_identification_is_rejected(service) -> None:
    _create(service)

    with pytest.raises(DuplicateIdentificationError):
        _create(service, first_name="OTRA")


def test_messages_and_logs_do_not_contain_full_number(service, caplog) -> None:
    caplog.set_level(logging.INFO, logger="party_identity_service")
    _create(service, identification_number="1234567890")

    with pytest.raises(InvalidIdentificationNumberError) as error:
        _create(service, identification_number="98765XYZ")

    assert "98765XYZ" not in error.value.message
    assert all("1234567890" not in record.getMessage() for record in caplog.records)
    assert any("******7890" in record.getMessage() for record in caplog.records)
