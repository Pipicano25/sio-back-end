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

# Matriz objetivo de Q-C1: recursos sensibles y sectores que cada grupo puede leer.
EXPECTED = {
    "administradores": SENSITIVE | SECTORS,
    "supervisores": SENSITIVE | SECTORS,
    "compras": CONTACTS | SECTORS,
    "ventas": CONTACTS | SECTORS,
    "reportes": SECTORS,
    "consulta": SECTORS,
    "inventario": set(),
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


@pytest.mark.parametrize("group", inventory.ALL_GROUPS)
def test_no_previous_read_was_lost_except_q_c1_exclusions(realm, group) -> None:
    """No regresión: toda lectura previa se conserva salvo las excluidas por Q-C1."""
    roles = inventory.group_roles(group, realm)
    previous = set(SNAPSHOT["groups"][group]["reads"])
    excluded = SENSITIVE - EXPECTED[group]

    lost = {permission for permission in previous - excluded if not inventory.grants(roles, permission)}

    assert not lost, lost


# Altas posteriores documentadas: la spec 021 asignó a `supervisores` tres permisos nuevos de otros servicios (políticas
# de precios, resolución de actualizaciones automáticas y ajuste de la tasa de una línea de compra). No afectan a Party
# Identity; cualquier otro cambio en estos grupos sigue fallando.
LATER_ADDITIONS = {
    "supervisores": {
        "perm:commercial-relationship:pricing_policies:delete",
        "perm:commercial-relationship:automatic_price_applications:resolve",
        "perm:purchase:purchase_line_taxes:override",
    },
    # Spec 022 (FR-022-111): permisos del servicio de consultas consolidadas para `inventario`. No afectan a Party
    # Identity.
    "inventario": {
        "perm:product-inventory-query:product_overviews:read",
        "perm:product-inventory-query:inventory_overviews:read",
        "perm:product-inventory-query:inventory_summary:read",
        "perm:product-inventory-query:low_stock_products:read",
        "perm:product-inventory-query:stock:read",
        # Spec 023 (DR-11): evolución de existencias (solo cantidades) y su reporte. No afectan a Party Identity.
        "perm:inventory:stock_evolution:read",
        "perm:business-reporting:stock_evolution:read",
    },
}


@pytest.mark.parametrize("group", ["administradores", "supervisores", "inventario"])
def test_unchanged_groups_keep_their_roles(realm, group) -> None:
    current = inventory.group_roles(group, realm)
    before = SNAPSHOT["groups"][group]["roles"]
    assert [role for role in current if role in before] == before  # conserva todos, en el mismo orden
    assert set(current) - set(before) == LATER_ADDITIONS.get(group, set())


@pytest.mark.parametrize("group", inventory.READ_ONLY_GROUPS)
def test_read_only_groups_no_longer_use_broad_read_wildcards(realm, group) -> None:
    roles = inventory.group_roles(group, realm)

    assert "perm:all:all:read" not in roles
    assert "perm:party-identity:all:read" not in roles


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


def test_every_read_permission_declared_by_code_exists_and_is_preserved(realm) -> None:
    """T083: los permisos `read` que declaran los routers existen como rol y los conservan reportes/consulta."""
    declared, _ = inventory.declared_read_permissions()
    names = set(inventory.realm_roles(realm))

    assert declared <= names, declared - names
    # La lectura de auditoría es exclusiva de quien la feature 011 decidió (no de reportes/consulta).
    audit_reads = {permission for permission in declared if permission.startswith("perm:audit:")}
    for group in ("reportes", "consulta"):
        roles = inventory.group_roles(group, realm)
        missing = {
            permission
            for permission in declared - SENSITIVE - audit_reads
            if not inventory.grants(roles, permission)
        }
        assert not missing, (group, missing)
