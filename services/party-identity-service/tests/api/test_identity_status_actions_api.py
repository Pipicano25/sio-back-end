"""Acciones de estado sin eliminación física (RC-09, FR-027, FR-035, DS-02, DS-11)."""

import pytest

from tests.conftest import organization_payload, person_payload, random_uuid

RESOURCES = {
    "person-identities": {"payload": person_payload, "perm": "person_identities", "other_status": "verification_status"},
    "organization-identities": {"payload": organization_payload, "perm": "organization_identities", "other_status": "registration_status"},
}


def _create(api, resource: str) -> dict:
    payload = RESOURCES[resource]["payload"]()
    if resource == "person-identities":
        payload["verification_status"] = "VERIFIED"
    else:
        payload["registration_status"] = "ACTIVA"
    response = api.post(f"/api/v1/{resource}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _action(client, resource: str, entity_id: str, action: str, version: int):
    return client.post(f"/api/v1/{resource}/{entity_id}/{action}", json={"version": version})


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


@pytest.mark.parametrize("resource", RESOURCES)
def test_deactivate_keeps_identity_and_hides_it_from_default_listing(api, api_as, resource) -> None:
    created = _create(api, resource)
    admin = api_as("perm:party-identity:all:all", sub="admin-2")

    response = _action(admin, resource, created["id"], "deactivate", 1)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert body["version"] == 2
    assert body["updated_by"] == "admin-2"
    other = RESOURCES[resource]["other_status"]
    assert body[other] == created[other]

    assert api.get(f"/api/v1/{resource}/{created['id']}").json()["status"] == "INACTIVE"
    assert api.get(f"/api/v1/{resource}").json()["total_records"] == 0
    inactive = api.get(f"/api/v1/{resource}", params={"status": "INACTIVE"}).json()
    assert [item["id"] for item in inactive["items"]] == [created["id"]]


@pytest.mark.parametrize("resource", RESOURCES)
def test_repeated_deactivate_is_409_without_version_change(api, resource) -> None:
    created = _create(api, resource)
    assert _action(api, resource, created["id"], "deactivate", 1).status_code == 200

    response = _action(api, resource, created["id"], "deactivate", 2)

    assert response.status_code == 409
    assert _code(response) == "INVALID_STATUS_TRANSITION"
    assert api.get(f"/api/v1/{resource}/{created['id']}").json()["version"] == 2


@pytest.mark.parametrize("resource", RESOURCES)
def test_reactivate_active_is_409_without_version_change(api, resource) -> None:
    created = _create(api, resource)

    response = _action(api, resource, created["id"], "reactivate", 1)

    assert response.status_code == 409
    assert _code(response) == "INVALID_STATUS_TRANSITION"
    assert api.get(f"/api/v1/{resource}/{created['id']}").json()["version"] == 1


@pytest.mark.parametrize("resource", RESOURCES)
def test_reactivate_restores_active(api, resource) -> None:
    created = _create(api, resource)
    _action(api, resource, created["id"], "deactivate", 1)

    response = _action(api, resource, created["id"], "reactivate", 2)

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["version"] == 3


@pytest.mark.parametrize("resource", RESOURCES)
def test_stale_version_is_409(api, resource) -> None:
    created = _create(api, resource)

    response = _action(api, resource, created["id"], "deactivate", 7)

    assert response.status_code == 409
    assert _code(response) == "VERSION_CONFLICT"


@pytest.mark.parametrize("resource", RESOURCES)
def test_deactivate_requires_delete_and_reactivate_requires_update(api, api_as, resource) -> None:
    """Como `supervisor.test`: con `update` reactiva, sin `delete` no inactiva."""
    created = _create(api, resource)
    perm = RESOURCES[resource]["perm"]
    updater = api_as(f"perm:party-identity:{perm}:update", f"perm:party-identity:{perm}:read")

    assert _action(updater, resource, created["id"], "deactivate", 1).status_code == 403
    assert _action(api, resource, created["id"], "deactivate", 1).status_code == 200
    assert _action(updater, resource, created["id"], "reactivate", 2).status_code == 200


@pytest.mark.parametrize("resource", RESOURCES)
def test_actions_on_missing_identity_are_404(api, resource) -> None:
    assert _action(api, resource, random_uuid(), "deactivate", 1).status_code == 404


@pytest.mark.parametrize("resource", RESOURCES)
def test_there_is_no_physical_delete(api, resource) -> None:
    created = _create(api, resource)

    response = api.delete(f"/api/v1/{resource}/{created['id']}")

    assert response.status_code == 405
    assert api.get(f"/api/v1/{resource}/{created['id']}").status_code == 200


@pytest.mark.parametrize("resource", RESOURCES)
def test_actions_do_not_call_geography(api, fake_countries, resource) -> None:
    created = _create(api, resource)
    fake_countries.calls.clear()
    fake_countries.mode = "unavailable"

    assert _action(api, resource, created["id"], "deactivate", 1).status_code == 200
    assert fake_countries.calls == []
