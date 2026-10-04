"""Adaptador de Party Identity con `httpx.MockTransport` (R-06, RC-06, FR-054).

Contrato: `specs/007-commercial-relationship-core/contracts/party-identity-dependency.md`.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    DependencyUnavailableError,
    PartyIdentityAccessDeniedError,
)
from commercial_relationship_service.infrastructure.party_identity_directory import (
    HTTPPartyDirectory,
)

TOKEN = "Bearer user-token"


def _directory(handler) -> HTTPPartyDirectory:
    return HTTPPartyDirectory(
        base_url="http://pi.test/api/v1",
        authorization=TOKEN,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [("get_person", "person-identities"), ("get_organization", "organization-identities")],
)
@pytest.mark.parametrize("status", ["ACTIVE", "INACTIVE"])
def test_identity_status_and_user_token(method, path, status):
    identity = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/{path}/{identity}"
        assert request.headers["authorization"] == TOKEN
        return httpx.Response(200, json={"id": str(identity), "status": status, "legal_name": "x"})

    ref = getattr(_directory(handler), method)(identity)
    assert ref.id == identity and ref.status == status


@pytest.mark.parametrize("method", ["get_person", "get_organization", "get_contact_person"])
def test_404_is_none(method):
    assert getattr(_directory(lambda request: httpx.Response(404)), method)(uuid4()) is None


@pytest.mark.parametrize("method", ["get_person", "get_organization", "get_contact_person"])
def test_403_is_access_denied_not_unavailable(method):
    with pytest.raises(PartyIdentityAccessDeniedError):
        getattr(_directory(lambda request: httpx.Response(403)), method)(uuid4())


@pytest.mark.parametrize("method", ["get_person", "get_organization", "get_contact_person"])
@pytest.mark.parametrize(
    "response",
    [httpx.Response(401), httpx.Response(500), httpx.Response(200, text="x"), httpx.Response(200, json={})],
)
def test_unavailable(method, response):
    with pytest.raises(DependencyUnavailableError) as error:
        getattr(_directory(lambda request: response), method)(uuid4())
    assert error.value.provider == "party-identity"


def test_network_error():
    def handler(request):
        raise httpx.ReadTimeout("x")

    with pytest.raises(DependencyUnavailableError):
        _directory(handler).get_person(uuid4())


def test_contact_person_fields_and_url():
    contact, organization = uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/organization-contact-persons/{contact}"
        return httpx.Response(
            200,
            json={
                "id": str(contact),
                "organization_identity_id": str(organization),
                "is_active": False,
                "email": "no-se-copia@x.co",
            },
        )

    ref = _directory(handler).get_contact_person(contact)
    assert ref.organization_identity_id == organization
    assert ref.is_active is False


# ---------------------------------------------------------------------------
# Razón social para el resumen de empresas (FR-046): dato de presentación
# ---------------------------------------------------------------------------


def test_organization_name_with_user_token():
    organization = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/organization-identities/{organization}"
        assert request.headers["authorization"] == TOKEN
        return httpx.Response(200, json={"id": str(organization), "status": "ACTIVE", "legal_name": "EMPRESA S.A.S."})

    assert _directory(handler).find_organization_name(organization) == "EMPRESA S.A.S."


@pytest.mark.parametrize("status", [403, 404])
def test_organization_name_hidden_is_none(status):
    assert _directory(lambda request: httpx.Response(status)).find_organization_name(uuid4()) is None


@pytest.mark.parametrize(
    "response",
    [httpx.Response(401), httpx.Response(502), httpx.Response(200, json={"status": "ACTIVE"}), httpx.Response(200, text="x")],
)
def test_organization_name_unavailable(response):
    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: response).find_organization_name(uuid4())
    assert error.value.provider == "party-identity"
