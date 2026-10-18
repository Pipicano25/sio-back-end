"""Usuarios de prueba del realm y evaluación de permisos con `sio-auth` (Principio XXII).

Se leen de la plantilla versionada del realm
(`infrastructure/keycloak/realm-template/sio-realm.template.json`): si la plantilla cambia, la prueba de
ejemplos y la documentación generada cambian con ella.
"""

from __future__ import annotations

import json
from pathlib import Path

from sio_auth.models import SioPermission
from sio_auth.permissions import extract_permission_grants, has_permission

REPO_ROOT = Path(__file__).resolve().parents[4]
REALM = REPO_ROOT / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"

_data = json.loads(REALM.read_text(encoding="utf-8"))
_groups = {"/" + group["name"]: group for group in _data["groups"]}

REALM_ROLES = frozenset(role["name"] for role in _data["roles"]["client"]["sio-api"])

USERS: list[dict] = []
for user in _data["users"]:
    if "serviceAccountClientId" in user:
        continue
    group = user["groups"][0]
    roles = _groups[group]["clientRoles"]["sio-api"]
    USERS.append(dict(username=user["username"], group=group.lstrip("/"), roles=roles,
                      perms=[role for role in roles if role.startswith("perm:")]))

PRICES = "perm:commercial-relationship:price_list_items:read"
STOCK = "perm:product-inventory-query:stock:read"
MINIMUMS = "perm:inventory:product-policies:read"
BLOCKS = {"Precios": PRICES, "Existencias": STOCK, "Mínimos": MINIMUMS}


def parse(permission: str) -> SioPermission:
    _, service, resource, action = permission.split(":")
    return SioPermission(service, resource, action)


def matching_grant(roles: list[str], permission: str) -> str | None:
    required = parse(permission)
    for role in roles:
        if role.startswith("perm:") and has_permission(extract_permission_grants([role]), required):
            return role
    return None


def allowed(user: dict, permission: str) -> bool:
    return matching_grant(user["perms"], permission) is not None
