"""Permisos `perm:payment-reference:…` y mínimo privilegio (RC-01; FR-001 a FR-005; GAP-PR-01)."""

from __future__ import annotations

import pytest
from sio_auth import FORBIDDEN_DETAIL

from tests.conftest import (
    CONDITION_TYPES,
    CT_READ,
    METHODS,
)

ANY_ID = "00000000-0000-4000-8000-000000000001"
CT = "global_payment_condition_types"
PM = "global_payment_methods"

# (método, ruta, recurso, acción)
ROUTES = [
    ("GET", CONDITION_TYPES, CT, "read"),
    ("POST", CONDITION_TYPES, CT, "create"),
    ("GET", f"{CONDITION_TYPES}/{ANY_ID}", CT, "read"),
    ("PUT", f"{CONDITION_TYPES}/{ANY_ID}", CT, "update"),
    ("POST", f"{CONDITION_TYPES}/{ANY_ID}/deactivate", CT, "delete"),
    ("POST", f"{CONDITION_TYPES}/{ANY_ID}/reactivate", CT, "update"),
    ("GET", METHODS, PM, "read"),
    ("POST", METHODS, PM, "create"),
    ("GET", f"{METHODS}/{ANY_ID}", PM, "read"),
    ("PUT", f"{METHODS}/{ANY_ID}", PM, "update"),
]
IDS = [f"{method} {path}" for method, path, _, _ in ROUTES]


def _call(client, method, path):
    if method in {"GET", "DELETE"}:
        return client.request(method, path)
    return client.request(method, path, json={})


@pytest.mark.parametrize(("method", "path", "resource", "action"), ROUTES, ids=IDS)
def test_without_token_is_401(as_token, method, path, resource, action):
    assert _call(as_token(None), method, path).status_code == 401


@pytest.mark.parametrize(("method", "path", "resource", "action"), ROUTES, ids=IDS)
def test_without_permission_is_403_without_revealing_it(as_roles, method, path, resource, action):
    response = _call(as_roles("perm:commercial-relationship:all:all"), method, path)

    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    assert "perm:" not in response.text


@pytest.mark.parametrize(("method", "path", "resource", "action"), ROUTES, ids=IDS)
def test_exact_permission_passes_authorization(as_roles, method, path, resource, action):
    response = _call(as_roles(f"perm:payment-reference:{resource}:{action}"), method, path)

    assert response.status_code not in {401, 403}, response.text


@pytest.mark.parametrize(("method", "path", "resource", "action"), ROUTES, ids=IDS)
def test_underscore_service_segment_is_not_accepted(as_roles, method, path, resource, action):
    """El segmento histórico `payment_reference` no concede nada (FR-001)."""
    response = _call(as_roles(f"perm:payment_reference:{resource}:{action}"), method, path)

    assert response.status_code == 403


def test_specific_read_permission_lists_and_gets_by_uuid(as_roles, condition_type):
    reader = as_roles(CT_READ, sub="sub-reportes")

    listed = reader.get(CONDITION_TYPES)
    fetched = reader.get(f"{CONDITION_TYPES}/{condition_type['id']}")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [condition_type["id"]]
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "ACTIVE"


def test_specific_read_permission_cannot_write(as_roles, condition_type):
    reader = as_roles(CT_READ, sub="sub-reportes")

    deactivate = reader.post(
        f"{CONDITION_TYPES}/{condition_type['id']}/deactivate",
        json={"version": condition_type["version"]},
    )

    assert deactivate.status_code == 403


def test_service_wildcard_read_permission_reads(as_roles, condition_type):
    response = as_roles("perm:payment-reference:all:read", sub="sub-compras").get(
        f"{CONDITION_TYPES}/{condition_type['id']}"
    )

    assert response.status_code == 200


def test_payment_methods_with_their_specific_read_permission(as_roles):
    response = as_roles("perm:payment-reference:global_payment_methods:read").get(METHODS)

    assert response.status_code == 200


def test_global_update_wildcard_cannot_deactivate(as_roles, condition_type):
    """`perm:all:all:update` (supervisores) no concede `delete`: no puede inactivar (FR-004)."""
    supervisor = as_roles("perm:all:all:read", "perm:all:all:create", "perm:all:all:update")

    response = supervisor.post(
        f"{CONDITION_TYPES}/{condition_type['id']}/deactivate",
        json={"version": condition_type["version"]},
    )

    assert response.status_code == 403
