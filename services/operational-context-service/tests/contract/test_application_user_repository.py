"""Repositorio de usuarios operativos contra la base de pruebas (T035)."""

from uuid import uuid4

import pytest

from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateMembershipError,
    VersionConflictError,
)
from operational_context_service.application.ports import ApplicationUserFilters
from operational_context_service.infrastructure.application_user_repository import (
    SQLAlchemyApplicationUserRepository,
)
from operational_context_service.infrastructure.models import CompanyModel


@pytest.fixture
def repository(db_session):
    return SQLAlchemyApplicationUserRepository(db_session)


def _company(db_session, status="ACTIVE"):
    company = CompanyModel(
        organization_identity_id=uuid4(),
        status=status,
        created_by="t",
        updated_by="t",
    )
    db_session.add(company)
    db_session.commit()
    return company.id


def _values(**overrides):
    values = {
        "keycloak_user_id": "sub-" + uuid4().hex,
        "person_identity_id": uuid4(),
        "display_name": "Usuario Ficticio",
        "reference_email": None,
    }
    values.update(overrides)
    return values


def test_create_and_read_with_company_status(repository, db_session):
    company = _company(db_session)

    user = repository.create_in_active_company(company, _values(), actor_id="actor")

    assert user.company_status == "ACTIVE"
    assert user.created_by == user.updated_by == "actor"
    assert repository.get_by_id(user.id) == user


def test_create_under_inactive_company_is_rejected(repository, db_session):
    with pytest.raises(CompanyInactiveError):
        repository.create_in_active_company(_company(db_session, "INACTIVE"), _values(), actor_id="a")


def test_duplicate_active_is_translated_with_field(repository, db_session):
    company = _company(db_session)
    person = uuid4()
    repository.create_in_active_company(company, _values(person_identity_id=person), actor_id="a")

    with pytest.raises(DuplicateMembershipError) as error:
        repository.create_in_active_company(company, _values(person_identity_id=person), actor_id="a")

    assert error.value.field == "person_identity_id"


def test_filters_search_and_stable_order(repository, db_session):
    company = _company(db_session)
    first = repository.create_in_active_company(company, _values(display_name="Zoe Ficticia"), actor_id="a")
    second = repository.create_in_active_company(
        company, _values(display_name="Ana", reference_email="ZOE@correo.co"), actor_id="a"
    )

    page = repository.list_by_company(
        company, ApplicationUserFilters(search="zoe"), page=1, page_size=10
    )

    assert [item.id for item in page.items] == [first.id, second.id]
    assert page.total_records == 2


def test_update_checks_version(repository, db_session):
    user = repository.create_in_active_company(_company(db_session), _values(), actor_id="a")

    updated = repository.update(user.id, expected_version=1, values={"display_name": "Nuevo"}, actor_id="b")
    assert updated.version == 2 and updated.updated_by == "b"

    with pytest.raises(VersionConflictError):
        repository.update(user.id, expected_version=1, values={"display_name": "X"}, actor_id="b")


def test_exists_active_ignores_inactive_and_excluded(repository, db_session):
    company = _company(db_session)
    person = uuid4()
    user = repository.create_in_active_company(company, _values(person_identity_id=person), actor_id="a")

    assert repository.exists_active(company, person_identity_id=person)
    assert not repository.exists_active(company, person_identity_id=person, exclude_id=user.id)
    repository.update(user.id, expected_version=1, values={"status": "INACTIVE"}, actor_id="a")
    assert not repository.exists_active(company, person_identity_id=person)
