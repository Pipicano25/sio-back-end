"""Perfil de contacto de persona (T050; FR-016, RC-14, DS-07, RN-12)."""

from __future__ import annotations

from tests.conftest import COMPANY_ID
from tests.phase_b import code, create_person, deactivate, profile_payload, profile_url


def test_person_profile_create_replace_noop_close_history(api, fake_membership) -> None:
    person = create_person(api)
    url = profile_url("person", person["id"])

    first = api.post(url, json=profile_payload(email=None, address_line=None, country_id=None,
                                                administrative_division_id=None, city_id=None))
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["person_identity_id"] == person["id"]
    assert body["phone"] == "+57 601 555 0100"
    assert body["confirmed_by_user_id"] == str(fake_membership.application_user_id(COMPANY_ID, "user-admin"))

    same = api.post(url, json=profile_payload(email=None, address_line=None, country_id=None,
                                               administrative_division_id=None, city_id=None,
                                               version=body["version"]))
    assert same.status_code == 200

    replaced = api.post(url, json=profile_payload(version=body["version"]))
    assert replaced.status_code == 201

    closed = api.post(f"{url}:close", json={"version": replaced.json()["version"]})
    assert closed.status_code == 200
    assert api.get(f"{url}/versions").json()["total_records"] == 2


def test_inactive_person_rejects_new_versions_but_keeps_history(api) -> None:
    person = create_person(api)
    url = profile_url("person", person["id"])
    current = api.post(url, json=profile_payload()).json()
    person = api.get(f"/api/v1/person-identities/{person['id']}").json()

    deactivate(api, "person", person)

    rejected = api.post(url, json=profile_payload(phone="+57 300 000 0009", version=current["version"]))
    assert rejected.status_code == 422
    assert code(rejected) == "PERSON_IDENTITY_INACTIVE"
    # Sin cascada: el perfil vigente sigue consultable y su historia se conserva.
    assert api.get(url).json()["id"] == current["id"]
    assert api.get(f"{url}/versions").json()["total_records"] == 1


def test_person_identity_read_does_not_grant_profile(api, api_as) -> None:
    person = create_person(api)

    response = api_as("perm:party-identity:person_identities:read").get(profile_url("person", person["id"]))

    assert response.status_code == 403
