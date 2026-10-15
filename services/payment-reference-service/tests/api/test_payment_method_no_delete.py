"""Métodos de pago sin borrado físico (spec 020, FR-020-10, RC-MVP-4; GAP-PR-18 parcial; D7)."""

from __future__ import annotations

from tests.conftest import ADMIN, METHODS


def _method(admin) -> dict:
    response = admin.post(
        METHODS,
        json={"code": "EFECTIVO_PRUEBA", "name": "Efectivo", "method_type": "CASH", "requires_reference": False, "status": "ACTIVE"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_delete_route_no_longer_exists(as_roles, admin):
    method = _method(admin)

    response = as_roles(ADMIN).delete(f"{METHODS}/{method['id']}")

    assert response.status_code == 405
    assert admin.get(f"{METHODS}/{method['id']}").status_code == 200


def test_method_is_inactivated_with_put_and_remains_readable(admin):
    method = _method(admin)
    body = {key: method[key] for key in ("code", "name", "method_type", "requires_reference")}

    response = admin.put(f"{METHODS}/{method['id']}", json={**body, "status": "INACTIVE"})

    assert response.status_code == 200, response.text
    fetched = admin.get(f"{METHODS}/{method['id']}")
    assert fetched.status_code == 200 and fetched.json()["status"] == "INACTIVE"
