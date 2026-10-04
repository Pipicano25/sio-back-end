"""Alcance por empresa e identidad técnica (R-02, R-11; RC-02, RC-03, FR-042, FR-061)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sio_auth.permissions import extract_permission_grants

from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
    is_technical_identity,
)
from commercial_relationship_service.application.exceptions import (
    CompanyInactiveError,
    NotFoundError,
)
from commercial_relationship_service.application.ports import CompanyAccess

LOOKUP = "perm:commercial-relationship:platform:lookup"


def _identity(roles, **claims) -> RequestIdentity:
    return RequestIdentity.build(
        subject="sub", grants=extract_permission_grants(roles), raw_claims=claims
    )


SERVICE_ACCOUNT = {"client_id": "inventory-service", "preferred_username": "service-account-inventory-service"}


# ------------------------------------------------------------ identidad técnica


def test_coherent_service_account_is_technical():
    assert is_technical_identity(SERVICE_ACCOUNT)


@pytest.mark.parametrize(
    "claims",
    [
        {"preferred_username": "service-account-x"},  # sin client_id
        {"client_id": "x", "preferred_username": "service-account-y"},  # no correlaciona
        {"client_id": "x", "preferred_username": "x"},
        {"client_id": "x"},  # sin preferred_username
        {"client_id": "", "preferred_username": "service-account-"},
        {"azp": "x", "preferred_username": "service-account-x"},  # azp no sustituye a client_id
        {"preferred_username": "admin.test", "sid": "s"},
    ],
)
def test_not_technical(claims):
    assert not is_technical_identity(claims)


@pytest.mark.parametrize("sid", [None, "session"])
def test_sid_does_not_change_the_result(sid):
    claims = dict(SERVICE_ACCOUNT)
    if sid:
        claims["sid"] = sid
    assert is_technical_identity(claims)


# -------------------------------------------------------------- exención (R-11)


def test_human_with_all_all_all_has_no_exemption():
    identity = _identity(["perm:all:all:all"], preferred_username="admin.test", sid="s")
    assert identity.technical_lookup is False


def test_human_named_like_service_account_without_client_id_has_no_exemption():
    identity = _identity([LOOKUP], preferred_username="service-account-x", sid="s")
    assert identity.technical_lookup is False


def test_mismatched_client_id_has_no_exemption():
    identity = _identity([LOOKUP], client_id="x", preferred_username="service-account-y")
    assert identity.technical_lookup is False


def test_service_account_with_lookup_has_exemption():
    assert _identity([LOOKUP], **SERVICE_ACCOUNT).technical_lookup is True


def test_service_account_without_lookup_has_no_exemption():
    assert _identity(["perm:commercial-relationship:company_products:read"], **SERVICE_ACCOUNT).technical_lookup is False


def test_read_wildcard_does_not_grant_lookup():
    for roles in (["perm:commercial-relationship:all:read"], ["perm:all:all:read"]):
        assert _identity(roles, **SERVICE_ACCOUNT).technical_lookup is False


# ------------------------------------------------------------------ membresía


class AccessStub:
    def __init__(self, access: CompanyAccess) -> None:
        self.access = access
        self.calls = 0

    def check_company_access(self, company_id):
        self.calls += 1
        return self.access


def test_require_member_not_member_is_not_found():
    stub = AccessStub(CompanyAccess(member_active=False, company_active=None))
    with pytest.raises(NotFoundError):
        CompanyScopeService(stub).require_member(uuid4(), write=False)
    assert stub.calls == 1


def test_require_member_write_with_inactive_company():
    stub = AccessStub(CompanyAccess(member_active=True, company_active=False))
    service = CompanyScopeService(stub)

    with pytest.raises(CompanyInactiveError):
        service.require_member(uuid4(), write=True)

    service.require_member(uuid4(), write=True, allow_inactive_company=True)
    service.require_member(uuid4(), write=False)
    assert stub.calls == 3  # una sola llamada por invocación, sin caché


def test_require_member_ok():
    stub = AccessStub(CompanyAccess(member_active=True, company_active=True))
    CompanyScopeService(stub).require_member(uuid4(), write=True)
    assert stub.calls == 1
