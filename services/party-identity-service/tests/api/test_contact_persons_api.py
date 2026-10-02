"""Personas de contacto de una organización (T052; FR-040–FR-047, DS-05, DS-07, RC-04)."""

from __future__ import annotations

import pytest

from tests.conftest import random_uuid
from tests.phase_b import code, create_organization, create_person, deactivate

ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def organization(api):
    return create_organization(api)


def _url(organization) -> str:
    return f"/api/v1/organization-identities/{organization['id']}/contact-persons"


def _create(api, organization, **body):
    payload = {"position": "Compras", "phone": "+57 601 555 0101", **body}
    return api.post(_url(organization), json=payload)


def test_create_is_active_and_not_primary_by_default(api, organization) -> None:
    response = _create(api, organization)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_active"] is True and body["is_primary"] is False
    assert body["organization_identity_id"] == organization["id"]


def test_contact_without_email_phone_or_person_is_rejected(api, organization) -> None:
    response = api.post(_url(organization), json={"position": "Cartera"})

    assert response.status_code == 422
    assert code(response) == "VALIDATION_ERROR"


def test_linked_person_must_exist_and_be_active(api, organization) -> None:
    missing = _create(api, organization, person_identity_id=random_uuid())
    assert missing.status_code == 422 and code(missing) == "PERSON_IDENTITY_NOT_FOUND"

    person = deactivate(api, "person", create_person(api))
    inactive = _create(api, organization, person_identity_id=person["id"])
    assert inactive.status_code == 422 and code(inactive) == "PERSON_IDENTITY_INACTIVE"


def test_inactive_organization_is_rejected(api, organization) -> None:
    deactivate(api, "organization", organization)

    response = _create(api, organization)

    assert response.status_code == 422
    assert code(response) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_same_person_cannot_be_active_contact_twice(api, organization) -> None:
    person = create_person(api)
    assert _create(api, organization, person_identity_id=person["id"]).status_code == 201

    response = _create(api, organization, person_identity_id=person["id"])

    assert response.status_code == 409
    assert code(response) == "DUPLICATE_ACTIVE_CONTACT_PERSON"


def test_creating_second_primary_is_conflict(api, organization) -> None:
    assert _create(api, organization, is_primary=True).status_code == 201

    response = _create(api, organization, is_primary=True, phone="+57 601 555 0102")

    assert response.status_code == 409
    assert code(response) == "PRIMARY_CONTACT_CONFLICT"


@pytest.mark.parametrize("field, value", [("is_primary", True), ("organization_identity_id", random_uuid())])
def test_put_cannot_change_primary_or_organization(api, organization, field, value) -> None:
    contact = _create(api, organization).json()

    response = api.put(
        f"/api/v1/organization-contact-persons/{contact['id']}",
        json={"position": "Compras", "phone": "+57 601 555 0101", field: value, "version": contact["version"]},
    )

    assert response.status_code == 422
    assert code(response) == "IMMUTABLE_FIELD"


def test_put_updates_and_identical_put_is_noop(api, organization) -> None:
    contact = _create(api, organization).json()
    url = f"/api/v1/organization-contact-persons/{contact['id']}"

    updated = api.put(url, json={"position": "Logística", "phone": "+57 601 555 0101", "version": contact["version"]})
    assert updated.status_code == 200
    assert updated.json()["position"] == "Logística" and updated.json()["version"] == contact["version"] + 1

    same = api.put(url, json={"position": "Logística", "phone": "+57 601 555 0101", "version": updated.json()["version"]})
    assert same.status_code == 200 and same.json()["version"] == updated.json()["version"]


