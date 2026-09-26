"""Orden de validación del alta de membresía (T034) con dobles y base de pruebas.

Empresa visible y `ACTIVE` → duplicado por persona → cuenta (Keycloak) →
duplicado por `sub` → persona (Party Identity) → inserción. Tras el primer
rechazo no se consulta nada más y las llamadas externas se hacen sin
transacción abierta.
"""

from uuid import uuid4

import pytest

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.application_user_service import ApplicationUserService
from operational_context_service.application.exceptions import (
    DuplicateMembershipError,
    KeycloakUserNotFoundError,
    NotFoundError,
    PersonIdentityNotFoundError,
)
from operational_context_service.infrastructure.application_user_repository import (
    SQLAlchemyApplicationUserRepository,
)
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository
from operational_context_service.infrastructure.models import CompanyModel
from tests.fakes import FakeIdentityAccountDirectory, FakePersonDirectory

PLATFORM = AccessScope(subject="admin", is_platform_admin=True, can_lookup=True, member_company_ids=frozenset())


@pytest.fixture
def company_id(db_session):
    company = CompanyModel(organization_identity_id=uuid4(), created_by="t", updated_by="t")
    db_session.add(company)
    db_session.commit()
    return company.id


@pytest.fixture
def doubles(db_session):
    accounts = FakeIdentityAccountDirectory()
    persons = FakePersonDirectory()
    accounts.watched_sessions.append(db_session)
    persons.watched_sessions.append(db_session)
    service = ApplicationUserService(
        SQLAlchemyApplicationUserRepository(db_session),
        SQLAlchemyCompanyRepository(db_session),
        accounts,
        persons,
    )
    return service, accounts, persons


def _data(person_id, **extra):
    return {"person_identity_id": person_id, "display_name": "P", "reference_email": None, **extra}


def test_happy_path_order_and_no_open_transaction(doubles, company_id):
    service, accounts, persons = doubles
    sub = accounts.add("ana")
    person = persons.add()

    user = service.create(PLATFORM, company_id, _data(person, username="ana"), actor_id="admin")

    assert user.keycloak_user_id == sub
    assert [name for name, _ in accounts.calls] == ["find_account_by_username"]
    assert [name for name, _ in persons.calls] == ["get_person"]
    assert not any(accounts.in_transaction_at_call + persons.in_transaction_at_call)


def test_duplicate_person_stops_before_calling_providers(doubles, company_id):
    service, accounts, persons = doubles
    person = persons.add()
    service.create(PLATFORM, company_id, _data(person, keycloak_user_id=accounts.add("a")), actor_id="x")
    accounts.reset()
    persons.reset()

    with pytest.raises(DuplicateMembershipError):
        service.create(PLATFORM, company_id, _data(person, keycloak_user_id=accounts.add("b")), actor_id="x")

    assert accounts.count() == 0 and persons.count() == 0


def test_unknown_account_stops_before_party_identity(doubles, company_id):
    service, accounts, persons = doubles

    with pytest.raises(KeycloakUserNotFoundError):
        service.create(PLATFORM, company_id, _data(persons.add(), username="nadie"), actor_id="x")

    assert persons.count() == 0


def test_duplicate_sub_stops_before_party_identity(doubles, company_id):
    service, accounts, persons = doubles
    sub = accounts.add("ana")
    service.create(PLATFORM, company_id, _data(persons.add(), keycloak_user_id=sub), actor_id="x")
    persons.reset()

    with pytest.raises(DuplicateMembershipError) as error:
        service.create(PLATFORM, company_id, _data(persons.add(), keycloak_user_id=sub), actor_id="x")

    assert error.value.field == "keycloak_user_id"
    assert persons.count() == 0


def test_unknown_person_is_rejected_last(doubles, company_id):
    service, accounts, persons = doubles

    with pytest.raises(PersonIdentityNotFoundError):
        service.create(PLATFORM, company_id, _data(uuid4(), username=None, keycloak_user_id=accounts.add("z")), actor_id="x")

    assert accounts.count() == 1


def test_company_out_of_scope_is_not_found_without_calls(doubles, company_id):
    service, accounts, persons = doubles
    outsider = AccessScope(subject="u", is_platform_admin=False, can_lookup=False, member_company_ids=frozenset())

    with pytest.raises(NotFoundError):
        service.create(outsider, company_id, _data(persons.add(), username="ana"), actor_id="u")

    assert accounts.count() == 0 and persons.count() == 0
