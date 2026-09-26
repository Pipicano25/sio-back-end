"""Repositorio de asignaciones usuario–sucursal contra la base de pruebas (T049)."""

from uuid import uuid4

import pytest

from operational_context_service.application.exceptions import (
    BranchCompanyMismatchError,
    DuplicateUserBranchError,
    InvalidStatusTransitionError,
)
from operational_context_service.infrastructure.models import (
    ApplicationUserModel,
    BranchModel,
    CompanyModel,
)
from operational_context_service.infrastructure.user_branch_repository import (
    SQLAlchemyUserBranchRepository,
)


@pytest.fixture
def repository(db_session):
    return SQLAlchemyUserBranchRepository(db_session)


def _company_with(db_session, code="B-1"):
    company = CompanyModel(organization_identity_id=uuid4(), created_by="t", updated_by="t")
    db_session.add(company)
    db_session.flush()
    branch = BranchModel(company_id=company.id, code=code, name="S", created_by="t", updated_by="t")
    user = ApplicationUserModel(
        company_id=company.id,
        keycloak_user_id="sub-" + uuid4().hex,
        person_identity_id=uuid4(),
        display_name="U",
        created_by="t",
        updated_by="t",
    )
    db_session.add_all([branch, user])
    db_session.commit()
    return company.id, branch.id, user.id


def test_create_reads_calculated_statuses(repository, db_session):
    company, branch, user = _company_with(db_session)

    created = repository.create(application_user_id=user, branch_id=branch, company_id=company, actor_id="a")

    assert created.assigned_by == "a" and created.status == "ACTIVE"
    assert created.membership_status == created.branch_status == created.company_status == "ACTIVE"


def test_duplicate_pair_is_translated(repository, db_session):
    company, branch, user = _company_with(db_session)
    repository.create(application_user_id=user, branch_id=branch, company_id=company, actor_id="a")

    with pytest.raises(DuplicateUserBranchError):
        repository.create(application_user_id=user, branch_id=branch, company_id=company, actor_id="a")


def test_composite_fk_rejects_other_company(repository, db_session):
    company, _, user = _company_with(db_session, "A-1")
    _, foreign_branch, _ = _company_with(db_session, "Z-1")

    with pytest.raises(BranchCompanyMismatchError):
        repository.create(application_user_id=user, branch_id=foreign_branch, company_id=company, actor_id="a")


def test_deactivate_and_reactivate_manage_dates_and_author(repository, db_session):
    company, branch, user = _company_with(db_session)
    created = repository.create(application_user_id=user, branch_id=branch, company_id=company, actor_id="a")

    retired = repository.deactivate(created.id, expected_version=1, actor_id="b")
    assert retired.status == "INACTIVE" and retired.deactivated_at is not None
    assert retired.assigned_by == "a" and retired.updated_by == "b"

    with pytest.raises(InvalidStatusTransitionError):
        repository.deactivate(created.id, expected_version=2, actor_id="b")

    back = repository.reactivate(created.id, expected_version=2, actor_id="c")
    assert back.status == "ACTIVE" and back.deactivated_at is None
    assert back.assigned_by == "c" and back.assigned_at > created.assigned_at


def test_list_filters_and_pagination(repository, db_session):
    company, branch, user = _company_with(db_session)
    repository.create(application_user_id=user, branch_id=branch, company_id=company, actor_id="a")

    by_user = repository.list_by(application_user_id=user, status="ACTIVE", page=1, page_size=10)
    by_branch_inactive = repository.list_by(branch_id=branch, status="INACTIVE", page=1, page_size=10)

    assert by_user.total_records == 1
    assert by_branch_inactive.total_records == 0
