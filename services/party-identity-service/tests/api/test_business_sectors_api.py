"""Catálogo de sectores económicos (T058; FR-050–FR-054, DS-09, RC-07)."""

from __future__ import annotations

import pytest

from tests.conftest import random_uuid
from tests.phase_b import code

BASE = "/api/v1/global-business-sectors"
ID = "00000000-0000-0000-0000-000000000001"


def _create(api, code_value: str, parent: str | None = None, system: str = "test_system", **extra):
    payload = {"classification_system": system, "code": code_value, "name": f"Sector {code_value}", **extra}
    if parent:
        payload["parent_sector_id"] = parent
    return api.post(BASE, json=payload)


def test_create_normalizes_system_and_code(api) -> None:
    response = _create(api, " a ")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["classification_system"] == "TEST_SYSTEM" and body["code"] == "A"
    assert body["status"] == "ACTIVE" and body["parent_sector_id"] is None


def test_duplicate_code_after_normalization_is_conflict(api) -> None:
    _create(api, "A")

    response = _create(api, " a", system="TEST_SYSTEM ")

    assert response.status_code == 409
    assert code(response) == "DUPLICATE_SECTOR_CODE"


def test_parent_must_exist_be_active_and_same_system(api) -> None:
    root = _create(api, "A").json()
    other_system = _create(api, "B", system="OTHER").json()

    assert code(_create(api, "01", parent=random_uuid())) == "INVALID_SECTOR_HIERARCHY"
    assert code(_create(api, "02", parent=other_system["id"])) == "INVALID_SECTOR_HIERARCHY"

    api.post(f"{BASE}/{root['id']}:deactivate", json={"version": root["version"]})
    response = _create(api, "03", parent=root["id"])
    assert response.status_code == 422 and code(response) == "INVALID_SECTOR_HIERARCHY"


def test_cycle_is_rejected(api) -> None:
    root = _create(api, "A").json()
    child = _create(api, "01", parent=root["id"]).json()

    response = api.put(
        f"{BASE}/{root['id']}",
        json={"name": "Raíz", "parent_sector_id": child["id"], "version": root["version"]},
    )

    assert response.status_code == 422
    assert code(response) == "INVALID_SECTOR_HIERARCHY"


@pytest.mark.parametrize("field", ["classification_system", "code"])
def test_identity_fields_are_immutable(api, field) -> None:
    sector = _create(api, "A").json()

    response = api.put(
        f"{BASE}/{sector['id']}",
        json={"name": "Otro", field: "X", "version": sector["version"]},
    )

    assert response.status_code == 422
    assert code(response) == "IMMUTABLE_FIELD"


def test_put_updates_name_description_and_parent(api) -> None:
    root = _create(api, "A").json()
    sector = _create(api, "B").json()

    response = api.put(
        f"{BASE}/{sector['id']}",
        json={"name": "Nuevo", "description": "Alcance", "parent_sector_id": root["id"], "version": sector["version"]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["parent_sector_id"] == root["id"] and response.json()["name"] == "Nuevo"


def test_cannot_deactivate_sector_with_active_children(api) -> None:
    root = _create(api, "A").json()
    child = _create(api, "01", parent=root["id"]).json()

    response = api.post(f"{BASE}/{root['id']}:deactivate", json={"version": root["version"]})

    assert response.status_code == 409
    assert code(response) == "SECTOR_HAS_ACTIVE_CHILDREN"
    assert api.get(f"{BASE}/{child['id']}").json()["status"] == "ACTIVE"

    child_off = api.post(f"{BASE}/{child['id']}:deactivate", json={"version": child["version"]})
    assert child_off.status_code == 200
    assert api.post(f"{BASE}/{root['id']}:deactivate", json={"version": root["version"]}).status_code == 200


def test_reactivate_child_requires_active_parent(api) -> None:
    root = _create(api, "A").json()
    child = _create(api, "01", parent=root["id"]).json()
    child = api.post(f"{BASE}/{child['id']}:deactivate", json={"version": child["version"]}).json()
    root = api.post(f"{BASE}/{root['id']}:deactivate", json={"version": root["version"]}).json()

    response = api.post(f"{BASE}/{child['id']}:reactivate", json={"version": child["version"]})

    assert response.status_code == 422
    assert code(response) == "INVALID_SECTOR_HIERARCHY"


def test_invalid_transitions(api) -> None:
    sector = _create(api, "A").json()

    response = api.post(f"{BASE}/{sector['id']}:reactivate", json={"version": sector["version"]})

    assert response.status_code == 409
    assert code(response) == "INVALID_STATUS_TRANSITION"


def test_filters(api) -> None:
    root = _create(api, "A").json()
    child = _create(api, "01", parent=root["id"]).json()
    _create(api, "Z", system="OTHER")
    inactive = _create(api, "B").json()
    api.post(f"{BASE}/{inactive['id']}:deactivate", json={"version": inactive["version"]})

    def codes(**params):
        return [item["code"] for item in api.get(BASE, params=params).json()["items"]]

    assert codes(classification_system="TEST_SYSTEM") == ["01", "A"]
    assert codes(classification_system="TEST_SYSTEM", level_root="true") == ["A"]
    assert codes(parent_sector_id=root["id"]) == ["01"]
    assert codes(code="01") == ["01"]
    assert codes(status="INACTIVE") == ["B"]
    assert codes(search="Sector Z") == ["Z"]
    assert api.get(BASE, params={"status": "OTRO"}).status_code == 422
    assert api.get(f"{BASE}/{child['id']}").json()["parent_sector_id"] == root["id"]


@pytest.mark.parametrize(
    "overrides",
    [{"code": "x" * 41}, {"name": "x" * 256}, {"classification_system": "x" * 31}],
)
def test_lengths(api, overrides) -> None:
    payload = {"classification_system": "T", "code": "A", "name": "n", **overrides}

    assert api.post(BASE, json=payload).status_code == 422


OPERATIONS = [
    ("GET", BASE, None, "read"),
    ("POST", BASE, {}, "create"),
    ("GET", f"{BASE}/{ID}", None, "read"),
    ("PUT", f"{BASE}/{ID}", {}, "update"),
    ("POST", f"{BASE}/{ID}:deactivate", {"version": 1}, "delete"),
    ("POST", f"{BASE}/{ID}:reactivate", {"version": 1}, "update"),
]


@pytest.mark.parametrize(("method", "path", "body", "action"), OPERATIONS)
def test_authorization_per_route(anonymous, api_as, method, path, body, action) -> None:
    resource = "global_business_sectors"
    assert anonymous.request(method, path, json=body).status_code == 401
    others = [f"perm:party-identity:{resource}:{other}" for other in ("read", "create", "update", "delete") if other != action]
    assert api_as(*others).request(method, path, json=body).status_code == 403
    assert api_as(f"perm:party-identity:{resource}:{action}").request(method, path, json=body).status_code not in {401, 403}
