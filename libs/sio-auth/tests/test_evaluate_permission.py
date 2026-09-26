"""Pruebas de `evaluate_permission` (API pública de sio-auth 0.3.0)."""

import pytest

from sio_auth import SioPermission, evaluate_permission
from sio_auth.permissions import extract_permission_grants, has_permission

REQUIRED = SioPermission("inventory", "movements", "create")


@pytest.mark.parametrize(
    "roles",
    [
        ["perm:inventory:movements:create"],
        ["perm:all:all:all"],
        ["perm:inventory:all:all"],
        ["perm:inventory:movements:all"],
        ["perm:all:movements:create"],
        ["rol-normal", "perm:inventory:all:create"],
    ],
)
def test_concede_con_rol_exacto_o_wildcard(roles):
    assert evaluate_permission(roles, REQUIRED) is True


@pytest.mark.parametrize(
    "roles",
    [
        [],
        ["perm:inventory:movements:read"],
        ["perm:all:all:read"],
        ["perm:sales:all:all"],
        ["inventory:movements:create"],
        ["perm:inventory:movements"],
        ["perm:Inventory:movements:create"],
        ["perm:inventory:movements:create:extra"],
    ],
)
def test_niega_sin_rol_o_con_roles_mal_formados(roles):
    assert evaluate_permission(roles, REQUIRED) is False


def test_mismo_resultado_que_el_algoritmo_interno():
    cases = [
        ["perm:all:all:all"],
        ["perm:inventory:all:read"],
        ["perm:inventory:movements:create", "perm:x"],
        ["perm:operational-context:platform:administer"],
        [],
    ]
    for roles in cases:
        for required in (
            REQUIRED,
            SioPermission("operational-context", "platform", "administer"),
            SioPermission("operational-context", "platform", "lookup"),
        ):
            assert evaluate_permission(roles, required) == has_permission(
                extract_permission_grants(roles), required
            )


def test_acepta_cualquier_iterable():
    assert evaluate_permission(iter(["perm:all:all:all"]), REQUIRED) is True
    assert evaluate_permission(frozenset({"perm:inventory:all:all"}), REQUIRED) is True
