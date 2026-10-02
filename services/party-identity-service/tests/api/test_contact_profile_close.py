"""Cierre explícito de perfiles (T041; DS-03, FR-020, RC-08, RC-12)."""

from __future__ import annotations

import pytest

from tests.conftest import random_uuid
from tests.phase_b import code, create_organization, create_person, profile_payload, profile_url

KINDS = ["person", "organization"]


def _identity(api, kind: str):
    return create_person(api) if kind == "person" else create_organization(api)


@pytest.mark.parametrize("kind", KINDS)
def test_close_current_then_repeat_then_never_existed(api, kind) -> None:
    identity = _identity(api, kind)
    url = profile_url(kind, identity["id"])
    current = api.post(url, json=profile_payload()).json()

    # (1) cerrar el perfil vigente
    closed = api.post(f"{url}:close", json={"version": current["version"]})
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["id"] == current["id"] and body["is_active"] is False and body["valid_to"]
    history = api.get(f"{url}/versions").json()
    assert history["total_records"] == 1

    # sin perfil vigente tras el cierre
    after = api.get(url)
    assert after.status_code == 404 and code(after) == "CONTACT_PROFILE_NOT_FOUND"

    # (2) repetir el cierre
    again = api.post(f"{url}:close", json={"version": body["version"]})
    assert again.status_code == 409
    assert code(again) == "CONTACT_PROFILE_ALREADY_CLOSED"

    # (3) identidad que nunca tuvo perfil
    other = (
        create_organization(api, number="900000077-7")
        if kind == "organization"
        else create_person(api, number="1000000077")
    )
    never = api.post(f"{profile_url(kind, other['id'])}:close", json={"version": 1})
    assert never.status_code == 404
    assert code(never) == "CONTACT_PROFILE_NOT_FOUND"


def test_close_unknown_identity_is_not_found(api) -> None:
    response = api.post(f"{profile_url('organization', random_uuid())}:close", json={"version": 1})

    assert response.status_code == 404
    assert code(response) == "NOT_FOUND"


def test_close_with_stale_version_is_conflict(api) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    current = api.post(url, json=profile_payload()).json()

    response = api.post(f"{url}:close", json={"version": current["version"] + 1})

    assert response.status_code == 409
    assert code(response) == "VERSION_CONFLICT"


def test_put_and_delete_do_not_exist_for_profiles(api) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    current = api.post(url, json=profile_payload()).json()

    assert api.put(url, json=profile_payload(version=current["version"])).status_code == 405
    assert api.delete(url).status_code == 405
    assert api.delete(f"/api/v1/organization-contact-profiles/{current['id']}").status_code == 405
