"""Inactivar y reactivar sin borrar (US2; RC-02, RC-04; FR-010 a FR-015, FR-016b)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from tests.conftest import CONDITION_TYPES, CT_DELETE, CT_UPDATE

VERSION_CONFLICT = "PAYMENT_REFERENCE.VERSION_CONFLICT"
INVALID_TRANSITION = "PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION"


def _action(client, item_id, action, version):
    return client.post(f"{CONDITION_TYPES}/{item_id}/{action}", json={"version": version})


def _current(admin, item_id):
    return admin.get(f"{CONDITION_TYPES}/{item_id}").json()


def test_deactivate_with_current_version(as_roles, admin, condition_type):
    actor = as_roles(CT_DELETE, sub="sub-catalogo")

    response = _action(actor, condition_type["id"], "deactivate", 1)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert body["version"] == 2
    assert body["updated_by"] == "sub-catalogo"
    assert body["created_by"] == condition_type["created_by"]
    assert datetime.fromisoformat(body["updated_at"]) > datetime.fromisoformat(condition_type["updated_at"])


def test_reactivate_with_current_version(as_roles, admin, condition_type):
    _action(admin, condition_type["id"], "deactivate", 1)

    response = _action(as_roles(CT_UPDATE, sub="sub-editor"), condition_type["id"], "reactivate", 2)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["version"] == 3
    assert response.json()["updated_by"] == "sub-editor"


def test_deactivating_an_inactive_type_is_invalid_transition(admin, condition_type):
    _action(admin, condition_type["id"], "deactivate", 1)

    response = _action(admin, condition_type["id"], "deactivate", 2)

    assert response.status_code == 409
    assert response.json()["code"] == INVALID_TRANSITION
    assert response.json()["detail"]
    assert _current(admin, condition_type["id"])["version"] == 2


def test_reactivating_an_active_type_is_invalid_transition(admin, condition_type):
    response = _action(admin, condition_type["id"], "reactivate", 1)

    assert response.status_code == 409
    assert response.json()["code"] == INVALID_TRANSITION
    current = _current(admin, condition_type["id"])
    assert (current["status"], current["version"]) == ("ACTIVE", 1)


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_stale_version_is_version_conflict_without_changes(admin, condition_type, action):
    response = _action(admin, condition_type["id"], action, 7)

    assert response.status_code == 409
    assert response.json()["code"] == VERSION_CONFLICT
    current = _current(admin, condition_type["id"])
    assert (current["status"], current["version"]) == ("ACTIVE", 1)


def test_version_is_checked_before_transition(admin, condition_type):
    """Versión vieja y transición inválida a la vez → conflicto de versión (orden de data-model)."""
    response = _action(admin, condition_type["id"], "reactivate", 99)

    assert response.json()["code"] == VERSION_CONFLICT


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_unknown_uuid_is_404(admin, action):
    assert _action(admin, uuid4(), action, 1).status_code == 404


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
@pytest.mark.parametrize(
    "body",
    [{}, {"version": "uno"}, {"version": 1.5}, {"version": 1, "status": "INACTIVE"}, {"version": 1, "foo": 1}],
    ids=["sin-version", "no-entera-texto", "no-entera-decimal", "status", "desconocido"],
)
def test_invalid_action_body_is_422_without_changes(admin, condition_type, action, body):
    response = admin.post(f"{CONDITION_TYPES}/{condition_type['id']}/{action}", json=body)

    assert response.status_code == 422
    assert _current(admin, condition_type["id"])["version"] == 1


def test_reactivate_requires_update_permission(as_roles, admin, condition_type):
    _action(admin, condition_type["id"], "deactivate", 1)

    assert _action(as_roles(CT_DELETE), condition_type["id"], "reactivate", 2).status_code == 403
    assert _action(as_roles(CT_UPDATE), condition_type["id"], "reactivate", 2).status_code == 200


def test_deactivate_requires_delete_permission(as_roles, condition_type):
    assert _action(as_roles(CT_UPDATE), condition_type["id"], "deactivate", 1).status_code == 403


def test_delete_does_not_exist_and_record_remains(admin, condition_type):
    response = admin.delete(f"{CONDITION_TYPES}/{condition_type['id']}")

    assert response.status_code == 405
    assert admin.get(f"{CONDITION_TYPES}/{condition_type['id']}").status_code == 200
