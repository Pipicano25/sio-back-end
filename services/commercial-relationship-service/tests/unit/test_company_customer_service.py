"""Orden y mapeos del servicio de clientes (FR-020 a FR-028; R-06, R-07; DS-08, RC-06)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.company_customer_service import (
    CompanyCustomerService,
)
from commercial_relationship_service.application.exceptions import (
    ContactPersonInvalidError,
    ContactPersonNotAllowedError,
    DependencyUnavailableError,
    DuplicateCustomerError,
    DuplicateInternalCodeError,
    OperationalAccessDeniedError,
    OrganizationIdentityInactiveError,
    PartyIdentityAccessDeniedError,
    PersonIdentityNotFoundError,
    SelfRelationshipNotAllowedError,
)
from tests.fakes import FakeOperationalContext, FakePartyIdentity


class RepositoryStub:
    duplicates: dict = {}

    def __init__(self, *, identity_taken=False, code_taken=False) -> None:
        self.identity_taken = identity_taken
        self.taken = code_taken
        self.events: list[str] = []
        self.saved = None

    def identity_exists(self, company_id, **kwargs):
        self.events.append("identity_exists")
        return self.identity_taken

    def code_taken(self, company_id, code, exclude_id=None):
        self.events.append("code_taken")
        return self.taken

    def create(self, **fields):
        self.events.append("create")
        return fields

    def load_for_update(self, entity_id, *, expected_version):
        self.events.append("load_for_update")
        return self.current

    def save(self, model, *, duplicates):
        self.events.append("save")
        self.saved = model
        return model

    def release(self):
        self.events.append("release")


def _service(repository, party, oc):
    company = uuid4()
    oc.organizations[company] = uuid4()
    return company, CompanyCustomerService(repository, lambda: party, lambda: oc.companies_for(None))


def _org_values(organization, **overrides):
    values = {
        "customer_kind": "ORGANIZATION",
        "person_identity_id": None,
        "organization_identity_id": organization,
        "internal_code": "C-1",
        "display_name": "Cliente",
        "preferred_contact_person_id": None,
    }
    values.update(overrides)
    return values


def test_organization_order_self_check_identity_then_contact():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    company, service = _service(repository, party, oc)
    organization, contact = uuid4(), uuid4()
    party.organizations[organization] = "ACTIVE"
    party.add_contact(contact, organization)

    service.create(company, _org_values(organization, preferred_contact_person_id=contact), actor="s")

    assert repository.events == ["identity_exists", "code_taken", "create"]
    assert oc.company_calls == [company]
    assert [call[0] for call in party.calls] == ["get_organization", "get_contact_person"]


def test_person_does_not_query_company():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    company, service = _service(repository, party, oc)
    person = uuid4()
    party.persons[person] = "ACTIVE"

    service.create(
        company,
        {"customer_kind": "PERSON", "person_identity_id": person, "organization_identity_id": None,
         "internal_code": "C", "display_name": "D", "preferred_contact_person_id": None},
        actor="s",
    )
    assert oc.company_calls == []


@pytest.mark.parametrize(
    ("repository", "error"),
    [(RepositoryStub(identity_taken=True), DuplicateCustomerError), (RepositoryStub(code_taken=True), DuplicateInternalCodeError)],
)
def test_local_uniqueness_before_providers(repository, error):
    party, oc = FakePartyIdentity(), FakeOperationalContext()
    company, service = _service(repository, party, oc)

    with pytest.raises(error):
        service.create(company, _org_values(uuid4()), actor="s")

    assert party.calls == [] and oc.company_calls == []


def test_self_relationship_before_party_identity():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    company, service = _service(repository, party, oc)

    with pytest.raises(SelfRelationshipNotAllowedError):
        service.create(company, _org_values(oc.organizations[company]), actor="s")

    assert party.calls == []
    assert "create" not in repository.events


@pytest.mark.parametrize(
    ("setup", "error"),
    [
        (lambda party, oc: setattr(oc, "company_forbidden", True), OperationalAccessDeniedError),
        (lambda party, oc: setattr(oc, "company_unavailable", True), DependencyUnavailableError),
        (lambda party, oc: setattr(party, "forbidden", True), PartyIdentityAccessDeniedError),
        (lambda party, oc: setattr(party, "unavailable", True), DependencyUnavailableError),
    ],
)
def test_provider_failures_save_nothing(setup, error):
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    company, service = _service(repository, party, oc)
    organization = uuid4()
    party.organizations[organization] = "ACTIVE"
    setup(party, oc)

    with pytest.raises(error):
        service.create(company, _org_values(organization), actor="s")

    assert "create" not in repository.events


def test_inactive_organization_and_invalid_contact():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    company, service = _service(repository, party, oc)
    organization = uuid4()
    party.organizations[organization] = "INACTIVE"

    with pytest.raises(OrganizationIdentityInactiveError):
        service.create(company, _org_values(organization), actor="s")

    party.organizations[organization] = "ACTIVE"
    other_org_contact = party.add_contact(uuid4(), uuid4())
    with pytest.raises(ContactPersonInvalidError):
        service.create(company, _org_values(organization, preferred_contact_person_id=other_org_contact), actor="s")


def test_reactivation_validates_identity_not_contact():
    party, oc = FakePartyIdentity(), FakeOperationalContext()
    repository = RepositoryStub()
    _, service = _service(repository, party, oc)
    organization, contact = uuid4(), uuid4()
    party.organizations[organization] = "ACTIVE"
    party.add_contact(contact, organization, is_active=False)
    current = SimpleNamespace(
        id=uuid4(), status="INACTIVE", customer_kind="ORGANIZATION", person_identity_id=None,
        organization_identity_id=organization, preferred_contact_person_id=contact,
    )
    repository.current = current

    service.reactivate(current, version=1, actor="s")

    assert [call[0] for call in party.calls] == ["get_organization"]
    assert repository.saved.status == "ACTIVE"
    assert repository.saved.preferred_contact_person_id == contact


def test_reactivation_of_missing_person():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    _, service = _service(repository, party, oc)
    current = SimpleNamespace(id=uuid4(), status="INACTIVE", customer_kind="PERSON", person_identity_id=uuid4())

    with pytest.raises(PersonIdentityNotFoundError):
        service.reactivate(current, version=1, actor="s")


def test_update_queries_contact_only_when_it_changes_to_non_null():
    party, oc = FakePartyIdentity(), FakeOperationalContext()
    repository = RepositoryStub()
    _, service = _service(repository, party, oc)
    organization, contact = uuid4(), uuid4()
    current = SimpleNamespace(
        id=uuid4(), company_id=uuid4(), customer_kind="ORGANIZATION", organization_identity_id=organization,
        internal_code="C", display_name="D", preferred_contact_person_id=contact,
    )
    repository.current = SimpleNamespace(**vars(current))

    service.update(current, {"internal_code": "C", "display_name": "D2", "preferred_contact_person_id": contact}, version=1, actor="s")
    service.update(current, {"internal_code": "C", "display_name": "D2", "preferred_contact_person_id": None}, version=1, actor="s")
    assert party.calls == []


def test_update_contact_on_person_is_not_allowed():
    party, oc, repository = FakePartyIdentity(), FakeOperationalContext(), RepositoryStub()
    _, service = _service(repository, party, oc)
    current = SimpleNamespace(id=uuid4(), company_id=uuid4(), customer_kind="PERSON", internal_code="C",
                              preferred_contact_person_id=None)

    with pytest.raises(ContactPersonNotAllowedError):
        service.update(current, {"internal_code": "C", "display_name": "D", "preferred_contact_person_id": uuid4()}, version=1, actor="s")
