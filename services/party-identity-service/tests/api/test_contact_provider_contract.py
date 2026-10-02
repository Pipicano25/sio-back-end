"""Contrato Provider de contactos (T056; FR-080, FR-081, RC-10, SC-009).

Fija las respuestas de `contracts/contact-lookup-provider.md`.
"""

from __future__ import annotations

from tests.conftest import random_uuid
from tests.phase_b import create_organization, create_person, profile_payload, profile_url

GUARANTEED_CONTACT_FIELDS = {
    "id", "organization_identity_id", "person_identity_id", "is_active", "is_primary",
    "position", "email", "phone", "version",
}


def test_contact_person_lookup_returns_guaranteed_fields_in_any_state(api, api_as) -> None:
    organization = create_organization(api)
    contact = api.post(
        f"/api/v1/organization-identities/{organization['id']}/contact-persons",
        json={"phone": "+57 601 555 0101"},
    ).json()
    api.post(f"/api/v1/organization-contact-persons/{contact['id']}:deactivate", json={"version": contact["version"]})
    consumer = api_as("perm:party-identity:organization_contact_persons:read", sub="service-account-commercial")

    response = consumer.get(f"/api/v1/organization-contact-persons/{contact['id']}")

    assert response.status_code == 200
    body = response.json()
    assert GUARANTEED_CONTACT_FIELDS <= set(body)
    # SC-009: una sola consulta basta para validar pertenencia y vigencia.
    assert body["organization_identity_id"] == organization["id"]
    assert body["is_active"] is False


def test_contact_person_lookup_errors(anonymous, api_as) -> None:
    path = f"/api/v1/organization-contact-persons/{random_uuid()}"

    assert anonymous.get(path).status_code == 401
    assert api_as("perm:party-identity:organization_identities:read").get(path).status_code == 403
    missing = api_as("perm:party-identity:organization_contact_persons:read").get(path)
    assert missing.status_code == 404
    assert missing.json()["code"] == "PARTY_IDENTITY.NOT_FOUND"


def test_current_profile_lookup_distinguishes_identity_from_profile(api, api_as) -> None:
    person = create_person(api)
    organization = create_organization(api)
    api.post(profile_url("organization", organization["id"]), json=profile_payload())

    person_reader = api_as("perm:party-identity:person_contact_profiles:read")
    organization_reader = api_as("perm:party-identity:organization_contact_profiles:read")

    no_profile = person_reader.get(profile_url("person", person["id"]))
    assert no_profile.status_code == 404
    assert no_profile.json()["code"] == "PARTY_IDENTITY.CONTACT_PROFILE_NOT_FOUND"

    no_identity = person_reader.get(profile_url("person", random_uuid()))
    assert no_identity.status_code == 404
    assert no_identity.json()["code"] == "PARTY_IDENTITY.NOT_FOUND"

    current = organization_reader.get(profile_url("organization", organization["id"]))
    assert current.status_code == 200
    assert current.json()["organization_identity_id"] == organization["id"]
    assert current.json()["is_active"] is True
