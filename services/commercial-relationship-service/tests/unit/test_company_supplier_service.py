"""Servicio de proveedores (FR-030 a FR-034, FR-033a; DS-08, DS-10; RC-08)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from commercial_relationship_service.application.company_supplier_service import (
    CompanySupplierService,
)
from commercial_relationship_service.application.exceptions import (
    DuplicateSupplierError,
    OrganizationIdentityInactiveError,
    SelfRelationshipNotAllowedError,
)
from commercial_relationship_service.domain.errors import InvalidStatusTransitionError
from tests.fakes import FakeOperationalContext, FakePartyIdentity


class RepositoryStub:
    duplicates: dict = {}

    def __init__(self, current=None, *, org_taken=False) -> None:
        self.current = current
        self.org_taken = org_taken
        self.saved = None

    def organization_exists(self, company_id, organization_identity_id):
        return self.org_taken

    def code_taken(self, *args, **kwargs):
        return False

    def create(self, **fields):
        return fields

    def load_for_update(self, entity_id, *, expected_version):
        return self.current

    def save(self, model, *, duplicates):
        self.saved = model
        return model

    def release(self):
        pass


def _supplier(status, **extra):
    return SimpleNamespace(
        id=uuid4(), company_id=uuid4(), status=status, organization_identity_id=uuid4(),
        internal_code="S", display_name="D", preferred_contact_person_id=None, block_reason=None, **extra,
    )


def _service(repository, party=None, oc=None):
    party = party or FakePartyIdentity()
    oc = oc or FakeOperationalContext()
    return CompanySupplierService(repository, lambda: party, lambda: oc.companies_for(None)), party, oc


@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE"])
def test_block_requires_reason_and_does_not_query_party_identity(status):
    current = _supplier(status)
    service, party, _ = _service(RepositoryStub(current))

    blocked = service.block(current, block_reason="Incumplimiento", version=1, actor="s")

    assert blocked.status == "BLOCKED" and blocked.block_reason == "Incumplimiento"
    assert party.calls == []


def test_unblock_revalidates_organization_and_clears_reason_without_contact_check():
    current = _supplier("BLOCKED", )
    current.block_reason = "Motivo"
    current.preferred_contact_person_id = uuid4()
    party = FakePartyIdentity()
    party.organizations[current.organization_identity_id] = "ACTIVE"
    service, party, _ = _service(RepositoryStub(current), party)

    unblocked = service.unblock(current, version=1, actor="s")

    assert unblocked.status == "ACTIVE" and unblocked.block_reason is None
    assert [call[0] for call in party.calls] == ["get_organization"]


def test_unblock_with_inactive_organization():
    current = _supplier("BLOCKED")
    current.block_reason = "M"
    party = FakePartyIdentity()
    party.organizations[current.organization_identity_id] = "INACTIVE"
    service, _, _ = _service(RepositoryStub(current), party)

    with pytest.raises(OrganizationIdentityInactiveError):
        service.unblock(current, version=1, actor="s")


@pytest.mark.parametrize(
    ("status", "action"),
    [("BLOCKED", "deactivate"), ("BLOCKED", "reactivate"), ("ACTIVE", "unblock"), ("ACTIVE", "reactivate")],
)
def test_invalid_transitions(status, action):
    current = _supplier(status)
    service, party, _ = _service(RepositoryStub(current))

    with pytest.raises(InvalidStatusTransitionError):
        getattr(service, action)(current, version=1, actor="s")

    assert party.calls == []  # se rechaza antes de consultar Party Identity


def test_block_blocked_is_invalid():
    current = _supplier("BLOCKED")
    service, _, _ = _service(RepositoryStub(current))
    with pytest.raises(InvalidStatusTransitionError):
        service.block(current, block_reason="x", version=1, actor="s")


def test_create_rejects_duplicate_and_self_relationship():
    service, party, oc = _service(RepositoryStub(org_taken=True))
    with pytest.raises(DuplicateSupplierError):
        service.create(uuid4(), {"organization_identity_id": uuid4(), "internal_code": "S", "display_name": "D"}, actor="s")

    service, party, oc = _service(RepositoryStub())
    company = uuid4()
    oc.organizations[company] = own = uuid4()
    with pytest.raises(SelfRelationshipNotAllowedError):
        service.create(company, {"organization_identity_id": own, "internal_code": "S", "display_name": "D"}, actor="s")
    assert party.calls == []
