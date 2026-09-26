"""Repositorio de empresas (FR-014, FR-015, R-09)."""

from uuid import uuid4

import pytest

from operational_context_service.application.exceptions import DuplicateOrganizationIdentityError
from operational_context_service.application.ports import CompanyFilters
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository


@pytest.fixture
def repository(db_session):
    return SQLAlchemyCompanyRepository(db_session)


def _values(**overrides):
    values = {
        "organization_identity_id": uuid4(),
        "email": None,
        "phone": None,
        "address_line": None,
        "country_id": None,
        "administrative_division_id": None,
        "city_id": None,
        "postal_code": None,
        "latitude": None,
        "longitude": None,
        "timezone": "America/Bogota",
        "default_currency": "COP",
    }
    values.update(overrides)
    return values


def test_create_and_get(repository):
    created = repository.create(_values(), actor_id="sub")

    loaded = repository.get_by_id(created.id)

    assert loaded == created
    assert loaded.version == 1 and loaded.status == "ACTIVE"


def test_get_unknown_returns_none(repository):
    assert repository.get_by_id(uuid4()) is None


def test_duplicate_organization_is_translated(repository):
    organization_id = uuid4()
    repository.create(_values(organization_identity_id=organization_id), actor_id="sub")

    with pytest.raises(DuplicateOrganizationIdentityError):
        repository.create(_values(organization_identity_id=organization_id), actor_id="sub")


def test_exists_organization(repository):
    created = repository.create(_values(), actor_id="sub")

    assert repository.exists_organization(created.organization_identity_id)
    assert not repository.exists_organization(created.organization_identity_id, exclude_company_id=created.id)
    assert not repository.exists_organization(uuid4())


def test_list_filters_and_stable_pagination(repository):
    country = uuid4()
    first = repository.create(_values(country_id=country), actor_id="sub")
    second = repository.create(_values(country_id=country), actor_id="sub")
    repository.create(_values(), actor_id="sub")

    page = repository.list_all(CompanyFilters(country_id=country), page=1, page_size=1)

    assert page.total_records == 2 and page.total_pages == 2
    assert [c.id for c in page.items] == [first.id]
    assert [c.id for c in repository.list_all(CompanyFilters(country_id=country), page=2, page_size=1).items] == [second.id]


def test_update_increments_version_and_actor(repository):
    created = repository.create(_values(), actor_id="sub-1")

    updated = repository.update(created.id, expected_version=1, values={"phone": "123"}, actor_id="sub-2")

    assert updated.version == 2 and updated.phone == "123"
    assert updated.created_by == "sub-1" and updated.updated_by == "sub-2"


def test_end_read_closes_transaction(repository, db_session):
    repository.get_by_id(uuid4())
    assert db_session.in_transaction()

    repository.end_read()

    assert not db_session.in_transaction()
