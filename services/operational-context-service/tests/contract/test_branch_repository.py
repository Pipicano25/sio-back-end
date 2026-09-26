"""Repositorio de sucursales (FR-021, FR-024, R-10)."""

from uuid import uuid4

import pytest

from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateBranchCodeError,
    NotFoundError,
)
from operational_context_service.application.ports import BranchFilters
from operational_context_service.infrastructure.branch_repository import SQLAlchemyBranchRepository
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository


def _company_values(**overrides):
    values = {field: None for field in (
        "email", "phone", "address_line", "country_id", "administrative_division_id",
        "city_id", "postal_code", "latitude", "longitude",
    )}
    values.update(organization_identity_id=uuid4(), timezone="America/Bogota", default_currency="COP")
    values.update(overrides)
    return values


def _branch_values(**overrides):
    values = {field: None for field in (
        "email", "phone", "address_line", "country_id", "administrative_division_id",
        "city_id", "postal_code", "latitude", "longitude", "timezone",
    )}
    values.update(code="B-01", name="Sucursal")
    values.update(overrides)
    return values


@pytest.fixture
def companies(db_session):
    return SQLAlchemyCompanyRepository(db_session)


@pytest.fixture
def branches(db_session):
    return SQLAlchemyBranchRepository(db_session)


def test_create_and_get_with_calculated_fields(companies, branches):
    company = companies.create(_company_values(timezone="America/Lima"), actor_id="sub")

    branch = branches.create_in_active_company(company.id, _branch_values(), actor_id="sub")

    assert branch.company_status == "ACTIVE"
    assert branch.timezone is None
    assert branch.effective_timezone == "America/Lima"
    assert branches.get_by_id(branch.id) == branch


def test_own_timezone_prevails_in_query(companies, branches):
    company = companies.create(_company_values(), actor_id="sub")

    branch = branches.create_in_active_company(company.id, _branch_values(timezone="Europe/Madrid"), actor_id="sub")

    assert branch.effective_timezone == "Europe/Madrid"


def test_duplicate_code_is_translated(companies, branches):
    company = companies.create(_company_values(), actor_id="sub")
    branches.create_in_active_company(company.id, _branch_values(), actor_id="sub")

    with pytest.raises(DuplicateBranchCodeError):
        branches.create_in_active_company(company.id, _branch_values(), actor_id="sub")


def test_create_under_inactive_or_missing_company(companies, branches):
    company = companies.create(_company_values(), actor_id="sub")
    companies.update(company.id, expected_version=1, values={"status": "INACTIVE"}, actor_id="sub")

    with pytest.raises(CompanyInactiveError):
        branches.create_in_active_company(company.id, _branch_values(), actor_id="sub")

    with pytest.raises(NotFoundError):
        branches.create_in_active_company(uuid4(), _branch_values(), actor_id="sub")


def test_list_by_company_with_filters(companies, branches):
    company = companies.create(_company_values(), actor_id="sub")
    city = uuid4()
    first = branches.create_in_active_company(
        company.id, _branch_values(code="A", name="Alfa", country_id=uuid4(), city_id=city), actor_id="sub",
    )
    branches.create_in_active_company(company.id, _branch_values(code="B", name="Beta"), actor_id="sub")

    by_city = branches.list_by_company(company.id, BranchFilters(city_id=city), page=1, page_size=10)
    by_search = branches.list_by_company(company.id, BranchFilters(search="alf"), page=1, page_size=10)

    assert [b.id for b in by_city.items] == [first.id]
    assert [b.id for b in by_search.items] == [first.id]


def test_exists_code(companies, branches):
    company = companies.create(_company_values(), actor_id="sub")
    branch = branches.create_in_active_company(company.id, _branch_values(code="X"), actor_id="sub")

    assert branches.exists_code(company.id, "X")
    assert not branches.exists_code(company.id, "X", exclude_branch_id=branch.id)
    assert not branches.exists_code(company.id, "Y")
