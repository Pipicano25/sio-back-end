"""Actualización semánticamente idéntica (T039; DS-04, FR-018)."""

from __future__ import annotations

from tests.conftest import random_uuid
from tests.phase_b import code, create_organization, profile_payload, profile_url


def test_identical_request_is_noop_without_dependencies(api, fake_locations, fake_membership) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()
    fake_locations.calls.clear()
    fake_membership.calls.clear()

    response = api.post(
        url,
        json=profile_payload(email="  CONTACTO@Ejemplo-Ficticio.CO ", version=first["version"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == first["id"]
    assert body["version"] == first["version"]
    assert body["updated_at"] == first["updated_at"]
    assert body["updated_by"] == first["updated_by"]
    assert fake_locations.calls == [] and fake_membership.calls == []
    assert api.get(f"{url}/versions").json()["total_records"] == 1


def test_identical_request_with_stale_version_is_conflict_first(api) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()

    response = api.post(url, json=profile_payload(version=first["version"] + 3))

    assert response.status_code == 409
    assert code(response) == "VERSION_CONFLICT"


def test_same_data_from_another_company_creates_new_version(api) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    first = api.post(url, json=profile_payload()).json()

    response = api.post(
        url,
        json=profile_payload(confirmed_by_company_id=random_uuid(), version=first["version"]),
    )

    assert response.status_code == 201
    assert response.json()["id"] != first["id"]
