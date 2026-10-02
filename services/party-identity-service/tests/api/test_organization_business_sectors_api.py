"""Sectores de una organización (T059; FR-060–FR-065, DS-07, DS-08, DS-12, R-05a)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.phase_b import code, create_organization, deactivate

ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def organization(api):
    return create_organization(api)


def _sector(api, code_value: str) -> dict:
    response = api.post(
        "/api/v1/global-business-sectors",
        json={"classification_system": "TEST", "code": code_value, "name": f"Sector {code_value}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign(api, organization, sector, **body):
    return api.post(
        f"/api/v1/organization-identities/{organization['id']}/business-sectors",
        json={"global_business_sector_id": sector["id"], **body},
    )


def test_assign_sector(api, organization) -> None:
    response = _assign(api, organization, _sector(api, "01"), is_primary=True)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_primary"] is True and body["is_active"] is True and body["valid_to"] is None


def test_inactive_organization_or_sector_is_rejected(api, organization) -> None:
    sector = _sector(api, "01")
    inactive_sector = _sector(api, "02")
    api.post(
        f"/api/v1/global-business-sectors/{inactive_sector['id']}:deactivate",
        json={"version": inactive_sector["version"]},
    )

    sector_response = _assign(api, organization, inactive_sector)
    assert sector_response.status_code == 422 and code(sector_response) == "SECTOR_INACTIVE"

    deactivate(api, "organization", organization)
    organization_response = _assign(api, organization, sector)
    assert organization_response.status_code == 422
    assert code(organization_response) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_duplicate_active_assignment_is_conflict(api, organization) -> None:
    sector = _sector(api, "01")
    _assign(api, organization, sector)

    response = _assign(api, organization, sector)

    assert response.status_code == 409
    assert code(response) == "DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT"


def test_second_primary_on_create_is_conflict(api, organization) -> None:
    _assign(api, organization, _sector(api, "01"), is_primary=True)

    response = _assign(api, organization, _sector(api, "02"), is_primary=True)

    assert response.status_code == 409
    assert code(response) == "PRIMARY_SECTOR_CONFLICT"


def test_set_primary_switches_and_closed_assignment_is_invalid(api, organization) -> None:
    first = _assign(api, organization, _sector(api, "01"), is_primary=True).json()
    second = _assign(api, organization, _sector(api, "02")).json()

    switched = api.post(
        f"/api/v1/organization-business-sectors/{second['id']}:set-primary", json={"version": second["version"]}
    )
    assert switched.status_code == 200 and switched.json()["is_primary"] is True
    assert api.get(f"/api/v1/organization-business-sectors/{first['id']}").json()["is_primary"] is False

    closed = api.post(
        f"/api/v1/organization-business-sectors/{first['id']}:close",
        json={"version": api.get(f"/api/v1/organization-business-sectors/{first['id']}").json()["version"]},
    ).json()
    invalid = api.post(
        f"/api/v1/organization-business-sectors/{first['id']}:set-primary", json={"version": closed["version"]}
    )
    assert invalid.status_code == 422 and code(invalid) == "INVALID_PRIMARY_SECTOR"


def test_close_sets_valid_to_and_is_immutable_without_reactivation(api, organization) -> None:
    primary = _assign(api, organization, _sector(api, "01"), is_primary=True).json()

    closed = api.post(f"/api/v1/organization-business-sectors/{primary['id']}:close", json={"version": primary["version"]})
    assert closed.status_code == 200
    body = closed.json()
    assert body["is_active"] is False and body["valid_to"] and body["is_primary"] is False

    again = api.post(f"/api/v1/organization-business-sectors/{primary['id']}:close", json={"version": body["version"]})
    assert again.status_code == 409 and code(again) == "INVALID_STATUS_TRANSITION"
    assert api.post(f"/api/v1/organization-business-sectors/{primary['id']}:reactivate",
                    json={"version": body["version"]}).status_code in {404, 405}

    # La organización queda sin principal; la relación vuelve a existir como fila nueva.
    renewed = _assign(api, organization, {"id": primary["global_business_sector_id"]}, is_primary=True)
    assert renewed.status_code == 201 and renewed.json()["id"] != primary["id"]


def test_closing_before_start_sets_valid_to_equal_valid_from(api, organization) -> None:
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    scheduled = _assign(api, organization, _sector(api, "01"), valid_from=future).json()

    closed = api.post(
        f"/api/v1/organization-business-sectors/{scheduled['id']}:close", json={"version": scheduled["version"]}
    ).json()

    assert closed["valid_to"] == closed["valid_from"]


def test_list_by_state(api, organization) -> None:
    active = _assign(api, organization, _sector(api, "01")).json()
    other = _assign(api, organization, _sector(api, "02")).json()
    api.post(f"/api/v1/organization-business-sectors/{other['id']}:close", json={"version": other["version"]})
    url = f"/api/v1/organization-identities/{organization['id']}/business-sectors"

    def ids(**params):
        return {item["id"] for item in api.get(url, params=params).json()["items"]}

    assert ids() == {active["id"]}
    assert ids(state="active") == {active["id"]}
    assert ids(state="closed") == {other["id"]}
    assert ids(state="all") == {active["id"], other["id"]}
    assert api.get(url, params={"state": "otro"}).status_code == 422


def test_provider_fields(api, api_as, organization) -> None:
    _assign(api, organization, _sector(api, "01"), is_primary=True)
    reader = api_as("perm:party-identity:organization_business_sectors:read")

    items = reader.get(f"/api/v1/organization-identities/{organization['id']}/business-sectors").json()["items"]

    assert {"global_business_sector_id", "is_primary", "valid_from"} <= set(items[0])


OPERATIONS = [
    ("GET", f"/api/v1/organization-identities/{ID}/business-sectors", None, "read"),
    ("POST", f"/api/v1/organization-identities/{ID}/business-sectors", {}, "create"),
    ("GET", f"/api/v1/organization-business-sectors/{ID}", None, "read"),
    ("POST", f"/api/v1/organization-business-sectors/{ID}:set-primary", {"version": 1}, "update"),
    ("POST", f"/api/v1/organization-business-sectors/{ID}:close", {"version": 1}, "delete"),
]


@pytest.mark.parametrize(("method", "path", "body", "action"), OPERATIONS)
def test_authorization_per_route(anonymous, api_as, method, path, body, action) -> None:
    resource = "organization_business_sectors"
    assert anonymous.request(method, path, json=body).status_code == 401
    others = [f"perm:party-identity:{resource}:{other}" for other in ("read", "create", "update", "delete") if other != action]
    assert api_as(*others).request(method, path, json=body).status_code == 403
    assert api_as(f"perm:party-identity:{resource}:{action}").request(method, path, json=body).status_code not in {401, 403}
