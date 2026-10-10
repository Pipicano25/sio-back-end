"""Lectura de la plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`).

Da los `id` fijos de los usuarios de prueba y de las cuentas de servicio, los roles de `sio-api` de cada
grupo (con sus compuestos) y la evaluación de un permiso `perm:{servicio}:{recurso}:{accion}` con el
comodín `all`, igual que `sio-auth`. No contiene secretos (la plantilla usa marcadores).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .config import REPO_ROOT

TEMPLATE = REPO_ROOT / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
API_CLIENT = "sio-api"


class Realm:
    def __init__(self, path: Path = TEMPLATE) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.users = {user["username"]: user for user in data.get("users", [])}
        self.groups = {group["name"]: group for group in data.get("groups", [])}
        roles = data.get("roles", {}).get("client", {}).get(API_CLIENT, [])
        self._composites = {
            role["name"]: tuple(((role.get("composites") or {}).get("client") or {}).get(API_CLIENT, []))
            for role in roles
        }
        self.role_names = set(self._composites)

    def user_id(self, username: str) -> str:
        return self.users[username]["id"]

    def service_account_id(self, client_id: str) -> str:
        return self.users[f"service-account-{client_id}"]["id"]

    def _expand(self, names) -> set[str]:
        result: set[str] = set()
        pending = list(names)
        while pending:
            name = pending.pop()
            if name in result:
                continue
            result.add(name)
            pending.extend(self._composites.get(name, ()))
        return result

    def user_roles(self, username: str) -> set[str]:
        user = self.users[username]
        names: list[str] = list((user.get("clientRoles") or {}).get(API_CLIENT, []))
        for group_path in user.get("groups", []):
            group = self.groups.get(group_path.strip("/"))
            if group:
                names += (group.get("clientRoles") or {}).get(API_CLIENT, [])
        return self._expand(names)

    def user_permissions(self, username: str) -> set[str]:
        return {role for role in self.user_roles(username) if role.startswith("perm:")}

    @staticmethod
    def grants(role: str, permission: str) -> bool:
        """`perm:a:b:c` concede `perm:x:y:z` si cada segmento coincide o es `all`."""
        granted = role.split(":")
        wanted = permission.split(":")
        if len(granted) != 4 or len(wanted) != 4 or granted[0] != "perm" or wanted[0] != "perm":
            return False
        return all(have in ("all", need) for have, need in zip(granted[1:], wanted[1:]))

    def has_permission(self, username: str, permission: str) -> bool:
        return any(self.grants(role, permission) for role in self.user_permissions(username))

    def granting_role(self, username: str, permission: str) -> str | None:
        matches = sorted(role for role in self.user_permissions(username) if self.grants(role, permission))
        # El más específico primero (menos comodines).
        return min(matches, key=lambda role: role.count(":all"), default=None)

    def permission_exists(self, permission: str) -> bool:
        """El permiso lo concede algún rol de la plantilla (directo o por comodín)."""
        return any(self.grants(role, permission) for role in self.role_names if role.startswith("perm:"))


@lru_cache(maxsize=1)
def realm() -> Realm:
    return Realm()
