"""Alta y `PUT` estrictos con versión (US3; FR-016, FR-016a, FR-016b, FR-017; N-03)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import CONDITION_TYPES

VERSION_CONFLICT = "PAYMENT_REFERENCE.VERSION_CONFLICT"


def _put(client, item_id, body):
    return client.put(f"{CONDITION_TYPES}/{item_id}", json=body)


def _current(admin, item_id):
    return admin.get(f"{CONDITION_TYPES}/{item_id}").json()


# ------------------------------------------------------------------ PUT


def test_put_full_replacement_increments_version(as_roles, admin, condition_type):
    editor = as_roles("perm:payment-reference:global_payment_condition_types:update", sub="sub-editor")

    response = _put(editor, condition_type["id"], {
        "version": 1, "code": "CREDIT", "name": "Crédito comercial", "description": "Plazo comercial",
    })

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["description"], body["version"]) == ("Crédito comercial", "Plazo comercial", 2)
    assert body["status"] == "ACTIVE"
    assert body["updated_by"] == "sub-editor"


def test_put_without_description_leaves_it_null(admin):
    created = admin.post(CONDITION_TYPES, json={"code": "CASH", "name": "Contado", "description": "Inmediato"}).json()

    response = _put(admin, created["id"], {"version": 1, "code": "CASH", "name": "Contado"})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_put_with_stale_version_is_conflict_without_changes(admin, condition_type):
    response = _put(admin, condition_type["id"], {"version": 5, "code": "CREDIT", "name": "Otro"})

    assert response.status_code == 409
    assert response.json()["code"] == VERSION_CONFLICT
    current = _current(admin, condition_type["id"])
    assert (current["name"], current["version"]) == ("Crédito", 1)


@pytest.mark.parametrize(
    "body",
    [
        {"version": 1, "code": "CREDIT", "name": "Crédito", "status": "INACTIVE"},
        {"version": 1, "code": "CREDIT", "name": "Crédito", "foo": 1},
        {"code": "CREDIT", "name": "Crédito"},
        {"version": 1, "name": "Crédito"},
        {"version": 1, "code": "CREDIT"},
        {"version": 1, "code": "X" * 31, "name": "Crédito"},
        {"version": 1, "code": "CREDIT", "name": "N" * 101},
    ],
    ids=["status", "desconocido", "sin-version", "sin-code", "sin-name", "code-31", "name-101"],
)
def test_invalid_put_body_is_422_without_changes(admin, condition_type, body):
    response = _put(admin, condition_type["id"], body)

    assert response.status_code == 422
    current = _current(admin, condition_type["id"])
    assert (current["status"], current["name"], current["version"]) == ("ACTIVE", "Crédito", 1)


def test_put_duplicate_code_is_409_without_code_field(admin, condition_type):
    other = admin.post(CONDITION_TYPES, json={"code": "CASH", "name": "Contado"}).json()

    response = _put(admin, other["id"], {"version": 1, "code": "CREDIT", "name": "Contado"})

    assert response.status_code == 409
    assert set(response.json()) == {"detail"}


def test_put_unknown_uuid_is_404(admin):
    assert _put(admin, uuid4(), {"version": 1, "code": "Z", "name": "z"}).status_code == 404


# ------------------------------------------------------------------ alta


def test_create_is_active_version_one(as_roles):
    creator = as_roles("perm:payment-reference:global_payment_condition_types:create", sub="sub-creador")

    response = creator.post(CONDITION_TYPES, json={"code": "FINANCING", "name": "Financiación"})

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["status"], body["version"], body["description"]) == ("ACTIVE", 1, None)
    assert body["created_by"] == body["updated_by"] == "sub-creador"


@pytest.mark.parametrize(
    "body",
    [
        {"code": "NEW", "name": "Nuevo", "status": "INACTIVE"},
        {"code": "NEW", "name": "Nuevo", "status": "ACTIVE"},
        {"code": "NEW", "name": "Nuevo", "version": 1},
        {"code": "NEW", "name": "Nuevo", "foo": 1},
    ],
    ids=["status-inactive", "status-active", "version", "desconocido"],
)
def test_create_rejects_fields_outside_its_contract(admin, body):
    response = admin.post(CONDITION_TYPES, json=body)

    assert response.status_code == 422
    assert admin.get(CONDITION_TYPES).json()["total_records"] == 0


def test_create_duplicate_code_is_409_without_code_field(admin, condition_type):
    response = admin.post(CONDITION_TYPES, json={"code": "CREDIT", "name": "Repetido"})

    assert response.status_code == 409
    assert set(response.json()) == {"detail"}
