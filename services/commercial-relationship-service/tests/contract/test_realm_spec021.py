"""Permisos de la spec 021 en la plantilla del realm (FR-021-32, FR-021-32a; T005, T006).

Se evalúa con `sio-auth` (incluidos los comodines) sobre la plantilla versionada:

- Los permisos nuevos de políticas, tasas y actualizaciones automáticas solo los tienen
  `administradores` (por `perm:all:all:all`) y `supervisores` (comodines más asignación explícita).
- `compras` y `ventas` ya no tienen los comodines `perm:purchase:all:all` ni
  `perm:commercial-relationship:all:read`: se reemplazaron por la lista explícita equivalente, de modo
  que conservan exactamente sus permisos anteriores sin ganar los nuevos (costos, porcentajes y el
  ajuste de tasa de línea).
- `automatic_price_update_requests:submit` lo tiene solo la cuenta técnica de Purchase; los
  administradores lo cubren por su comodín total, pero la ruta exige además identidad técnica (DS-05).
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
ACCOUNTS = {user["username"]: user.get("clientRoles", {}).get("sio-api", []) for user in DATA["users"]}
ROLES = [role["name"] for role in DATA["roles"]["client"]["sio-api"]]

CR = "commercial-relationship"
SENSITIVE = [
    SioPermission(CR, "pricing_policies", "read"),
    SioPermission(CR, "pricing_policies", "create"),
    SioPermission(CR, "pricing_policies", "update"),
    SioPermission(CR, "pricing_policies", "delete"),
    SioPermission(CR, "company_product_purchase_taxes", "update"),
    SioPermission(CR, "automatic_price_applications", "read"),
    SioPermission(CR, "automatic_price_applications", "resolve"),
    SioPermission("purchase", "purchase_line_taxes", "override"),
]
SUBMIT = SioPermission(CR, "automatic_price_update_requests", "submit")
NEW = {f"perm:{p.service}:{p.resource}:{p.action}" for p in [*SENSITIVE, SUBMIT]}


def concrete(prefix: str, action: str | None = None) -> list[SioPermission]:
    """Permisos concretos (sin comodines) anteriores a la spec 021 con ese prefijo."""
    found = []
    for name in ROLES:
        parts = name.split(":")
        if len(parts) != 4 or not name.startswith(prefix) or "all" in parts[1:] or name in NEW:
            continue
        if action is None or parts[3] == action:
            found.append(SioPermission(parts[1], parts[2], parts[3]))
    return found


def test_new_roles_exist() -> None:
    assert NEW <= set(ROLES)


@pytest.mark.parametrize("permission", SENSITIVE, ids=lambda p: f"{p.resource}:{p.action}")
@pytest.mark.parametrize(
    ("group", "expected"),
    [
        ("administradores", True),
        ("supervisores", True),
        ("compras", False),
        ("ventas", False),
        ("inventario", False),
        ("reportes", False),
        ("consulta", False),
    ],
)
def test_sensitive_permissions_only_for_admins_and_supervisors(group: str, expected: bool, permission) -> None:
    assert evaluate_permission(GROUPS[group], permission) is expected


def test_submit_only_for_purchase_technical_account() -> None:
    holders = {name for name, roles in ACCOUNTS.items() if evaluate_permission(roles, SUBMIT)}
    assert holders == {"service-account-purchase-service"}
    groups = {name for name, roles in GROUPS.items() if evaluate_permission(roles, SUBMIT)}
    assert groups == {"administradores"}  # comodín total; la ruta exige además identidad técnica


@pytest.mark.parametrize("group", ["compras", "ventas"])
def test_wildcards_replaced_by_explicit_equivalent(group: str) -> None:
    roles = GROUPS[group]
    assert "perm:commercial-relationship:all:read" not in roles
    assert "perm:purchase:all:all" not in roles
    for permission in concrete(f"perm:{CR}:", "read"):
        assert evaluate_permission(roles, permission), permission


def test_purchasers_keep_every_previous_purchase_permission() -> None:
    for permission in concrete("perm:purchase:"):
        assert evaluate_permission(GROUPS["compras"], permission), permission


def test_sellers_keep_sales_permissions_without_purchase_access() -> None:
    assert evaluate_permission(GROUPS["ventas"], SioPermission("sales", "sales", "create"))
    assert not evaluate_permission(GROUPS["ventas"], SioPermission("purchase", "purchases", "read"))
