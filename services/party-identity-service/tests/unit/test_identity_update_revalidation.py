"""Revalidación solo ante cambios de identificación (FR-026, FR-034, FR-029, DS-06)."""

from datetime import timedelta
from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    AgeOutOfRangeError,
    VersionConflictError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
    operational_today,
)
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)
from party_identity_service.application.person_identity_service import (
    PersonIdentityService,
)
from tests.conftest import COLOMBIA_ID, FakeCountryDirectory
from tests.doubles import (
    InMemoryOrganizationRepository,
    InMemoryPersonRepository,
    InMemoryRuleRepository,
)

RULES = [
    IdentificationRule("PERSON", COLOMBIA_ID, "CITIZEN_ID_MODERN", "CC", r"^[0-9]{10}$", "CC moderna.", 18, None),
    IdentificationRule("PERSON", COLOMBIA_ID, "IDENTITY_CARD_MODERN", "TI", r"^[0-9]{10}$", "TI moderna.", 7, 17),
    IdentificationRule("ORGANIZATION", COLOMBIA_ID, "TAX_ID", "NIT", r"^[A-Z0-9]{4,11}-[0-9]$", "NIT.", None, None),
]


def _years_ago(years: int):
    today = operational_today()
    return today.replace(year=today.year - years) - timedelta(days=1)


@pytest.fixture
def countries() -> FakeCountryDirectory:
    return FakeCountryDirectory()


@pytest.fixture
def people(countries) -> PersonIdentityService:
    return PersonIdentityService(InMemoryPersonRepository(), InMemoryRuleRepository(RULES), countries)


@pytest.fixture
def organizations(countries) -> OrganizationIdentityService:
    return OrganizationIdentityService(InMemoryOrganizationRepository(), InMemoryRuleRepository(RULES), countries)


def _person_values(**overrides) -> dict:
    values = {
        "identification_country_id": COLOMBIA_ID,
        "identification_type": "CC",
        "identification_number": "1000000001",
        "first_name": "ANA",
        "middle_name": None,
        "last_name": "PRUEBA",
        "second_last_name": None,
        "birth_date": _years_ago(30),
        "verification_status": "UNVERIFIED",
    }
    values.update(overrides)
    return values


def _org_values(**overrides) -> dict:
    values = {
        "country_id": COLOMBIA_ID,
        "identification_type": "NIT",
        "identification_number": "900000001-1",
        "legal_name": "ORGANIZACION FICTICIA S.A.S.",
        "trade_name": None,
        "organization_type": None,
        "registration_status": None,
        "website": None,
    }
    values.update(overrides)
    return values


def _created_person(people, countries):
    person = people.create(**_person_values(), actor_id="creador")
    countries.calls.clear()
    return person


def test_person_change_without_identification_does_not_call_geography(people, countries) -> None:
    person = _created_person(people, countries)
    countries.mode = "unavailable"

    updated = people.update(
        person.id,
        expected_version=1,
        actor_id="editor",
        **_person_values(first_name="ANA MARIA", identification_type=" cc "),
    )

    assert updated.first_name == "ANA MARIA"
    assert updated.version == 2
    assert countries.calls == []


@pytest.mark.parametrize(
    "change",
    [
        {"identification_number": "1000000002"},
        {"identification_type": "TI", "birth_date": _years_ago(10)},
    ],
)
def test_person_identification_change_calls_geography_once(people, countries, change) -> None:
    person = _created_person(people, countries)

    people.update(person.id, expected_version=1, actor_id="editor", **_person_values(**change))

    assert countries.exists_calls == 1


def test_person_country_change_calls_geography(people, countries) -> None:
    person = _created_person(people, countries)
    other = uuid4()
    countries.countries[other] = "PER"

    people.update(person.id, expected_version=1, actor_id="editor", **_person_values(identification_country_id=other))

    assert countries.calls == [("exists", other)]


def test_only_birth_date_change_recalculates_age_locally(people, countries) -> None:
    person = _created_person(people, countries)
    countries.mode = "unavailable"

    with pytest.raises(AgeOutOfRangeError):
        people.update(person.id, expected_version=1, actor_id="editor", **_person_values(birth_date=_years_ago(10)))

    updated = people.update(person.id, expected_version=1, actor_id="editor", **_person_values(birth_date=_years_ago(40)))

    assert updated.birth_date == _years_ago(40)
    assert countries.calls == []


def test_identical_put_does_not_write_or_call_geography(people, countries) -> None:
    person = _created_person(people, countries)
    repository = people.repository
    writes = repository.writes

    result = people.update(
        person.id,
        expected_version=1,
        actor_id="otro-usuario",
        **_person_values(identification_type="cc", identification_number=" 1000000001 "),
    )

    assert result.version == 1
    assert result.updated_by == "creador"
    assert result.updated_at == person.updated_at
    assert repository.writes == writes
    assert countries.calls == []


def test_identical_put_with_stale_version_is_conflict(people, countries) -> None:
    person = _created_person(people, countries)
    people.update(person.id, expected_version=1, actor_id="editor", **_person_values(first_name="OTRO"))

    with pytest.raises(VersionConflictError):
        people.update(person.id, expected_version=1, actor_id="editor", **_person_values(first_name="OTRO"))


def test_organization_change_without_identification_does_not_call_geography(organizations, countries) -> None:
    organization = organizations.create(**_org_values(), actor_id="creador")
    countries.calls.clear()
    countries.mode = "unavailable"

    updated = organizations.update(
        organization.id,
        expected_version=1,
        actor_id="editor",
        **_org_values(legal_name="NUEVA RAZON SOCIAL", identification_type="nit"),
    )

    assert updated.legal_name == "NUEVA RAZON SOCIAL"
    assert countries.calls == []


def test_organization_identification_change_calls_geography(organizations, countries) -> None:
    organization = organizations.create(**_org_values(), actor_id="creador")
    countries.calls.clear()

    organizations.update(
        organization.id,
        expected_version=1,
        actor_id="editor",
        **_org_values(identification_number="900000009-9"),
    )

    assert countries.exists_calls == 1


def test_identical_organization_put_does_not_write(organizations, countries) -> None:
    organization = organizations.create(**_org_values(), actor_id="creador")
    writes = organizations.repository.writes

    result = organizations.update(organization.id, expected_version=1, actor_id="otro", **_org_values())

    assert result.version == 1
    assert organizations.repository.writes == writes
