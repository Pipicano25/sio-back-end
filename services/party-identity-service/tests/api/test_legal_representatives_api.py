"""Representantes legales (T070; FR-070–FR-078, DS-06, DS-08, DS-13)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import random_uuid
from tests.phase_b import code, create_organization, create_person, deactivate

ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def organization(api):
    return create_organization(api)


def _url(organization) -> str:
    return f"/api/v1/organization-identities/{organization['id']}/legal-representatives"


def _register(api, organization, person, representative_type="PRIMARY", **body):
    return api.post(
        _url(organization),
        json={"person_identity_id": person["id"], "representative_type": representative_type, **body},
    )


def test_register_primary_derives_is_primary(api, organization) -> None:
    response = _register(api, organization, create_person(api), position="Gerente")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["representative_type"] == "PRIMARY" and body["is_primary"] is True
    assert body["is_active"] is True and body["valid_to"] is None


def test_second_primary_is_conflict(api, organization) -> None:
    _register(api, organization, create_person(api))

    response = _register(api, organization, create_person(api, number="1000000002"))

    assert response.status_code == 409
    assert code(response) == "PRIMARY_REPRESENTATIVE_CONFLICT"


@pytest.mark.parametrize("representative_type, is_primary", [("ALTERNATE", True), ("PRIMARY", False)])
def test_contradictory_is_primary_is_rejected(api, organization, representative_type, is_primary) -> None:
    response = _register(api, organization, create_person(api), representative_type, is_primary=is_primary)

    assert response.status_code == 422


def test_person_and_organization_must_exist_and_be_active(api, organization) -> None:
    missing = api.post(_url(organization), json={"person_identity_id": random_uuid(), "representative_type": "OTHER"})
    assert missing.status_code == 422 and code(missing) == "PERSON_IDENTITY_NOT_FOUND"

    inactive_person = deactivate(api, "person", create_person(api))
    response = _register(api, organization, inactive_person, "OTHER")
    assert response.status_code == 422 and code(response) == "PERSON_IDENTITY_INACTIVE"

    person = create_person(api, number="1000000003")
    deactivate(api, "organization", organization)
    blocked = _register(api, organization, person, "OTHER")
    assert blocked.status_code == 422 and code(blocked) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_same_person_cannot_have_two_active_relations(api, organization) -> None:
    person = create_person(api)
    _register(api, organization, person, "ALTERNATE")

    response = _register(api, organization, person, "OTHER")

    assert response.status_code == 409
    assert code(response) == "DUPLICATE_ACTIVE_REPRESENTATIVE"


def test_set_primary_replaces_current_in_one_transaction(api, organization) -> None:
    current = _register(api, organization, create_person(api)).json()
    successor = create_person(api, number="1000000002")

    response = api.post(
        f"{_url(organization)}:set-primary",
        json={"person_identity_id": successor["id"], "current_primary_version": current["version"]},
    )

    assert response.status_code == 201, response.text
    assert response.json()["person_identity_id"] == successor["id"]
    previous = api.get(f"/api/v1/organization-legal-representatives/{current['id']}").json()
    assert previous["is_active"] is False and previous["valid_to"]


def test_set_primary_establishes_first_primary(api, organization) -> None:
    response = api.post(
        f"{_url(organization)}:set-primary",
        json={"person_identity_id": create_person(api)["id"]},
    )

    assert response.status_code == 201
    assert response.json()["representative_type"] == "PRIMARY"


def test_set_primary_same_person_is_noop_and_stale_version_conflicts(api, organization) -> None:
    person = create_person(api)
    current = _register(api, organization, person).json()

    same = api.post(
        f"{_url(organization)}:set-primary",
        json={"person_identity_id": person["id"], "current_primary_version": current["version"]},
    )
    assert same.status_code == 200 and same.json()["id"] == current["id"]

    stale = api.post(
        f"{_url(organization)}:set-primary",
        json={"person_identity_id": create_person(api, number="1000000005")["id"],
              "current_primary_version": current["version"] + 1},
    )
    assert stale.status_code == 409 and code(stale) == "VERSION_CONFLICT"


def test_put_only_position_and_document_reference(api, organization) -> None:
    current = _register(api, organization, create_person(api)).json()
    url = f"/api/v1/organization-legal-representatives/{current['id']}"

    updated = api.put(url, json={"position": "Presidente", "source_document_reference": "  Acta 12 (ficticia) ",
                                  "version": current["version"]})
    assert updated.status_code == 200
    assert updated.json()["source_document_reference"] == "Acta 12 (ficticia)"

    for field, value in (("person_identity_id", random_uuid()), ("representative_type", "OTHER"),
                         ("organization_identity_id", random_uuid())):
        response = api.put(url, json={"position": "X", field: value, "version": updated.json()["version"]})
        assert response.status_code == 422 and code(response) == "IMMUTABLE_FIELD"


def test_document_reference_rules(api, organization) -> None:
    blank = _register(api, organization, create_person(api), "OTHER", source_document_reference="   ")
    assert blank.status_code == 201 and blank.json()["source_document_reference"] is None

    too_long = _register(api, organization, create_person(api, number="1000000002"), "OTHER",
                         source_document_reference="x" * 1001)
    assert too_long.status_code == 422


def test_close_and_closed_relation_is_immutable(api, organization) -> None:
    current = _register(api, organization, create_person(api)).json()
    url = f"/api/v1/organization-legal-representatives/{current['id']}"

    closed = api.post(f"{url}:close", json={"version": current["version"]})
    assert closed.status_code == 200 and closed.json()["is_active"] is False

    for response in (
        api.post(f"{url}:close", json={"version": closed.json()["version"]}),
        api.put(url, json={"position": "X", "version": closed.json()["version"]}),
    ):
        assert response.status_code == 409 and code(response) == "INVALID_STATUS_TRANSITION"
    assert api.post(f"{url}:reactivate", json={"version": closed.json()["version"]}).status_code in {404, 405}


def test_close_before_start_sets_valid_to_equal_valid_from(api, organization) -> None:
    future = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
    scheduled = _register(api, organization, create_person(api), "ALTERNATE", valid_from=future).json()

    closed = api.post(
        f"/api/v1/organization-legal-representatives/{scheduled['id']}:close", json={"version": scheduled["version"]}
    ).json()

    assert closed["valid_to"] == closed["valid_from"]


def test_multiple_alternates_and_state_filter(api, organization) -> None:
    first = _register(api, organization, create_person(api), "ALTERNATE").json()
    _register(api, organization, create_person(api, number="1000000002"), "OTHER")
    api.post(f"/api/v1/organization-legal-representatives/{first['id']}:close", json={"version": first["version"]})

    def count(**params):
        return api.get(_url(organization), params=params).json()["total_records"]

    assert (count(), count(state="active"), count(state="closed"), count(state="all")) == (1, 1, 1, 2)
    assert api.get(_url(organization), params={"state": "x"}).status_code == 422


def test_provider_fields_and_sensitive_permission(api, api_as, organization) -> None:
    _register(api, organization, create_person(api))

    reader = api_as("perm:party-identity:organization_legal_representatives:read")
    items = reader.get(_url(organization)).json()["items"]
    assert {"person_identity_id", "representative_type", "is_primary", "position", "valid_from"} <= set(items[0])

    # compras/ventas leen contactos pero no representantes (Q-C1).
    purchaser = api_as(
        "perm:party-identity:organization_identities:read",
        "perm:party-identity:organization_contact_persons:read",
        "perm:party-identity:organization_contact_profiles:read",
    )
    assert purchaser.get(_url(organization)).status_code == 403


OPERATIONS = [
    ("GET", f"/api/v1/organization-identities/{ID}/legal-representatives", None, "read"),
    ("POST", f"/api/v1/organization-identities/{ID}/legal-representatives", {}, "create"),
    ("POST", f"/api/v1/organization-identities/{ID}/legal-representatives:set-primary", {}, "create"),
    ("GET", f"/api/v1/organization-legal-representatives/{ID}", None, "read"),
    ("PUT", f"/api/v1/organization-legal-representatives/{ID}", {}, "update"),
    ("POST", f"/api/v1/organization-legal-representatives/{ID}:close", {"version": 1}, "delete"),
]


@pytest.mark.parametrize(("method", "path", "body", "action"), OPERATIONS)
def test_authorization_per_route(anonymous, api_as, method, path, body, action) -> None:
    resource = "organization_legal_representatives"
    assert anonymous.request(method, path, json=body).status_code == 401
    others = [f"perm:party-identity:{resource}:{other}" for other in ("read", "create", "update", "delete") if other != action]
    assert api_as(*others).request(method, path, json=body).status_code == 403
    assert api_as(f"perm:party-identity:{resource}:{action}").request(method, path, json=body).status_code not in {401, 403}
