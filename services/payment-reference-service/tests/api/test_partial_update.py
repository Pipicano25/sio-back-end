"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28)."""

from __future__ import annotations

import pytest

from tests.conftest import CONDITION_TYPES, METHODS


def test_condition_type_put_with_one_field_keeps_the_rest(admin):
    created = admin.post(CONDITION_TYPES, json={"code": "CASH", "name": "Contado", "description": "Inmediato"}).json()

    response = admin.put(f"{CONDITION_TYPES}/{created['id']}", json={"name": "Contado inmediato"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["code"], body["name"], body["description"]) == ("CASH", "Contado inmediato", "Inmediato")
    assert body["version"] == created["version"] + 1


def test_condition_type_null_clears_description(admin):
    created = admin.post(CONDITION_TYPES, json={"code": "CASH", "name": "Contado", "description": "Inmediato"}).json()

    response = admin.put(f"{CONDITION_TYPES}/{created['id']}", json={"description": None})

    assert response.status_code == 200, response.text
    assert response.json()["description"] is None


def test_condition_type_stale_version_is_409_and_missing_version_applies(admin, condition_type):
    admin.put(f"{CONDITION_TYPES}/{condition_type['id']}", json={"name": "Primero"})

    stale = admin.put(f"{CONDITION_TYPES}/{condition_type['id']}", json={"name": "Segundo", "version": 1})
    latest = admin.put(f"{CONDITION_TYPES}/{condition_type['id']}", json={"name": "Tercero"})

    assert stale.status_code == 409
    assert latest.status_code == 200, latest.text
    assert latest.json()["name"] == "Tercero"


@pytest.mark.parametrize("body", [{}, {"version": 1}, {"name": None}, {"nombre": "X"}])
def test_condition_type_body_without_valid_changes_is_422(admin, condition_type, body):
    assert admin.put(f"{CONDITION_TYPES}/{condition_type['id']}", json=body).status_code == 422


def test_condition_type_status_actions_without_body(admin, condition_type):
    deactivated = admin.post(f"{CONDITION_TYPES}/{condition_type['id']}/deactivate")
    reactivated = admin.post(f"{CONDITION_TYPES}/{condition_type['id']}/reactivate", json={})

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "ACTIVE"


def test_payment_method_put_changes_only_status(admin):
    method = admin.post(
        METHODS,
        json={"code": "EFECTIVO_PARCIAL", "name": "Efectivo", "method_type": "CASH", "requires_reference": False,
              "status": "ACTIVE"},
    ).json()

    response = admin.put(f"{METHODS}/{method['id']}", json={"status": "INACTIVE"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert (body["code"], body["name"], body["method_type"]) == ("EFECTIVO_PARCIAL", "Efectivo", "CASH")
