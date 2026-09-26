"""Usuarios de prueba del realm y evaluación de permisos con la misma lógica de sio-auth.

Los usuarios, grupos y permisos se leen de la plantilla versionada del realm
(`infrastructure/keycloak/realm-template/sio-realm.template.json`), no de una copia: si la
plantilla cambia, la prueba de ejemplos y la documentación generada cambian con ella.
"""

import json
from pathlib import Path

from sio_auth.models import SioPermission
from sio_auth.permissions import extract_permission_grants, has_permission

REPO_ROOT = Path(__file__).resolve().parents[4]
REALM = REPO_ROOT / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"

_data = json.loads(REALM.read_text(encoding="utf-8"))
_groups = {"/" + group["name"]: group for group in _data["groups"]}

# Nombres de todos los client roles de `sio-api` definidos en el realm.
REALM_ROLES = frozenset(role["name"] for role in _data["roles"]["client"]["sio-api"])

USERS = []
for user in _data["users"]:
    if "serviceAccountClientId" in user:
        # Cuentas de servicio (client_credentials): no son usuarios de prueba de los ejercicios.
        continue
    group = user["groups"][0]
    roles = _groups[group]["clientRoles"]["sio-api"]
    USERS.append(dict(
        username=user["username"],
        group=group.lstrip("/"),
        roles=roles,
        perms=[role for role in roles if role.startswith("perm:")],
        role=next(role for role in roles if not role.startswith("perm:")),
    ))


def parse(permission):
    _, service, resource, action = permission.split(":")
    return SioPermission(service, resource, action)


def matching_grant(user, permission):
    """Devuelve el rol del usuario que concede el permiso, o None."""
    required = parse(permission)
    for role in user["perms"]:
        if has_permission(extract_permission_grants([role]), required):
            return role
    return None


def allowed(user, permission):
    return matching_grant(user, permission) is not None