def test_set_primary_switches_in_one_operation(api, organization) -> None:
    first = _create(api, organization, is_primary=True).json()
    second = _create(api, organization, phone="+57 601 555 0102").json()

    response = api.post(
        f"/api/v1/organization-contact-persons/{second['id']}:set-primary",
        json={"version": second["version"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_primary"] is True
    previous = api.get(f"/api/v1/organization-contact-persons/{first['id']}").json()
    assert previous["is_primary"] is False and previous["version"] == first["version"] + 1


def test_set_primary_on_current_primary_is_noop(api, organization) -> None:
    primary = _create(api, organization, is_primary=True).json()

    response = api.post(
        f"/api/v1/organization-contact-persons/{primary['id']}:set-primary",
        json={"version": primary["version"]},
    )

    assert response.status_code == 200
    assert response.json()["version"] == primary["version"]


def test_set_primary_on_inactive_contact_is_rejected(api, organization) -> None:
    contact = _create(api, organization).json()
    inactive = api.post(
        f"/api/v1/organization-contact-persons/{contact['id']}:deactivate",
        json={"version": contact["version"]},
    ).json()

    response = api.post(
        f"/api/v1/organization-contact-persons/{contact['id']}:set-primary",
        json={"version": inactive["version"]},
    )

    assert response.status_code == 422
    assert code(response) == "INVALID_PRIMARY_CONTACT"


def test_deactivate_removes_primary_only_from_itself(api, organization) -> None:
    primary = _create(api, organization, is_primary=True).json()
    other = _create(api, organization, phone="+57 601 555 0102").json()

    response = api.post(
        f"/api/v1/organization-contact-persons/{primary['id']}:deactivate",
        json={"version": primary["version"]},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False and response.json()["is_primary"] is False
    untouched = api.get(f"/api/v1/organization-contact-persons/{other['id']}").json()
    assert untouched["version"] == other["version"] and untouched["is_primary"] is False


def test_invalid_transitions_and_reactivation_rules(api, organization) -> None:
    contact = _create(api, organization).json()
    url = f"/api/v1/organization-contact-persons/{contact['id']}"

    again = api.post(f"{url}:reactivate", json={"version": contact["version"]})
    assert again.status_code == 409 and code(again) == "INVALID_STATUS_TRANSITION"

    inactive = api.post(f"{url}:deactivate", json={"version": contact["version"]}).json()
    twice = api.post(f"{url}:deactivate", json={"version": inactive["version"]})
    assert twice.status_code == 409 and code(twice) == "INVALID_STATUS_TRANSITION"

    organization = api.get(f"/api/v1/organization-identities/{organization['id']}").json()
    deactivate(api, "organization", organization)
    blocked = api.post(f"{url}:reactivate", json={"version": inactive["version"]})
    assert blocked.status_code == 422 and code(blocked) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_list_defaults_to_active_and_filters_inactive(api, organization) -> None:
    active = _create(api, organization).json()
    other = _create(api, organization, phone="+57 601 555 0102").json()
    api.post(f"/api/v1/organization-contact-persons/{other['id']}:deactivate", json={"version": other["version"]})

    default = api.get(_url(organization)).json()
    inactive = api.get(_url(organization), params={"is_active": "false"}).json()

    assert [item["id"] for item in default["items"]] == [active["id"]]
    assert [item["id"] for item in inactive["items"]] == [other["id"]]


def test_position_max_length(api, organization) -> None:
    response = _create(api, organization, position="x" * 121)

    assert response.status_code == 422


OPERATIONS = [
    ("GET", f"/api/v1/organization-identities/{ID}/contact-persons", None, "read"),
    ("POST", f"/api/v1/organization-identities/{ID}/contact-persons", {}, "create"),
    ("GET", f"/api/v1/organization-contact-persons/{ID}", None, "read"),
    ("PUT", f"/api/v1/organization-contact-persons/{ID}", {}, "update"),
    ("POST", f"/api/v1/organization-contact-persons/{ID}:set-primary", {"version": 1}, "update"),
    ("POST", f"/api/v1/organization-contact-persons/{ID}:deactivate", {"version": 1}, "delete"),
    ("POST", f"/api/v1/organization-contact-persons/{ID}:reactivate", {"version": 1}, "update"),
]
ACTIONS = ("read", "create", "update", "delete")


@pytest.mark.parametrize(("method", "path", "body", "action"), OPERATIONS)
def test_authorization_per_route(anonymous, api_as, method, path, body, action) -> None:
    resource = "organization_contact_persons"
    assert anonymous.request(method, path, json=body).status_code == 401
    others = [f"perm:party-identity:{resource}:{other}" for other in ACTIONS if other != action]
    assert api_as(*others).request(method, path, json=body).status_code == 403
    assert api_as(f"perm:party-identity:{resource}:{action}").request(method, path, json=body).status_code not in {401, 403}
