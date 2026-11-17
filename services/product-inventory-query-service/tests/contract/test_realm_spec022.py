"""Plantilla del realm para la spec 022 (FR-022-100, FR-022-101, FR-022-110, FR-022-111; T056).

Lee `infrastructure/keycloak/realm-template/sio-realm.template.json`. Solo verifica la plantilla: el realm
persistente no se modifica en esta spec sin autorización (FR-022-112).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
TEMPLATE = REPO / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
COMPOSE = REPO / "infrastructure" / "compose.yaml"
CLIENT = "product-inventory-query-service"

PIQ = "perm:product-inventory-query"
NEW_ROLES = {
    f"{PIQ}:product_overviews:read",
    f"{PIQ}:inventory_overviews:read",
    f"{PIQ}:inventory_summary:read",
    f"{PIQ}:low_stock_products:read",
    f"{PIQ}:stock:read",
    f"{PIQ}:inventory_valuation:read",
}
# Spec 026: `empleado` reúne lo que tenían `ventas` e `inventario` (sin valoración); `admin` lee todo el servicio con
# permisos explícitos; `superadmin` lo cubre con `perm:all:all:all`.
GROUP_ROLES = {
    "empleado": {
        f"{PIQ}:product_overviews:read",
        f"{PIQ}:inventory_overviews:read",
        f"{PIQ}:inventory_summary:read",
        f"{PIQ}:low_stock_products:read",
        f"{PIQ}:stock:read",
    },
    "admin": NEW_ROLES,
}
TECHNICAL_ROLES = {
    "perm:commercial-relationship:platform:lookup",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:product-catalog:products:read",
    "perm:product-catalog:brands:read",
    "perm:product-catalog:categories:read",
    "perm:product-catalog:units-of-measure:read",
    "perm:inventory:platform:lookup",
    "perm:inventory:balances:read",
    "perm:inventory:product-policies:read",
}


@pytest.fixture(scope="module")
def realm() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def _groups(realm) -> dict[str, set[str]]:
    return {group["name"]: set(group.get("clientRoles", {}).get("sio-api", [])) for group in realm["groups"]}


def test_new_roles_exist_in_sio_api(realm) -> None:
    names = {role["name"] for role in realm["roles"]["client"]["sio-api"]}
    assert NEW_ROLES <= names
    descriptions = {role["name"]: role.get("description", "") for role in realm["roles"]["client"]["sio-api"]}
    assert all(descriptions[name] for name in NEW_ROLES)


def test_group_assignments_are_exact(realm) -> None:
    groups = _groups(realm)
    for group, expected in GROUP_ROLES.items():
        assert groups[group] & NEW_ROLES == expected, group


def test_empleado_has_no_valuation_permission(realm) -> None:
    empleado = _groups(realm)["empleado"]
    assert f"{PIQ}:inventory_valuation:read" not in empleado


def test_superadmin_covers_everything_without_explicit_roles(realm) -> None:
    groups = _groups(realm)
    assert "perm:all:all:all" in groups["superadmin"]
    assert not (groups["superadmin"] & NEW_ROLES)


def test_no_other_client_or_user_received_the_new_roles(realm) -> None:
    for user in realm["users"]:
        roles = set(user.get("clientRoles", {}).get("sio-api", []))
        assert not (roles & NEW_ROLES), user["username"]


def test_technical_client_is_confidential_with_service_account(realm) -> None:
    [client] = [c for c in realm["clients"] if c["clientId"] == CLIENT]
    assert client["publicClient"] is False
    assert client["serviceAccountsEnabled"] is True
    assert client["standardFlowEnabled"] is False and client["directAccessGrantsEnabled"] is False
    assert client["secret"] == "${PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET}"


def test_technical_client_has_exactly_the_read_roles(realm) -> None:
    [account] = [u for u in realm["users"] if u.get("serviceAccountClientId") == CLIENT]
    roles = set(account["clientRoles"]["sio-api"])
    assert roles == TECHNICAL_ROLES
    names = {role["name"] for role in realm["roles"]["client"]["sio-api"]}
    assert TECHNICAL_ROLES <= names, TECHNICAL_ROLES - names
    for role in roles:
        assert role.endswith((":read", ":lookup")), role
        assert not role.startswith(("perm:audit", "perm:purchase", "perm:sales", "perm:party-identity", "perm:operational-context"))


def test_technical_client_has_no_valuation_permission(realm) -> None:
    """Mínimo privilegio (D-022-12): el servicio no pide valoración a Inventory ni la entrega, así que su cuenta
    técnica no tiene `perm:inventory:valuation:read` ni el permiso reservado de este servicio."""
    [account] = [u for u in realm["users"] if u.get("serviceAccountClientId") == CLIENT]
    roles = set(account["clientRoles"]["sio-api"])
    assert not any("valuation" in role for role in roles)


def test_reserved_valuation_role_is_not_assigned(realm) -> None:
    """`inventory_valuation:read` queda definido para una spec futura: ningún usuario ni cuenta lo tiene, y entre los
    grupos solo `admin` (spec 026: lectura de todo Product Inventory Query); el servicio no expone esa ruta."""
    role = f"{PIQ}:inventory_valuation:read"
    assert [name for name, roles in _groups(realm).items() if role in roles] == ["admin"]
    assert all(role not in user.get("clientRoles", {}).get("sio-api", []) for user in realm["users"])


def test_inventory_valuation_assignments_are_unchanged(realm) -> None:
    """Retirar el permiso del cliente técnico no altera los roles de Inventory: el grupo `empleado` (antes
    `inventario`, spec 026) y la cuenta de prueba de Inventory lo conservan."""
    assert "perm:inventory:valuation:read" in _groups(realm)["empleado"]
    [operator] = [u for u in realm["users"] if u["username"] == "service-account-inventory-test-operator"]
    assert "perm:inventory:valuation:read" in operator["clientRoles"]["sio-api"]
    names = {role["name"] for role in realm["roles"]["client"]["sio-api"]}
    assert "perm:inventory:valuation:read" in names


def test_keycloak_receives_the_secret_from_the_environment() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET: ${PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET}" in compose
    assert "change-this" not in TEMPLATE.read_text(encoding="utf-8").split(CLIENT, 1)[1][:2000]


def test_no_realm_text_exceeds_keycloak_column_limits(realm) -> None:
    """Keycloak guarda descripciones y nombres en columnas de 255 caracteres: un texto más largo hace fallar la
    importación del realm (lo detectó la pila aislada de la spec 022)."""
    long_values = []

    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
        elif isinstance(value, str) and len(value) > 255:
            long_values.append(path)

    walk(realm, "")
    assert long_values == []
