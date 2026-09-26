"""Servicio de empresas con dobles instrumentados (FR-013, RN-03, R-09)."""

from uuid import uuid4

import pytest

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.company_service import CompanyService
from operational_context_service.application.exceptions import (
    DependencyUnavailableError,
    OrganizationIdentityNotFoundError,
)
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository

# Alcance de plataforma (Fase B): estas pruebas llaman a los servicios directamente.
PLATFORM = AccessScope(
    subject="test", is_platform_admin=True, can_lookup=True, member_company_ids=frozenset()
)


@pytest.fixture
def service(db_session, fake_organizations, fake_geography):
    fake_organizations.watched_sessions.append(db_session)
    fake_geography.watched_sessions.append(db_session)
    return CompanyService(SQLAlchemyCompanyRepository(db_session), fake_organizations, fake_geography)


def _data(organization_id, **overrides):
    data = {
        "organization_identity_id": organization_id,
        "timezone": "America/Bogota",
        "default_currency": "COP",
    }
    data.update(overrides)
    return data


def test_create_calls_party_identity_once_without_open_transaction(service, fake_organizations, fake_geography, geo):
    organization_id = fake_organizations.add()
    location = {
        "country_id": geo.colombia,
        "administrative_division_id": geo.antioquia,
        "city_id": geo.medellin,
    }

    company = service.create(_data(organization_id, **location), actor_id="sub-1")

    assert company.created_by == "sub-1" and company.updated_by == "sub-1"
    assert fake_organizations.count("get_organization") == 1
    assert fake_geography.count() == 3
    assert fake_organizations.in_transaction_at_call == [False]
    assert fake_geography.in_transaction_at_call == [False, False, False]


def test_update_calls_providers_without_open_transaction(service, fake_organizations, fake_geography, geo):
    company = service.create(_data(fake_organizations.add()), actor_id="sub-1")
    fake_organizations.reset()
    fake_geography.reset()
    new_organization = fake_organizations.add()

    service.update(
        PLATFORM,
        company.id,
        _data(new_organization, country_id=geo.colombia),
        expected_version=company.version,
        actor_id="sub-2",
    )

    assert fake_organizations.in_transaction_at_call == [False]
    assert fake_geography.in_transaction_at_call == [False]


def test_rejections_write_nothing(service, db_session, fake_organizations):
    with pytest.raises(OrganizationIdentityNotFoundError):
        service.create(_data(uuid4()), actor_id="sub-1")

    fake_organizations.mode = "unavailable"
    with pytest.raises(DependencyUnavailableError):
        service.create(_data(uuid4()), actor_id="sub-1")

    assert service.repository.exists_organization(uuid4()) is False
    from sqlalchemy import text

    assert db_session.execute(text("SELECT count(*) FROM companies")).scalar_one() == 0


def test_actor_comes_from_context_not_data(service, fake_organizations):
    company = service.create(
        {**_data(fake_organizations.add()), "created_by": "intruso"},
        actor_id="sub-real",
    )

    assert company.created_by == "sub-real"
