"""Perfil de contacto de organización (T038; FR-010–FR-022, FR-026, RC-02, RC-06)."""

from __future__ import annotations

import pytest

from tests.conftest import COMPANY_ID, random_uuid
from tests.phase_b import code, create_organization, deactivate, profile_payload, profile_url


@pytest.fixture
def organization(api):
    return create_organization(api)


def test_first_version_is_created_with_confirmation_context(api, organization, fake_membership) -> None:
    response = api.post(profile_url("organization", organization["id"]), json=profile_payload())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["organization_identity_id"] == organization["id"]
    assert body["is_active"] is True and body["valid_to"] is None
    assert body["confirmed_by_company_id"] == str(COMPANY_ID)
    assert body["confirmed_by_user_id"] == str(
        fake_membership.application_user_id(COMPANY_ID, "user-admin")
    )
    assert fake_membership.calls == [(COMPANY_ID, "user-admin")]
    assert body["created_by"] == "user-admin"
    assert body["email"] == "contacto@ejemplo-ficticio.co"


def test_replacement_closes_current_and_creates_new_with_same_instant(api, organization) -> None:
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()

    second = api.post(url, json=profile_payload(phone="+57 300 000 0000", version=first["version"]))

    assert second.status_code == 201, second.text
    new = second.json()
    old = api.get(f"/api/v1/organization-contact-profiles/{first['id']}").json()
    assert old["is_active"] is False and old["valid_to"] == new["valid_from"]
    assert api.get(url).json()["id"] == new["id"]


def test_get_current_history_and_version(api, organization) -> None:
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()
    second = api.post(url, json=profile_payload(email="otro@ejemplo-ficticio.co", version=first["version"])).json()

    history = api.get(f"{url}/versions").json()
    assert [item["id"] for item in history["items"]] == [second["id"], first["id"]]
    assert history["total_records"] == 2
    assert api.get(f"/api/v1/organization-contact-profiles/{first['id']}").status_code == 200


def test_without_current_version_is_contact_profile_not_found(api, organization) -> None:
    response = api.get(profile_url("organization", organization["id"]))

    assert response.status_code == 404
    assert code(response) == "CONTACT_PROFILE_NOT_FOUND"


def test_unknown_organization_is_not_found(api) -> None:
    response = api.post(profile_url("organization", random_uuid()), json=profile_payload())

    assert response.status_code == 404
    assert code(response) == "NOT_FOUND"
    assert api.get(profile_url("organization", random_uuid())).json()["code"] == "PARTY_IDENTITY.NOT_FOUND"


def test_inactive_organization_is_rejected(api, organization) -> None:
    deactivate(api, "organization", organization)

    response = api.post(profile_url("organization", organization["id"]), json=profile_payload())

    assert response.status_code == 422
    assert code(response) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_profile_without_email_phone_or_address_is_rejected(api, organization, fake_membership) -> None:
    response = api.post(
        profile_url("organization", organization["id"]),
        json=profile_payload(email=None, phone="  ", address_line=None),
    )

    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"
    assert fake_membership.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "no-es-correo"},
        {"email": "a" * 250 + "@x.co"},
        {"phone": "300-ABC"},
        {"phone": "1" * 41},
        {"postal_code": "1" * 21},
    ],
)
def test_invalid_formats_and_lengths(api, organization, overrides) -> None:
    response = api.post(profile_url("organization", organization["id"]), json=profile_payload(**overrides))

    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"


def test_body_with_confirmed_by_user_id_is_rejected(api, organization, fake_membership) -> None:
    response = api.post(
        profile_url("organization", organization["id"]),
        json=profile_payload(confirmed_by_user_id=random_uuid()),
    )

    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"
    assert fake_membership.calls == []


def test_missing_version_with_current_profile_is_conflict(api, organization) -> None:
    """Sin versión el cliente cree que no hay vigente: vista desactualizada (spec, casos límite)."""
    url = profile_url("organization", organization["id"])
    api.post(url, json=profile_payload())

    response = api.post(url, json=profile_payload(phone="+57 300 000 0001"))

    assert response.status_code == 409
    assert code(response) == "VERSION_CONFLICT"


def test_version_grows_monotonically_per_owner(api, organization) -> None:
    """Una versión nueva nunca reutiliza un número ya visto (detecta vistas desactualizadas)."""
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()
    second = api.post(url, json=profile_payload(phone="+57 300 000 0002", version=first["version"])).json()

    assert second["version"] > first["version"]
    stale = api.post(url, json=profile_payload(phone="+57 300 000 0003", version=first["version"]))
    assert stale.status_code == 409


def test_stale_version_is_conflict(api, organization) -> None:
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()

    response = api.post(url, json=profile_payload(phone="+57 300 000 0001", version=first["version"] + 1))

    assert response.status_code == 409
    assert code(response) == "VERSION_CONFLICT"
