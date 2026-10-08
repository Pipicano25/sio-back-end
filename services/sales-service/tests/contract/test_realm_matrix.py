"""Matriz de grupos y cliente técnico en la plantilla del realm (C-08, DS-12; research.md R-02; T076).

Se evalúa con `sio-auth` (incluidos los comodines) sobre la plantilla versionada: solo
`administradores` (por `perm:all:all:all`) y `supervisores` (asignación explícita) ven la
rentabilidad; `ventas` conserva el CRUD de sales sin ella; el cliente `sales-service` tiene
exactamente los roles de R-02 y nunca puede escribir ventas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sio_auth.models import SioPermission
from sio_auth.permissions import evaluate_permission

REALM = Path(__file__).resolve().parents[4] / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
DATA = json.loads(REALM.read_text(encoding="utf-8"))
GROUPS = {group["name"]: group["clientRoles"]["sio-api"] for group in DATA["groups"]}
PROFITABILITY = SioPermission("sales", "sales", "read-profitability")

SALES_CLIENT_ROLES = {
    "perm:operational-context:platform:lookup",
    "perm:operational-context:companies:read",
    "perm:operational-context:branches:read",
    "perm:operational-context:application_users:read",
    "perm:commercial-relationship:platform:lookup",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_product_presentations:read",
    "perm:commercial-relationship:price_lists:read",
    "perm:commercial-relationship:price_list_items:read",
    "perm:product-catalog:products:read",
    "perm:product-catalog:units-of-measure:read",
    "perm:party-identity:person_identities:read",
    "perm:party-identity:organization_identities:read",
    "perm:inventory:outputs:create",
    "perm:inventory:balances:read",
    "perm:inventory:movements:read",
    "perm:inventory:platform:lookup",
    "perm:audit:audit-events:create",
}


def test_profitability_role_exists() -> None:
    roles = {role["name"] for role in DATA["roles"]["client"]["sio-api"]}
    assert "perm:sales:sales:read-profitability" in roles


@pytest.mark.parametrize(
    ("group", "expected"),
    [
        ("administradores", True),
        ("supervisores", True),
        ("ventas", False),
        ("reportes", False),
        ("consulta", False),
        ("compras", False),
        ("inventario", False),
    ],
)
def test_who_sees_profitability(group, expected) -> None:
    assert evaluate_permission(GROUPS[group], PROFITABILITY) is expected


def test_ventas_keeps_full_sales_crud_without_wildcard() -> None:
    roles = GROUPS["ventas"]
    assert "perm:sales:all:all" not in roles
    for resource in ("sales", "sale_details", "sale_sequences", "sale_operations"):
        for action in ("create", "read", "update", "delete"):
            assert evaluate_permission(roles, SioPermission("sales", resource, action)), (resource, action)


def test_supervisores_keep_their_wildcards() -> None:
    assert {"perm:all:all:read", "perm:all:all:create", "perm:all:all:update"} <= set(GROUPS["supervisores"])


def test_sales_service_client_and_account() -> None:
    client = next(item for item in DATA["clients"] if item["clientId"] == "sales-service")
    assert client["serviceAccountsEnabled"] is True and client["publicClient"] is False
    assert client["standardFlowEnabled"] is False and client["directAccessGrantsEnabled"] is False
    assert "service_account" in client["defaultClientScopes"]
    assert client["secret"] == "${SALES_SERVICE_CLIENT_SECRET}"
    assert len(client["description"]) < 255
    assert any(mapper["config"].get("included.client.audience") == "sio-api" for mapper in client["protocolMappers"])
    account = next(user for user in DATA["users"] if user.get("serviceAccountClientId") == "sales-service")
    assert account["id"] == "5b2e8c41-7a3d-4f6e-9c12-3d44e5f6a7b8"
    assert set(account["clientRoles"]["sio-api"]) == SALES_CLIENT_ROLES
    assert not evaluate_permission(account["clientRoles"]["sio-api"], SioPermission("sales", "sales", "create"))
    assert not evaluate_permission(account["clientRoles"]["sio-api"], PROFITABILITY)
