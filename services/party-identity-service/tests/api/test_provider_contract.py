"""Contrato Provider de consulta por UUID (RC-07, FR-050–FR-052).

Fija lo que los consumidores (Product Catalog, Operational Context,
Commercial Relationship) pueden esperar de `contracts/identity-lookup-provider.md`.
"""

import pytest
from sqlalchemy import text

from tests.conftest import organization_payload, person_payload, random_uuid

RESOURCES = {
    "organization-identities": {
        "table": "organization_identities",
        "permission": "perm:party-identity:organization_identities:read",
        "payload": organization_payload,
        "fields": {"id", "status", "version", "legal_name", "country_id"},
    },
    "person-identities": {
        "table": "person_identities",
        "permission": "perm:party-identity:person_identities:read",
        "payload": person_payload,
        "fields": {"id", "status", "version", "first_name", "last_name", "identification_country_id"},
    },
}


def _create(api, resource: str) -> dict:
    response = api.post(f"/api/v1/{resource}", json=RESOURCES[resource]["payload"]())
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("resource", RESOURCES)
def test_existing_active_identity_returns_200_with_guaranteed_fields(api, api_as, resource) -> None:
    created = _create(api, resource)
    reader = api_as(RESOURCES[resource]["permission"])

    response = reader.get(f"/api/v1/{resource}/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert RESOURCES[resource]["fields"].issubset(body)
    assert body["status"] == "ACTIVE"


@pytest.mark.parametrize("resource", RESOURCES)
def test_inactive_identity_is_still_returned_by_uuid(api, test_engine, resource) -> None:
    created = _create(api, resource)

    with test_engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {RESOURCES[resource]['table']} SET status = 'INACTIVE' WHERE id = :id"),
            {"id": created["id"]},
        )

    response = api.get(f"/api/v1/{resource}/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


@pytest.mark.parametrize("resource", RESOURCES)
def test_unknown_uuid_is_404_problem(api, resource) -> None:
    response = api.get(f"/api/v1/{resource}/{random_uuid()}")

    assert response.status_code == 404
    assert response.json()["code"] == "PARTY_IDENTITY.NOT_FOUND"


@pytest.mark.parametrize("resource", RESOURCES)
def test_malformed_uuid_is_422(api, resource) -> None:
    response = api.get(f"/api/v1/{resource}/12345")

    assert response.status_code == 422
    assert response.json()["code"] == "PARTY_IDENTITY.VALIDATION_ERROR"


@pytest.mark.parametrize("resource", RESOURCES)
def test_without_token_is_401(anonymous, resource) -> None:
    assert anonymous.get(f"/api/v1/{resource}/{random_uuid()}").status_code == 401


@pytest.mark.parametrize("resource", RESOURCES)
def test_without_read_permission_is_403(api_as, resource) -> None:
    other = "perm:party-identity:person_identities:read" if resource == "organization-identities" else "perm:party-identity:organization_identities:read"

    assert api_as(other).get(f"/api/v1/{resource}/{random_uuid()}").status_code == 403


@pytest.mark.parametrize("resource", RESOURCES)
def test_wildcard_read_permissions_are_accepted(api, api_as, resource) -> None:
    """Los grupos del realm usan comodines (`all:read`, `perm:all:all:read`)."""
    created = _create(api, resource)

    for permission in ("perm:party-identity:all:read", "perm:all:all:read"):
        assert api_as(permission).get(f"/api/v1/{resource}/{created['id']}").status_code == 200
