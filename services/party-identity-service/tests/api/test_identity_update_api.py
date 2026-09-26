"""Pruebas de API de modificación con concurrencia (RC-06, RC-10, FR-025–FR-029, FR-033–FR-034)."""

import pytest

from tests.conftest import COLOMBIA_ID, organization_payload, person_payload, random_uuid

RESOURCES = {
    "person-identities": {
        "payload": person_payload,
        "rename": {"first_name": "RENOMBRADA"},
        "country_field": "identification_country_id",
        "number_field": "identification_number",
        "second_number": "1000000099",
    },
    "organization-identities": {
        "payload": organization_payload,
        "rename": {"legal_name": "RENOMBRADA S.A.S."},
        "country_field": "country_id",
        "number_field": "identification_number",
        "second_number": "900000099-9",
    },
}


def _create(api, resource: str, **overrides) -> dict:
    response = api.post(f"/api/v1/{resource}", json=RESOURCES[resource]["payload"](**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def _put(client, resource: str, entity_id: str, version: int, **overrides):
    body = {**RESOURCES[resource]["payload"](**overrides), "version": version}
    if resource == "person-identities":
        body.setdefault("verification_status", "UNVERIFIED")
    return client.put(f"/api/v1/{resource}/{entity_id}", json=body)


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


@pytest.mark.parametrize("resource", RESOURCES)
def test_put_with_current_version_updates_audit(api, api_as, resource) -> None:
    created = _create(api, resource)
    editor = api_as(f"perm:party-identity:{resource.replace('-', '_')}:update", sub="editor-2")

    response = _put(editor, resource, created["id"], 1, **RESOURCES[resource]["rename"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2
    assert body["updated_by"] == "editor-2"
    assert body["created_by"] == created["created_by"]


@pytest.mark.parametrize("resource", RESOURCES)
def test_put_with_stale_version_is_409_without_changes(api, resource) -> None:
    created = _create(api, resource)
    assert _put(api, resource, created["id"], 1, **RESOURCES[resource]["rename"]).status_code == 200

    response = _put(api, resource, created["id"], 1)

    assert response.status_code == 409
    assert _code(response) == "VERSION_CONFLICT"
    assert api.get(f"/api/v1/{resource}/{created['id']}").json()["version"] == 2


@pytest.mark.parametrize("resource", RESOURCES)
def test_put_to_existing_identification_is_409(api, resource) -> None:
    config = RESOURCES[resource]
    _create(api, resource, **{config["number_field"]: config["second_number"]})
    created = _create(api, resource)

    response = _put(api, resource, created["id"], 1, **{config["number_field"]: config["second_number"]})

    assert response.status_code == 409
    assert _code(response) == "DUPLICATE_IDENTIFICATION"


@pytest.mark.parametrize("resource", RESOURCES)
def test_geography_down_does_not_block_changes_without_identification(api, fake_countries, resource) -> None:
    created = _create(api, resource)
    fake_countries.mode = "unavailable"

    response = _put(api, resource, created["id"], 1, **RESOURCES[resource]["rename"])

    assert response.status_code == 200


@pytest.mark.parametrize("resource", RESOURCES)
def test_geography_down_blocks_country_change(api, fake_countries, resource) -> None:
    created = _create(api, resource)
    other = random_uuid()
    fake_countries.mode = "unavailable"

    response = _put(api, resource, created["id"], 1, **{RESOURCES[resource]["country_field"]: other})

    assert response.status_code == 503


@pytest.mark.parametrize("resource", RESOURCES)
def test_put_on_missing_identity_is_404(api, resource) -> None:
    response = _put(api, resource, random_uuid(), 1)

    assert response.status_code == 404


@pytest.mark.parametrize("resource", RESOURCES)
def test_identical_put_does_not_change_version_or_audit(api, api_as, fake_countries, resource) -> None:
    created = _create(api, resource)
    fake_countries.calls.clear()
    other_user = api_as(f"perm:party-identity:{resource.replace('-', '_')}:update", sub="otro-usuario")
    number = RESOURCES[resource]["payload"]()[RESOURCES[resource]["number_field"]]

    response = _put(
        other_user,
        resource,
        created["id"],
        1,
        identification_type=f" {RESOURCES[resource]['payload']()['identification_type'].lower()} ",
        **{RESOURCES[resource]["number_field"]: f" {number} "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert body["updated_at"] == created["updated_at"]
    assert body["updated_by"] == created["updated_by"]
    assert fake_countries.calls == []


@pytest.mark.parametrize("resource", RESOURCES)
def test_identical_put_with_stale_version_is_409(api, resource) -> None:
    created = _create(api, resource)
    assert _put(api, resource, created["id"], 1, **RESOURCES[resource]["rename"]).status_code == 200

    response = _put(api, resource, created["id"], 1, **RESOURCES[resource]["rename"])

    assert response.status_code == 409


@pytest.mark.parametrize("resource", RESOURCES)
def test_put_cannot_set_status_or_audit(api, resource) -> None:
    created = _create(api, resource)
    body = {**RESOURCES[resource]["payload"](), "version": 1, "status": "INACTIVE"}
    if resource == "person-identities":
        body["verification_status"] = "UNVERIFIED"

    response = api.put(f"/api/v1/{resource}/{created['id']}", json=body)

    assert response.status_code == 422


def test_country_field_is_used(api) -> None:
    """Sanidad del fixture: el país por defecto es el que conoce el doble."""
    assert _create(api, "person-identities")["identification_country_id"] == str(COLOMBIA_ID)
