"""Empleados por sucursal (FR-025a): Party Identity se consulta con la lectura de la base cerrada (R-09)."""

from uuid import uuid4

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.branch_employees_service import BranchEmployeesService
from operational_context_service.infrastructure.application_user_repository import (
    SQLAlchemyApplicationUserRepository,
)
from operational_context_service.infrastructure.branch_repository import SQLAlchemyBranchRepository
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository
from operational_context_service.infrastructure.models import (
    ApplicationUserModel,
    BranchModel,
    CompanyModel,
)
from operational_context_service.infrastructure.user_branch_repository import (
    SQLAlchemyUserBranchRepository,
)
from tests.fakes import FakePersonDirectory

PLATFORM = AccessScope(subject="admin", is_platform_admin=True, can_lookup=True, member_company_ids=frozenset())


def test_persons_are_read_without_open_transaction(db_session):
    persons = FakePersonDirectory()
    persons.watched_sessions.append(db_session)
    company = CompanyModel(organization_identity_id=uuid4(), created_by="t", updated_by="t")
    db_session.add(company)
    db_session.flush()
    branch = BranchModel(company_id=company.id, code="PRINCIPAL", name="Sede", created_by="t", updated_by="t")
    user = ApplicationUserModel(
        company_id=company.id,
        keycloak_user_id="sub-" + uuid4().hex,
        person_identity_id=persons.add(),
        display_name="U",
        created_by="t",
        updated_by="t",
    )
    db_session.add_all([branch, user])
    db_session.commit()
    user_branches = SQLAlchemyUserBranchRepository(db_session)
    user_branches.create(application_user_id=user.id, branch_id=branch.id, company_id=company.id, actor_id="t")
    service = BranchEmployeesService(
        SQLAlchemyCompanyRepository(db_session),
        SQLAlchemyBranchRepository(db_session),
        user_branches,
        SQLAlchemyApplicationUserRepository(db_session),
        persons,
    )

    result = service.list(
        PLATFORM,
        company.id,
        branch_id=None,
        branch_status="ACTIVE",
        assignment_status="ACTIVE",
        search=None,
        page=1,
        page_size=20,
    )

    assert [len(group.employees) for group in result.items] == [1]
    assert result.items[0].employees[0].person is not None
    assert persons.count("get_person_profile") == 1
    assert persons.in_transaction_at_call == [False]
