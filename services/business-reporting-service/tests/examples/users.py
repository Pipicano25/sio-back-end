"""Usuarios de prueba del realm y evaluación de permisos con `sio-auth` (Principio XXII).

Se leen de la plantilla versionada del realm: si cambia, la prueba de ejemplos y la documentación cambian con ella.
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

# Solo los usuarios de prueba aparecen en los ejemplos; los copiados del servidor OCI (alex, manuel, pedro, tomas)
# quedan fuera (spec 026).
EXAMPLE_USERS = ("admin.sio", "admin.dao", "operario.dao")


def _user_roles(user):
    """Roles de `sio-api` del usuario: suma de los de todos sus grupos, sin repetir (spec 026)."""
    return list(dict.fromkeys(role for path in user["groups"] for role in _groups[path]["clientRoles"]["sio-api"]))

REALM_ROLES = frozenset(role["name"] for role in _data["roles"]["client"]["sio-api"])

USERS: list[dict] = []
for user in _data["users"]:
    if "serviceAccountClientId" in user:
        continue
    if user["username"] not in EXAMPLE_USERS:
        continue
    roles = _user_roles(user)
    group = ", ".join(path.lstrip("/") for path in user["groups"])
    USERS.append(dict(username=user["username"], group=group.lstrip("/"), roles=roles,
                      perms=[role for role in roles if role.startswith("perm:")]))


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
