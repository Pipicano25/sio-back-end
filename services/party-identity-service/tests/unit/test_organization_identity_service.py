"""Pruebas del servicio de organizaciones con dobles (RC-04, RC-05, FR-031, DS-03).

Conserva las comprobaciones previas (patrón NIT en alta y modificación) sobre
el nuevo contrato.
"""

import logging
from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    UnsupportedIdentificationTypeError,
    CountryNotFoundError,
    DependencyUnavailableError,
    InvalidIdentificationNumberError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)
from tests.conftest import COLOMBIA_ID, FakeCountryDirectory
from tests.doubles import InMemoryOrganizationRepository, InMemoryRuleRepository

ACTOR_ID = "user-admin"
NIT_RULE = IdentificationRule(
    party_kind="ORGANIZATION",
    country_id=COLOMBIA_ID,
    identification_type="TAX_ID",
    sigla="NIT",
    pattern="^[0-9]{6,10}-[0-9]$",
    description="NIT con guion y dígito de verificación.",
)


@pytest.fixture
def countries() -> FakeCountryDirectory:
    return FakeCountryDirectory()


@pytest.fixture
def repository() -> InMemoryOrganizationRepository:
    return InMemoryOrganizationRepository()


@pytest.fixture
def service(repository, countries) -> OrganizationIdentityService:
    return OrganizationIdentityService(repository, InMemoryRuleRepository([NIT_RULE]), countries)


def base_payload(**overrides) -> dict:
    payload = {
        "country_id": COLOMBIA_ID,
        "identification_type": "nit",
        "identification_number": " 900123456-8 ",
        "legal_name": "ORGANIZACION FICTICIA S.A.S.",
        "trade_name": None,
        "organization_type": None,
        "registration_status": None,
        "website": None,
        "actor_id": ACTOR_ID,
    }
    payload.update(overrides)
    return payload


def test_create_accepts_identification_number_that_matches_rule(service) -> None:
    organization = service.create(**base_payload())

    assert organization.identification_type == "NIT"
    assert organization.identification_number == "900123456-8"
    assert organization.status == "ACTIVE"


def test_create_rejects_identification_number_that_does_not_match_rule(service, repository) -> None:
    with pytest.raises(InvalidIdentificationNumberError) as error:
        service.create(**base_payload(identification_number="900123456"))

    assert "dígito de verificación" in error.value.message
    assert repository.writes == 0


def test_update_rejects_identification_number_that_does_not_match_rule(service) -> None:
    organization = service.create(**base_payload())
    payload = base_payload(identification_number="ABC")
    payload.pop("actor_id")

    with pytest.raises(InvalidIdentificationNumberError):
        service.update(organization.id, expected_version=1, actor_id=ACTOR_ID, **payload)


def test_sigla_without_rule_in_country_with_rules_is_rejected(service) -> None:
    """DS-03 (enmienda 2026-11-18): el país tiene la regla NIT, pero no una para la sigla RUT."""
    with pytest.raises(UnsupportedIdentificationTypeError) as error:
        service.create(**base_payload(identification_type="RUT", identification_number="LIBRE-1"))

    assert "'RUT'" in error.value.message


def test_typo_in_sigla_is_rejected(service) -> None:
    """Un error de digitación (TRPE en vez de NIT) no crea una segunda organización con el mismo número."""
    with pytest.raises(UnsupportedIdentificationTypeError):
        service.create(**base_payload(identification_type="TRPE"))


def test_country_without_rules_is_rejected(service, countries) -> None:
    other_country = uuid4()
    countries.countries[other_country] = "PER"

    with pytest.raises(UnsupportedIdentificationTypeError):
        service.create(**base_payload(country_id=other_country, identification_number="20100070970"))


def test_unknown_country_does_not_persist(service, repository) -> None:
    with pytest.raises(CountryNotFoundError):
        service.create(**base_payload(country_id=uuid4()))

    assert repository.writes == 0


@pytest.mark.parametrize("mode", ["unavailable", "denied"])
def test_geography_unavailable_does_not_persist(service, repository, countries, mode) -> None:
    countries.mode = mode

    with pytest.raises(DependencyUnavailableError):
        service.create(**base_payload())

    assert repository.writes == 0


def test_logs_do_not_contain_full_number(service, caplog) -> None:
    caplog.set_level(logging.INFO, logger="party_identity_service")

    service.create(**base_payload(identification_number="900123456-8"))

    assert all("900123456-8" not in record.getMessage() for record in caplog.records)
