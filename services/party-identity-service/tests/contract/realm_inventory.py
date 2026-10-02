"""Inventario de permisos del realm (T074, T075; FR-110, R-11, R-12).

- `effective_reads(group)`: permisos `read` sin comodín de la plantilla que
  concede cada grupo, evaluados con la misma lógica de `sio-auth`.
- `declared_read_permissions()`: permisos `read` que declaran los routers de los
  servicios (`auth.permission(servicio, recurso, "read")`), resueltos por AST.

Ejecutar como script regenera la instantánea `data/realm_reads_before.json`;
solo debe hacerse con la plantilla ANTERIOR al ajuste de Q-C1 (ya generada).
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from sio_auth.models import SioPermission
from sio_auth.permissions import extract_permission_grants, has_permission

REPO_ROOT = Path(__file__).resolve().parents[4]
REALM = REPO_ROOT / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
SNAPSHOT = Path(__file__).resolve().parent / "data" / "realm_reads_before.json"
SERVICES_ROOT = REPO_ROOT / "services"


def load_realm() -> dict:
    return json.loads(REALM.read_text(encoding="utf-8"))


def realm_roles(realm: dict | None = None) -> list[str]:
    realm = realm or load_realm()
    return [role["name"] for role in realm["roles"]["client"]["sio-api"]]


def explicit_read_roles(realm: dict | None = None) -> list[str]:
    """Roles `perm:{servicio}:{recurso}:read` sin comodines."""
    return sorted(
        name
        for name in realm_roles(realm)
        if name.startswith("perm:") and name.endswith(":read") and ":all:" not in name
    )


def group_roles(group_name: str, realm: dict | None = None) -> list[str]:
    realm = realm or load_realm()
    for group in realm["groups"]:
        if group["name"] == group_name:
            return list(group.get("clientRoles", {}).get("sio-api", []))
    raise KeyError(group_name)


def service_account_roles(client_id: str, realm: dict | None = None) -> list[str]:
    realm = realm or load_realm()
    for user in realm["users"]:
        if user.get("serviceAccountClientId") == client_id:
            return list(user.get("clientRoles", {}).get("sio-api", []))
    raise KeyError(client_id)


def grants(roles: list[str], permission: str) -> bool:
    _, service, resource, action = permission.split(":")
    return has_permission(extract_permission_grants(roles), SioPermission(service, resource, action))


def effective_reads(group_name: str, realm: dict | None = None, candidates: list[str] | None = None) -> list[str]:
    realm = realm or load_realm()
    roles = group_roles(group_name, realm)
    candidates = candidates if candidates is not None else explicit_read_roles(realm)
    return sorted(permission for permission in candidates if grants(roles, permission))


# --------------------------------------------------------------------------
# Permisos declarados por el código (T075)
# --------------------------------------------------------------------------


def _module_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = node.value.value
    return constants


def declared_read_permissions() -> tuple[set[str], list[str]]:
    """Devuelve (permisos `read` resueltos, llamadas no resolubles estáticamente)."""
    resolved: set[str] = set()
    dynamic: list[str] = []

    for path in SERVICES_ROOT.glob("*/src/**/*.py"):
        text = path.read_text(encoding="utf-8")
        if "permission(" not in text:
            continue
        tree = ast.parse(text)
        constants = _module_constants(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) != 3:
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "permission":
                arguments = list(node.args)
            elif isinstance(node.func, ast.Name) and node.func.id == "permission":
                # Helper `permission(auth, recurso, acción)` de un servicio: el nombre
                # del servicio sale de su carpeta (p. ej. Product Catalog).
                service_folder = path.relative_to(SERVICES_ROOT).parts[0].removesuffix("-service")
                arguments = [ast.Constant(service_folder), *node.args[1:]]
            else:
                continue
            values = []
            for argument in arguments:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    values.append(argument.value)
                elif isinstance(argument, ast.Name) and argument.id in constants:
                    values.append(constants[argument.id])
                else:
                    values.append(None)
            if values[2] != "read":
                continue
            if None in values:
                dynamic.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
            else:
                resolved.add(f"perm:{values[0]}:{values[1]}:read")

    return resolved, sorted(dynamic)


READ_ONLY_GROUPS = ("compras", "ventas", "reportes", "consulta")
ALL_GROUPS = ("administradores", "supervisores", "compras", "ventas", "inventario", "reportes", "consulta")


def build_snapshot() -> dict:
    realm = load_realm()
    return {
        "description": (
            "Lecturas efectivas por grupo con la plantilla del realm ANTERIOR al ajuste de mínimo "
            "privilegio (specs/006-party-identity-complementary, Q-C1). Generado por "
            "tests/contract/realm_inventory.py; no editar a mano."
        ),
        "explicit_read_roles": explicit_read_roles(realm),
        "groups": {name: {"roles": group_roles(name, realm), "reads": effective_reads(name, realm)}
                   for name in ALL_GROUPS},
    }


if __name__ == "__main__":
    if "--write-snapshot" not in sys.argv:
        print(json.dumps(build_snapshot(), indent=2, ensure_ascii=False))
        resolved, dynamic = declared_read_permissions()
        print("Permisos read declarados por código:", len(resolved))
        print("No presentes en la plantilla:", sorted(resolved - set(realm_roles())))
        print("Llamadas dinámicas a revisar:", dynamic)
    else:
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(build_snapshot(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Instantánea escrita en {SNAPSHOT}")
