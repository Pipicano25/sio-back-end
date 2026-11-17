"""Mínimo privilegio en la plantilla del realm (T084; RC-17, SC-012, FR-110, FR-111, Q-C1).

Compara la plantilla vigente con la instantánea `data/realm_reads_before.json`,
tomada con la plantilla anterior al ajuste, usando la lógica de `sio-auth`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import realm_inventory as inventory  # noqa: E402

SENSITIVE = {
    "perm:party-identity:person_contact_profiles:read",
    "perm:party-identity:organization_contact_profiles:read",
    "perm:party-identity:organization_contact_persons:read",
    "perm:party-identity:organization_legal_representatives:read",
}
SECTORS = {
    "perm:party-identity:global_business_sectors:read",
    "perm:party-identity:organization_business_sectors:read",
}
CONTACTS = SENSITIVE - {"perm:party-identity:organization_legal_representatives:read"}

# Matriz objetivo de Q-C1 con los tres grupos de la spec 026: los tres leen contactos, representantes y sectores
# (el Empleado registra y corrige personas y organizaciones; FR-010, FR-011).
EXPECTED = {
    "superadmin": SENSITIVE | SECTORS,
    "admin": SENSITIVE | SECTORS,
    "empleado": SENSITIVE | SECTORS,
}
SNAPSHOT = json.loads(inventory.SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def realm() -> dict:
    return inventory.load_realm()


@pytest.mark.parametrize("group", sorted(EXPECTED))
def test_q_c1_matrix_for_sensitive_and_sector_resources(realm, group) -> None:
    roles = inventory.group_roles(group, realm)
    granted = {permission for permission in SENSITIVE | SECTORS if inventory.grants(roles, permission)}

    assert granted == EXPECTED[group]


@pytest.mark.parametrize(("previous", "current"), sorted(inventory.PREVIOUS_TO_CURRENT.items()))
def test_no_previous_read_was_lost(realm, previous, current) -> None:
    """No regresión: el grupo nuevo conserva toda lectura del grupo de la instantánea que lo origina."""
    roles = inventory.group_roles(current, realm)
    expected_previous = set(SNAPSHOT["groups"][previous]["reads"]) - (SENSITIVE - EXPECTED[current])

    lost = {permission for permission in expected_previous if not inventory.grants(roles, permission)}

    assert not lost, lost


def test_superadmin_keeps_the_global_wildcard(realm) -> None:
    assert inventory.group_roles("superadmin", realm) == ["superadmin", "perm:all:all:all"]


@pytest.mark.parametrize("group", ["admin", "empleado"])
def test_user_groups_do_not_use_global_read_wildcards(realm, group) -> None:
    roles = inventory.group_roles(group, realm)

    assert "perm:all:all:read" not in roles
    assert "perm:all:all:all" not in roles


@pytest.mark.parametrize("group", ["admin", "empleado"])
def test_user_groups_never_delete_in_party_identity(realm, group) -> None:
    deletes = [name for name in inventory.realm_roles(realm) if name.startswith("perm:party-identity:")
               and name.endswith(":delete") and ":all:" not in name]
    assert [name for name in deletes if inventory.grants(inventory.group_roles(group, realm), name)] == []


def test_party_identity_service_account_can_query_operational_context(realm) -> None:
    roles = inventory.service_account_roles("party-identity-service", realm)

    assert "perm:operational-context:platform:lookup" in roles
    assert "perm:operational-context:application_users:read" in roles
    assert "perm:geography:global_countries:read" in roles


def test_phase_b_roles_exist(realm) -> None:
    names = set(inventory.realm_roles(realm))
    for resource in (
        "person_contact_profiles", "organization_contact_profiles", "organization_contact_persons",
        "global_business_sectors", "organization_business_sectors", "organization_legal_representatives",
    ):
        for action in ("read", "create", "update", "delete"):
            assert f"perm:party-identity:{resource}:{action}" in names


def test_every_read_permission_declared_by_code_exists_and_admin_reads_it(realm) -> None:
    """T083: los permisos `read` que declaran los routers existen como rol y el Admin los cubre todos, salvo la lectura
    de auditoría de plataforma, exclusiva del SuperAdmin (spec 026, FR-005)."""
    declared, _ = inventory.declared_read_permissions()
    names = set(inventory.realm_roles(realm))

    assert declared <= names, declared - names
    roles = inventory.group_roles("admin", realm)
    missing = {
        permission
        for permission in declared - {"perm:audit:platform-events:read"}
        if not inventory.grants(roles, permission)
    }
    assert not missing, missing
